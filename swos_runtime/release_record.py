"""Validate SWOS's small, exact-commit release record."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

RELEASE_RECORD_VERSION = "swos.release-record.v1"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ReleaseRecordError(ValueError):
    """Raised when a release record cannot be trusted."""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseRecordError(f"cannot load release record {path}: {exc}") from exc


def _digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ReleaseRecordError(f"cannot hash release evidence {path}: {exc}") from exc


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _source_hashes(project: dict[str, Any]) -> dict[str, str]:
    snapshots = project.get("source_snapshots")
    if not isinstance(snapshots, list):
        raise ReleaseRecordError("public proof project has no source snapshots")
    result: dict[str, str] = {}
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            raise ReleaseRecordError("public proof source snapshot is not an object")
        source_id = snapshot.get("source_id")
        digest = snapshot.get("sha256")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ReleaseRecordError("public proof source snapshot has no source_id")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise ReleaseRecordError(f"public proof source hash is invalid: {source_id}")
        if source_id in result:
            raise ReleaseRecordError(f"public proof source_id is duplicated: {source_id}")
        result[source_id] = digest
    return dict(sorted(result.items()))


def _validate(
    record: Any,
    *,
    selected_sha: str,
    proof_dir: Path,
    reproduction_path: Path,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["release record must be a JSON object"]

    required = {
        "record_version",
        "selected_sha",
        "decision",
        "approved_by",
        "approved_at",
        "rationale",
        "tests",
        "proof",
        "evidence",
    }
    missing = sorted(required - set(record))
    unknown = sorted(set(record) - required)
    if missing:
        errors.append("release record is missing: " + ", ".join(missing))
    if unknown:
        errors.append("release record has unsupported fields: " + ", ".join(unknown))

    if record.get("record_version") != RELEASE_RECORD_VERSION:
        errors.append(f"release record version must be {RELEASE_RECORD_VERSION}")

    expected_sha = selected_sha.lower()
    record_sha = record.get("selected_sha")
    if not isinstance(record_sha, str) or not COMMIT_PATTERN.fullmatch(record_sha.lower()):
        errors.append("release record selected_sha must be a full 40-character hexadecimal commit")
    elif record_sha.lower() != expected_sha:
        errors.append("release record selected_sha does not match the selected commit")

    if record.get("decision") != "approve":
        errors.append("release record decision must be approve")

    approver = record.get("approved_by")
    if not isinstance(approver, dict) or not str(approver.get("id") or "").strip():
        errors.append("release record approved_by.id is missing")
    if not isinstance(approver, dict) or not str(approver.get("name") or "").strip():
        errors.append("release record approved_by.name is missing")

    if not _timestamp(record.get("approved_at")):
        errors.append("release record approved_at must be a timezone-aware ISO 8601 timestamp")
    if not str(record.get("rationale") or "").strip():
        errors.append("release record rationale is missing")

    tests = record.get("tests")
    if not isinstance(tests, dict):
        errors.append("release record tests must be an object")
    else:
        for name in ("deterministic_pr", "offline_public_release"):
            if tests.get(name) != "passed":
                errors.append(f"release record test result did not pass: {name}")

    proof_result_path = proof_dir / "proof-result.json"
    project_path = proof_dir / "project.json"
    proof_result: Any = None
    project: Any = None
    try:
        proof_result = _load(proof_result_path)
    except ReleaseRecordError as exc:
        errors.append(str(exc))
    try:
        project = _load(project_path)
    except ReleaseRecordError as exc:
        errors.append(str(exc))

    proof = record.get("proof")
    if not isinstance(proof, dict):
        errors.append("release record proof must be an object")
    else:
        if proof.get("status") != "passed":
            errors.append("release record proof status did not pass")
        fingerprint = proof.get("fingerprint")
        if not isinstance(fingerprint, str) or not SHA256_PATTERN.fullmatch(fingerprint):
            errors.append("release record proof fingerprint is invalid")
        elif isinstance(proof_result, dict) and fingerprint != proof_result.get(
            "proof_fingerprint"
        ):
            errors.append("release record proof fingerprint does not match proof-result.json")
        if proof.get("run_id") != (proof_result or {}).get("run_id"):
            errors.append("release record proof run_id does not match proof-result.json")
        if proof.get("reproduction") != "passed":
            errors.append("release record reproduction result did not pass")

    try:
        reproduction = _load(reproduction_path)
    except ReleaseRecordError as exc:
        reproduction = None
        errors.append(str(exc))
    if not isinstance(reproduction, dict):
        errors.append("independent reproduction report must be an object")
    elif (
        reproduction.get("decision") != "pass"
        or reproduction.get("reasons")
        or reproduction.get("primary_fingerprint") != reproduction.get("reproduced_fingerprint")
        or reproduction.get("primary_fingerprint") != (proof_result or {}).get("proof_fingerprint")
    ):
        errors.append("independent reproduction does not match the release proof")

    evidence = record.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("release record evidence must be an object")
    else:
        expected_evidence = {
            "proof_result_sha256",
            "project_sha256",
            "reproduction_sha256",
            "source_sha256",
        }
        if set(evidence) != expected_evidence:
            errors.append("release record evidence must contain only the four required hash fields")
        for field, path in (
            ("proof_result_sha256", proof_result_path),
            ("project_sha256", project_path),
            ("reproduction_sha256", reproduction_path),
        ):
            digest = evidence.get(field)
            if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
                errors.append(f"release record evidence hash is invalid: {field}")
            elif path.is_file() and _digest(path) != digest:
                errors.append(f"release record evidence hash does not match: {field}")
        try:
            expected_sources = _source_hashes(project) if isinstance(project, dict) else None
        except ReleaseRecordError as exc:
            expected_sources = None
            errors.append(str(exc))
        if expected_sources is not None and evidence.get("source_sha256") != expected_sources:
            errors.append("release record source hashes do not match the public project")

    return sorted(set(errors))


def read_release_record(path: str | Path) -> dict[str, Any]:
    """Load one release record without weakening its JSON shape checks."""

    record = _load(Path(path))
    if not isinstance(record, dict):
        raise ReleaseRecordError("release record must be a JSON object")
    return record


def verify_release_record(
    record_path: str | Path,
    *,
    selected_sha: str,
    proof_dir: str | Path,
    reproduction_path: str | Path,
) -> list[str]:
    """Return deterministic validation errors for one exact-SHA release record."""

    try:
        record = read_release_record(record_path)
        return _validate(
            record,
            selected_sha=selected_sha,
            proof_dir=Path(proof_dir),
            reproduction_path=Path(reproduction_path),
        )
    except ReleaseRecordError as exc:
        return [str(exc)]


def create_release_record(
    *,
    selected_sha: str,
    proof_dir: str | Path,
    reproduction_path: str | Path,
    approved_by_id: str,
    approved_by_name: str,
    approved_at: str,
    rationale: str,
    output_path: str | Path,
) -> dict[str, Any]:
    """Create and validate the single release record from existing evidence."""

    proof_root = Path(proof_dir)
    reproduction = Path(reproduction_path)
    proof_result = _load(proof_root / "proof-result.json")
    project = _load(proof_root / "project.json")
    if not isinstance(proof_result, dict) or not isinstance(project, dict):
        raise ReleaseRecordError("proof-result.json and project.json must be JSON objects")
    if not isinstance(selected_sha, str) or not COMMIT_PATTERN.fullmatch(selected_sha.lower()):
        raise ReleaseRecordError("selected SHA must be a full 40-character hexadecimal commit")

    record = {
        "record_version": RELEASE_RECORD_VERSION,
        "selected_sha": selected_sha.lower(),
        "decision": "approve",
        "approved_by": {"id": approved_by_id, "name": approved_by_name},
        "approved_at": approved_at,
        "rationale": rationale,
        "tests": {"deterministic_pr": "passed", "offline_public_release": "passed"},
        "proof": {
            "status": "passed",
            "run_id": proof_result.get("run_id"),
            "fingerprint": proof_result.get("proof_fingerprint"),
            "reproduction": "passed",
        },
        "evidence": {
            "proof_result_sha256": _digest(proof_root / "proof-result.json"),
            "project_sha256": _digest(proof_root / "project.json"),
            "reproduction_sha256": _digest(reproduction),
            "source_sha256": _source_hashes(project),
        },
    }
    errors = _validate(
        record,
        selected_sha=selected_sha,
        proof_dir=proof_root,
        reproduction_path=reproduction,
    )
    if errors:
        raise ReleaseRecordError("release record failed validation: " + "; ".join(errors))

    output = Path(output_path)
    if output.exists():
        raise ReleaseRecordError("release record output already exists; use a new path")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record
