"""Safe, deterministic export and inspect-before-commit RPM exchange."""

from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from uuid import uuid4

from .models import ResourceLimitError, canonical_digest, canonical_json
from .research_memory import (
    DataClassification,
    HumanApproval,
    ResearchMemoryService,
    ResearchScope,
)


class ExchangeError(ValueError):
    """Raised when an exchange bundle is malformed or unsafe."""


@dataclass(frozen=True)
class BundleLimits:
    max_bytes: int = 50 * 1024 * 1024
    max_files: int = 10_000
    max_events: int = 100_000
    max_uncompressed_bytes: int = 100 * 1024 * 1024

    def __post_init__(self) -> None:
        if min(self.max_bytes, self.max_files, self.max_events, self.max_uncompressed_bytes) <= 0:
            raise ValueError("bundle limits must be positive")


@dataclass(frozen=True)
class ExportSelection:
    start_sequence: int | None = None
    end_sequence: int | None = None
    include_inactive: bool = False
    max_classification: DataClassification = DataClassification.CONFIDENTIAL

    def __post_init__(self) -> None:
        if self.start_sequence is not None and self.start_sequence < 1:
            raise ValueError("start_sequence must be positive")
        if self.end_sequence is not None and self.end_sequence < 1:
            raise ValueError("end_sequence must be positive")
        if self.start_sequence and self.end_sequence and self.start_sequence > self.end_sequence:
            raise ValueError("sequence range is inverted")
        if not isinstance(self.max_classification, DataClassification):
            object.__setattr__(
                self, "max_classification", DataClassification(self.max_classification)
            )


@dataclass(frozen=True)
class ExportReceipt:
    status: str
    bundle_digest: str
    origin_scope: ResearchScope
    source_head: str
    files: tuple[str, ...]
    redacted_items: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "bundle_digest": self.bundle_digest,
            "origin_scope": self.origin_scope.to_dict(),
            "source_head": self.source_head,
            "files": list(self.files),
            "redacted_items": list(self.redacted_items),
        }


