"""File-backed append-only stores for governed SWOS audit artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .governance import can_write_durable_rpm
from .models import swos_id

STORE_VERSION = "swos.governed-store.v1"
GENESIS_HASH = "GENESIS"
VALID_OPERATIONS = {"append", "correction", "supersession"}
RUN_STORE_ARTIFACTS = {
    "epg": ("epg", "provenance.json"),
    "sdl": ("sdl", "decision-ledger.json"),
    "rpm": ("rpm", "rpm.json"),
    "evidence_matrix": ("evidence_matrix", "evidence-matrix.json"),
    "argument_graph": ("argument_graph", "argument-graph.json"),
}


class StoreError(RuntimeError):
    """Raised when a governed store cannot be trusted or safely mutated."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


class GovernedJsonStore:
    """Append-only JSONL chain with correction and supersession semantics."""

    def __init__(self, path: str | Path, *, store_name: str, artifact_type: str) -> None:
        self.path = Path(path)
        self.store_name = store_name
        self.artifact_type = artifact_type

    def _read_unverified(self) -> tuple[list[dict[str, Any]], list[str]]:
        if not self.path.is_file():
            return [], [f"store file is missing: {self.path}"]
        records: list[dict[str, Any]] = []
        errors: list[str] = []
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                errors.append(f"line {line_number}: blank records are not permitted")
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: malformed JSON: {exc.msg}")
                continue
            if not isinstance(record, dict):
                errors.append(f"line {line_number}: record is not an object")
                continue
            records.append(record)
        if not records:
            errors.append("store contains no records")
        return records, errors

    def verification_errors(self) -> list[str]:
        records, errors = self._read_unverified()
        previous_hash = GENESIS_HASH
        seen_ids: set[str] = set()
        active_ids: set[str] = set()
        required = {
            "store_version",
            "store_name",
            "artifact_type",
            "sequence",
            "record_id",
            "operation",
            "recorded_at",
            "actor",
            "payload",
            "payload_hash",
            "supersedes",
            "rationale",
            "approval",
            "previous_hash",
            "record_hash",
        }
        for expected_sequence, record in enumerate(records, start=1):
            prefix = f"record {expected_sequence}"
            missing = sorted(required - set(record))
            if missing:
                errors.append(f"{prefix}: missing fields: {', '.join(missing)}")
            if record.get("store_version") != STORE_VERSION:
                errors.append(f"{prefix}: wrong store version")
            if record.get("store_name") != self.store_name:
                errors.append(f"{prefix}: wrong store identity")
            if record.get("artifact_type") != self.artifact_type:
                errors.append(f"{prefix}: wrong artifact type")
            if record.get("sequence") != expected_sequence:
                errors.append(f"{prefix}: sequence is not contiguous")
            record_id = record.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                errors.append(f"{prefix}: invalid record id")
            elif record_id in seen_ids:
                errors.append(f"{prefix}: duplicate record id")
            if not _valid_timestamp(record.get("recorded_at")):
                errors.append(f"{prefix}: invalid recorded_at timestamp")
            actor = record.get("actor")
            if not isinstance(actor, dict) or not str(actor.get("actor_id") or "").strip():
                errors.append(f"{prefix}: actor identity is incomplete")
            if record.get("payload_hash") != _digest(record.get("payload")):
                errors.append(f"{prefix}: payload hash mismatch")
            if record.get("previous_hash") != previous_hash:
                errors.append(f"{prefix}: previous hash mismatch")

            operation = record.get("operation")
            supersedes = record.get("supersedes")
            if operation not in VALID_OPERATIONS:
                errors.append(f"{prefix}: invalid operation")
            if not isinstance(supersedes, list):
                errors.append(f"{prefix}: supersedes must be an array")
                supersedes = []
            if operation == "append" and supersedes:
                errors.append(f"{prefix}: append cannot supersede a prior record")
            if operation in {"correction", "supersession"}:
                if len(supersedes) != 1:
                    errors.append(f"{prefix}: {operation} must target exactly one record")
                elif supersedes[0] not in active_ids:
                    errors.append(f"{prefix}: supersession target is not active")
                if not str(record.get("rationale") or "").strip():
                    errors.append(f"{prefix}: {operation} requires a rationale")

            material = {key: value for key, value in record.items() if key != "record_hash"}
            expected_hash = _digest(material)
            if record.get("record_hash") != expected_hash:
                errors.append(f"{prefix}: record hash mismatch")

            if isinstance(record_id, str) and record_id:
                seen_ids.add(record_id)
                active_ids.add(record_id)
            for target in supersedes:
                active_ids.discard(target)
            previous_hash = expected_hash
        return errors

    def records(self) -> list[dict[str, Any]]:
        errors = self.verification_errors()
        if errors:
            raise StoreError("; ".join(errors))
        records, _ = self._read_unverified()
        return records

    def lifecycle_records(self) -> list[dict[str, Any]]:
        records = self.records()
        superseded_by: dict[str, list[str]] = {record["record_id"]: [] for record in records}
        for record in records:
            for target in record["supersedes"]:
                superseded_by[target].append(record["record_id"])
        return [
            {**record, "superseded_by": superseded_by[record["record_id"]]} for record in records
        ]

    def active_records(self) -> list[dict[str, Any]]:
        records = self.records()
        superseded = {target for record in records for target in record["supersedes"]}
        return [record for record in records if record["record_id"] not in superseded]

    def append(
        self,
        payload: Any,
        *,
        actor: dict[str, Any],
        recorded_at: str | None = None,
        record_id: str | None = None,
        approval: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._append_record(
            payload,
            actor=actor,
            operation="append",
            supersedes=[],
            rationale=None,
            recorded_at=recorded_at,
            record_id=record_id,
            approval=approval,
        )

    def correct(
        self,
        target_record_id: str,
        payload: Any,
        *,
        actor: dict[str, Any],
        rationale: str,
        recorded_at: str | None = None,
        record_id: str | None = None,
        approval: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._append_record(
            payload,
            actor=actor,
            operation="correction",
            supersedes=[target_record_id],
            rationale=rationale,
            recorded_at=recorded_at,
            record_id=record_id,
            approval=approval,
        )

    def supersede(
        self,
        target_record_id: str,
        payload: Any,
        *,
        actor: dict[str, Any],
        rationale: str,
        recorded_at: str | None = None,
        record_id: str | None = None,
        approval: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._append_record(
            payload,
            actor=actor,
            operation="supersession",
            supersedes=[target_record_id],
            rationale=rationale,
            recorded_at=recorded_at,
            record_id=record_id,
            approval=approval,
        )

    def _append_record(
        self,
        payload: Any,
        *,
        actor: dict[str, Any],
        operation: str,
        supersedes: list[str],
        rationale: str | None,
        recorded_at: str | None,
        record_id: str | None,
        approval: dict[str, Any] | None,
    ) -> dict[str, Any]:
        existing: list[dict[str, Any]] = []
        if self.path.exists():
            existing = self.records()
        if not isinstance(actor, dict) or not str(actor.get("actor_id") or "").strip():
            raise StoreError("actor identity is incomplete")
        timestamp = recorded_at or _now()
        if not _valid_timestamp(timestamp):
            raise StoreError("recorded_at must be an ISO 8601 timestamp")
        if operation not in VALID_OPERATIONS:
            raise StoreError(f"unsupported store operation: {operation}")
        active_ids = (
            {record["record_id"] for record in self.active_records()} if existing else set()
        )
        if operation == "append" and supersedes:
            raise StoreError("append cannot supersede a prior record")
        if operation in {"correction", "supersession"}:
            if len(supersedes) != 1 or supersedes[0] not in active_ids:
                raise StoreError("correction/supersession target must be an active record")
            if not str(rationale or "").strip():
                raise StoreError("correction/supersession requires a rationale")

        material = {
            "store_version": STORE_VERSION,
            "store_name": self.store_name,
            "artifact_type": self.artifact_type,
            "sequence": len(existing) + 1,
            "record_id": record_id or swos_id("rec"),
            "operation": operation,
            "recorded_at": timestamp,
            "actor": actor,
            "payload": payload,
            "payload_hash": _digest(payload),
            "supersedes": supersedes,
            "rationale": rationale,
            "approval": approval,
            "previous_hash": existing[-1]["record_hash"] if existing else GENESIS_HASH,
        }
        if any(record["record_id"] == material["record_id"] for record in existing):
            raise StoreError("record id already exists")
        record = {**material, "record_hash": _digest(material)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        errors = self.verification_errors()
        if errors:
            raise StoreError("store failed verification after append: " + "; ".join(errors))
        return record


class ResearchProgrammeMemoryStore(GovernedJsonStore):
    """RPM item store enforcing the frozen durable-write governance rule."""

    def __init__(self, path: str | Path) -> None:
        super().__init__(path, store_name="rpm", artifact_type="rpm_item")

    def append_item(
        self,
        item: dict[str, Any],
        *,
        approval: dict[str, Any],
        recorded_at: str | None = None,
        record_id: str | None = None,
    ) -> dict[str, Any]:
        provenance = item.get("provenance") if isinstance(item, dict) else None
        epg_refs = provenance.get("epg_node_ids") if isinstance(provenance, dict) else []
        sdl_id = provenance.get("sdl_decision_id") if isinstance(provenance, dict) else None
        approver = approval.get("approver") if isinstance(approval, dict) else None
        approval_actor_type = approval.get("actor_type") if isinstance(approval, dict) else None
        approved_at = approval.get("approved_at") if isinstance(approval, dict) else None
        rationale = approval.get("rationale") if isinstance(approval, dict) else None
        owner = item.get("owner") if isinstance(item, dict) else None
        expiry = item.get("expiry") if isinstance(item, dict) else None
        timestamp = recorded_at or _now()
        try:
            expiry_date = date.fromisoformat(str(expiry))
            recorded_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()
            expiry_valid = expiry_date > recorded_date
        except (TypeError, ValueError):
            expiry_valid = False
        if not isinstance(owner, dict) or not str(owner.get("actor_id") or "").strip():
            raise StoreError("RPM item owner is required")
        if not expiry_valid:
            raise StoreError("RPM item requires a valid expiry date")
        if (
            approval_actor_type != "human"
            or not _valid_timestamp(approved_at)
            or not str(rationale or "").strip()
        ):
            raise StoreError("RPM write requires timestamped human approval and rationale")
        if not can_write_durable_rpm(
            source_grounded=item.get("source_grounded") is True,
            epg_refs=list(epg_refs or []),
            sdl_id=str(sdl_id) if sdl_id else None,
            human_approver=str(approver) if approver else None,
        ):
            raise StoreError("RPM write lacks source, EPG, SDL or human-approval evidence")
        return self.append(
            item,
            actor=owner,
            recorded_at=timestamp,
            record_id=record_id,
            approval=approval,
        )


def persist_run_stores(
    root: str | Path,
    *,
    actor: dict[str, Any],
    recorded_at: str | None = None,
) -> dict[str, str]:
    """Persist or supersede the five canonical run artifacts."""
    root = Path(root)
    timestamp = recorded_at or _now()
    heads: dict[str, str] = {}
    for store_name, (artifact_type, filename) in RUN_STORE_ARTIFACTS.items():
        artifact_path = root / filename
        if not artifact_path.is_file():
            raise StoreError(f"run artifact is missing: {filename}")
        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StoreError(f"run artifact is malformed: {filename}") from exc
        store = GovernedJsonStore(
            root / "governed-stores" / f"{store_name}.jsonl",
            store_name=store_name,
            artifact_type=artifact_type,
        )
        if store.path.exists():
            active = store.active_records()
            if len(active) != 1:
                raise StoreError(f"{store_name} does not have exactly one active record")
            record = store.supersede(
                active[0]["record_id"],
                payload,
                actor=actor,
                rationale="Superseded by a later finalized artifact snapshot.",
                recorded_at=timestamp,
            )
        else:
            record = store.append(payload, actor=actor, recorded_at=timestamp)
        heads[store_name] = record["record_hash"]
    errors = verify_run_stores(root)
    if errors:
        raise StoreError("run store verification failed: " + "; ".join(errors))
    return heads


def verify_run_stores(root: str | Path, *, expected_heads: object | None = None) -> list[str]:
    """Verify all store chains and bind each active payload to its artifact."""
    root = Path(root)
    errors: list[str] = []
    if expected_heads is not None and not isinstance(expected_heads, dict):
        return ["declared store heads must be an object"]
    for store_name, (artifact_type, filename) in RUN_STORE_ARTIFACTS.items():
        store = GovernedJsonStore(
            root / "governed-stores" / f"{store_name}.jsonl",
            store_name=store_name,
            artifact_type=artifact_type,
        )
        store_errors = store.verification_errors()
        errors.extend(f"{store_name}: {error}" for error in store_errors)
        if store_errors:
            continue
        active = store.active_records()
        if len(active) != 1:
            errors.append(f"{store_name}: expected exactly one active record")
            continue
        if (
            expected_heads is not None
            and expected_heads.get(store_name) != active[0]["record_hash"]
        ):
            errors.append(f"{store_name}: active record does not match declared store head")
        artifact_path = root / filename
        if not artifact_path.is_file():
            errors.append(f"{store_name}: bound artifact is missing: {filename}")
            continue
        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"{store_name}: bound artifact is malformed: {filename}")
            continue
        if active[0]["payload_hash"] != _digest(artifact) or active[0]["payload"] != artifact:
            errors.append(f"{store_name}: active record does not match {filename}")
    return errors