@dataclass(frozen=True)
class ImportInspection:
    inspection_id: str
    inspection_digest: str
    source_bundle_digest: str
    origin_scope: ResearchScope
    destination_scope: ResearchScope
    commit_eligible: bool
    diff: dict[str, Any]
    checks: dict[str, str]
    events: tuple[Mapping[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = "2.0.0"

    def __post_init__(self) -> None:
        # Copy the inspected payload at the boundary so later origin-store
        # mutations cannot change the set committed for this inspection.
        object.__setattr__(
            self,
            "events",
            tuple(json.loads(canonical_json(dict(event))) for event in self.events),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "inspection_id": self.inspection_id,
            "inspection_digest": self.inspection_digest,
            "source_bundle_digest": self.source_bundle_digest,
            "origin_scope": self.origin_scope.to_dict(),
            "destination_scope": self.destination_scope.to_dict(),
            "commit_eligible": self.commit_eligible,
            "diff": self.diff,
            "checks": self.checks,
            "events": [dict(event) for event in self.events],
            "warnings": list(self.warnings),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ImportReceipt:
    status: str
    inspection_id: str
    origin_scope: ResearchScope
    destination_scope: ResearchScope
    imported_event_ids: tuple[str, ...] = ()
    collision_ids: tuple[str, ...] = ()
    schema_version: str = "2.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "inspection_id": self.inspection_id,
            "origin_scope": self.origin_scope.to_dict(),
            "destination_scope": self.destination_scope.to_dict(),
            "imported_event_ids": list(self.imported_event_ids),
            "collision_ids": list(self.collision_ids),
            "schema_version": self.schema_version,
        }


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_member(name: str) -> str:
    if not name or "\\" in name:
        raise ExchangeError(f"unsafe bundle path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or name.startswith("/"):
        raise ExchangeError(f"unsafe bundle path: {name!r}")
    normalized = path.as_posix()
    if normalized in {".", ""} or normalized != name:
        raise ExchangeError(f"non-canonical bundle path: {name!r}")
    return normalized


class RPMExchange:
    """Exchange facade bound to one :class:`ResearchMemoryService`."""

    REQUIRED_FILES = {
        "manifest.json",
        "events.ndjson",
        "checksums.json",
        "limitations.json",
    }

    def __init__(self, service: ResearchMemoryService) -> None:
        self.service = service
        self._inspections: dict[str, ImportInspection] = {}
        self._committed: set[str] = set()

    def export_bundle(
        self,
        scope: ResearchScope,
        selection: ExportSelection,
        approval: HumanApproval,
        limits: BundleLimits,
        output_dir: str | Path,
        *,
        epg_v2: Any | None = None,
        epg_certificate: Any | None = None,
    ) -> ExportReceipt:
        self.service._binding(scope)
        output = Path(output_dir)
        if output.exists() and any(output.iterdir()):
            raise ExchangeError("export destination is not empty")
        output.mkdir(parents=True, exist_ok=True)
        events = self.service.store.events(scope)
        events = [
            event
            for event in events
            if (selection.start_sequence is None or event["sequence"] >= selection.start_sequence)
            and (selection.end_sequence is None or event["sequence"] <= selection.end_sequence)
        ]
        if len(events) > limits.max_events:
            raise ResourceLimitError("export exceeds event limit")
        redacted: list[str] = []
        exported: list[dict[str, Any]] = []
        for event in events:
            copy = json.loads(canonical_json(event))
            candidate = copy.get("payload", {}).get("candidate")
            if isinstance(candidate, dict):
                classification = DataClassification(candidate.get("data_classification", "secret"))
                if classification.rank > selection.max_classification.rank:
                    redacted.append(str(candidate.get("item_id", copy.get("item_id"))))
                    copy["payload"]["candidate"] = {
                        "item_id": candidate.get("item_id"),
                        "data_classification": classification.value,
                        "redacted": True,
                    }
            exported.append(copy)
        self._write_file(
            output / "events.ndjson", "".join(canonical_json(event) + "\n" for event in exported)
        )
        payload_dir = output / "payloads"
        provenance_dir = output / "provenance"
        decisions_dir = output / "decisions"
        for directory in (payload_dir, provenance_dir, decisions_dir):
            directory.mkdir()
        for event in exported:
            payload = event.get("payload", {})
            self._write_file(
                payload_dir / f"{event['event_id']}.json", canonical_json(payload) + "\n"
            )
        self._write_file(
            provenance_dir / "export.json",
            canonical_json(
                {
                    "scope": scope.to_dict(),
                    "event_ids": [event["event_id"] for event in exported],
                    "source_head": self.service.store.chain_head(scope),
                }
            )
            + "\n",
        )
        self._write_file(
            decisions_dir / "export-approval.json", canonical_json(approval.to_dict()) + "\n"
        )
        if epg_v2 is not None:
            self._write_certified_epg(output / "provenance", epg_v2, epg_certificate)
        self._write_file(
            output / "limitations.json",
            canonical_json(
                {
                    "redacted_items": sorted(redacted),
                    "logical_deletion_only": True,
                    "origin_preserved": True,
                }
            )
            + "\n",
        )
        file_entries = []
        for path in sorted(output.rglob("*")):
            if path.is_file():
                relative = path.relative_to(output).as_posix()
                file_entries.append(
                    {
                        "path": relative,
                        "bytes": path.stat().st_size,
                        "sha256": _sha256_bytes(path.read_bytes()),
                    }
                )
        manifest = {
            "schema_version": "2.0.0",
            "bundle_version": "2.0.0",
            "origin_scope": scope.to_dict(),
            "files": file_entries,
            "source_head": self.service.store.chain_head(scope),
            "classification_ceiling": selection.max_classification.value,
            "canonicalization": ["canonical-json-v1", "sha256"],
            "approval": {
                "approval_id": approval.approval_id,
                "digest": canonical_digest(approval.to_dict()),
            },
            "counts": {"events": len(exported), "redacted": len(redacted)},
            "rights_exclusions": sorted(redacted),
        }
        self._write_file(output / "manifest.json", canonical_json(manifest) + "\n")
        checksums = {
            path.relative_to(output).as_posix(): _sha256_bytes(path.read_bytes())
            for path in sorted(output.rglob("*"))
            if path.is_file() and path.name != "checksums.json"
        }
        self._write_file(output / "checksums.json", canonical_json(checksums) + "\n")
        total_bytes = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
        if total_bytes > limits.max_bytes:
            raise ResourceLimitError("export exceeds byte limit")
        return ExportReceipt(
            status="exported",
            bundle_digest=canonical_digest(checksums),
            origin_scope=scope,
            source_head=self.service.store.chain_head(scope),
            files=tuple(sorted(checksums)),
            redacted_items=tuple(sorted(redacted)),
        )

    @staticmethod
    def _write_certified_epg(directory: Path, document: Any, certificate: Any | None) -> None:
        """Add EPG v2 only when a matching independent certificate is certified."""

        from .prov_validation import canonical_fingerprint, validate_prov

        payload = document if hasattr(document, "to_dict") else document
        if not hasattr(document, "semantic_normal_form"):
            from .prov_model import ProvDocument

            document = ProvDocument(**dict(payload or {}))
        certificate_payload = (
            certificate.to_dict() if hasattr(certificate, "to_dict") else dict(certificate or {})
        )
        if certificate_payload.get("status") != "certified":
            raise ExchangeError(
                "certified EPG v2 export requires an independent certified certificate"
            )
        validation = validate_prov(document)
        fingerprint = canonical_fingerprint(document)
        if (
            validation.status != "valid"
            or certificate_payload.get("input_digest") != fingerprint.semantic_digest
        ):
            raise ExchangeError("EPG v2 certificate does not match a valid document fingerprint")
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "epg-v2.json").write_text(
            canonical_json(document.to_dict()) + "\n", encoding="utf-8"
        )
        (directory / "epg-v2-fingerprint.json").write_text(
            canonical_json(fingerprint.to_dict()) + "\n", encoding="utf-8"
        )
        (directory / "epg-v2-certificate.json").write_text(
            canonical_json(certificate_payload) + "\n", encoding="utf-8"
        )

    def export_certified_epg(self, document: Any, certificate: Any, output_dir: str | Path) -> str:
        """Export a standalone certified EPG v2 provenance set."""

        output = Path(output_dir)
        if output.exists() and any(output.iterdir()):
            raise ExchangeError("EPG export destination is not empty")
        self._write_certified_epg(output, document, certificate)
        from .prov_validation import canonical_fingerprint

        return canonical_fingerprint(document).semantic_digest

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8", newline="\n")

    def _read_bundle(self, bundle: str | Path, limits: BundleLimits) -> dict[str, bytes]:
        path = Path(bundle)
        files: dict[str, bytes] = {}
        if path.is_dir():
            candidates = list(path.rglob("*"))
            if len(candidates) > limits.max_files * 2:
                raise ResourceLimitError("bundle entry count exceeds limit")
            for item in candidates:
                if item.is_symlink() or (not item.is_file() and not item.is_dir()):
                    raise ExchangeError(f"links and devices are not allowed: {item}")
                if item.is_file():
                    name = _safe_member(item.relative_to(path).as_posix())
                    files[name] = item.read_bytes()
        elif path.is_file() and path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                if len(infos) > limits.max_files:
                    raise ResourceLimitError("bundle file count exceeds limit")
                for info in infos:
                    if info.is_dir():
                        continue
                    name = _safe_member(info.filename)
                    if name in files:
                        raise ExchangeError(f"duplicate bundle path: {name}")
                    mode = (info.external_attr >> 16) & 0o170000
                    if mode == stat.S_IFLNK:
                        raise ExchangeError("zip symlink is not allowed")
                    if info.file_size > limits.max_uncompressed_bytes:
                        raise ResourceLimitError("compressed member exceeds uncompressed limit")
                    files[name] = archive.read(info)
        else:
            raise ExchangeError("bundle must be a directory or zip file")
        if len(files) > limits.max_files:
            raise ResourceLimitError("bundle file count exceeds limit")
        if sum(len(value) for value in files.values()) > limits.max_uncompressed_bytes:
            raise ResourceLimitError("bundle exceeds uncompressed byte limit")
        if not self.REQUIRED_FILES <= set(files):
            raise ExchangeError("bundle is missing required files")
        return files

    def inspect_import(
        self,
        bundle: str | Path,
        *,
        destination: ResearchScope,
        limits: BundleLimits,
        as_of: Any | None = None,
    ) -> ImportInspection:
        self.service._binding(destination)
        files = self._read_bundle(bundle, limits)
        try:
            manifest = json.loads(files["manifest.json"].decode("utf-8"))
            checksums = json.loads(files["checksums.json"].decode("utf-8"))
            events = [
                json.loads(line)
                for line in files["events.ndjson"].decode("utf-8").splitlines()
                if line.strip()
            ]
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExchangeError("malformed bundle JSON or NDJSON") from exc
        origin_data = manifest.get("origin_scope")
        if not isinstance(origin_data, dict):
            raise ExchangeError("bundle has no origin scope")
        origin = ResearchScope(**origin_data)
        actual_bundle_digest = canonical_digest(
            {
                name: _sha256_bytes(data)
                for name, data in sorted(files.items())
                if name != "checksums.json"
            }
        )
        checksum_errors: list[str] = []
        if not isinstance(checksums, dict):
            raise ExchangeError("checksums must be an object")
        for name, expected in checksums.items():
            if name not in files or _sha256_bytes(files[name]) != expected:
                checksum_errors.append(name)
        if checksum_errors:
            raise ExchangeError("checksum failure: " + ", ".join(sorted(checksum_errors)))
        if len(events) > limits.max_events:
            raise ResourceLimitError("bundle event count exceeds limit")
        chain_errors = self._verify_import_chain(events, origin)
        collision_ids: list[str] = []
        identical_ids: list[str] = []
        for event in events:
            item_id = event.get("item_id") or event.get("payload", {}).get("item_id")
            if not item_id:
                continue
            existing = self.service.store.get_projection(destination, item_id)
            if existing is None:
                continue
            incoming_digest = event.get("payload", {}).get("candidate_digest")
            if incoming_digest and incoming_digest == existing.get("candidate_digest"):
                identical_ids.append(str(item_id))
            else:
                collision_ids.append(str(item_id))
        diff = {
            "events": len(events),
            "identical_ids": sorted(set(identical_ids)),
            "collision_ids": sorted(set(collision_ids)),
            "origin_scope": origin.to_dict(),
            "destination_scope": destination.to_dict(),
        }
        checks = {
            "schema": "pass" if manifest.get("schema_version") == "2.0.0" else "fail",
            "checksums": "pass",
            "chain": "pass" if not chain_errors else "fail",
            "collisions": "pass" if not collision_ids else "fail",
        }
        inspection = ImportInspection(
            inspection_id=f"inspection-{uuid4()}",
            inspection_digest=canonical_digest(
                {"manifest": manifest, "events": events, "diff": diff}
            ),
            source_bundle_digest=actual_bundle_digest,
            origin_scope=origin,
            destination_scope=destination,
            commit_eligible=not chain_errors and not collision_ids and checks["schema"] == "pass",
            diff=diff,
            checks=checks,
            events=tuple(events),
            warnings=tuple(chain_errors),
        )
        self._inspections[inspection.inspection_id] = inspection
        if chain_errors:
            raise ExchangeError("event chain failure: " + "; ".join(chain_errors))
        if collision_ids:
            raise ExchangeError("ID/digest collision: " + ", ".join(sorted(set(collision_ids))))
        return inspection

    @staticmethod
    def _verify_import_chain(events: list[Mapping[str, Any]], scope: ResearchScope) -> list[str]:
        errors: list[str] = []
        previous = ""
        for sequence, event in enumerate(events, start=1):
            if event.get("sequence") != sequence:
                errors.append(f"sequence mismatch at {sequence}")
            if event.get("previous_hash") != previous:
                errors.append(f"previous hash mismatch at {sequence}")
            body = dict(event)
            event_hash = body.pop("event_hash", None)
            if event_hash != canonical_digest(body):
                errors.append(f"event digest mismatch at {sequence}")
            if event.get("scope") != scope.to_dict():
                errors.append(f"scope mismatch at {sequence}")
            previous = str(event_hash or "")
        return errors

    def commit_import(
        self,
        inspection_id: str,
        inspection_digest: str,
        approval: HumanApproval,
    ) -> ImportReceipt:
        inspection = self._inspections.get(inspection_id)
        if inspection is None or inspection.inspection_digest != inspection_digest:
            raise ExchangeError("inspection digest is unknown or stale")
        if not inspection.commit_eligible:
            raise ExchangeError("import inspection is not eligible")
        if approval.disposition != "approved":
            raise ExchangeError("import approval is not approved")
        if approval.assessment_digest != inspection.inspection_digest:
            raise ExchangeError("import approval is not bound to inspection digest")
        if inspection.diff.get("events") != len(inspection.events):
            raise ExchangeError("import inspection does not retain its event snapshot")
        if inspection_id in self._committed:
            return ImportReceipt(
                "noop", inspection_id, inspection.origin_scope, inspection.destination_scope
            )
        imported: list[str] = []
        for event in inspection.events:
            operation_id = f"import:{inspection_id}:{event['event_id']}"
            self.service.store.append_event(
                inspection.destination_scope,
                "import",
                event.get("item_id"),
                {"origin_event": event, **dict(event.get("payload", {}))},
                operation_id=operation_id,
            )
            imported.append(str(event["event_id"]))
        self._committed.add(inspection_id)
        return ImportReceipt(
            status="committed",
            inspection_id=inspection_id,
            origin_scope=inspection.origin_scope,
            destination_scope=inspection.destination_scope,
            imported_event_ids=tuple(imported),
        )


def export_bundle(
    service: ResearchMemoryService,
    scope: ResearchScope,
    selection: ExportSelection,
    approval: HumanApproval,
    limits: BundleLimits,
    output_dir: str | Path,
    *,
    epg_v2: Any | None = None,
    epg_certificate: Any | None = None,
) -> ExportReceipt:
    return RPMExchange(service).export_bundle(
        scope,
        selection,
        approval,
        limits,
        output_dir,
        epg_v2=epg_v2,
        epg_certificate=epg_certificate,
    )


def inspect_import(
    service: ResearchMemoryService,
    bundle: str | Path,
    *,
    destination: ResearchScope,
    limits: BundleLimits,
    as_of: Any | None = None,
) -> ImportInspection:
    return RPMExchange(service).inspect_import(
        bundle, destination=destination, limits=limits, as_of=as_of
    )
