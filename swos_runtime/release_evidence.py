"""Exact-commit release evidence assembly and verification."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

from .public_proof import verify_public_proof
from .release_record import verify_release_record

CHECKSUM_FILE = "SHA256SUMS"
RECORD_FILE = "release-record.json"
GATE_FILE = "release-record-gate.json"


class ReleaseEvidenceError(RuntimeError):
    """Raised when release evidence cannot be trusted."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseEvidenceError(f"cannot load {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise ReleaseEvidenceError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def assert_exact_clean_head(repo_root: str | Path, selected_sha: str) -> str:
    repo = Path(repo_root).resolve()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", selected_sha):
        raise ReleaseEvidenceError("selected SHA must be a full 40-character hexadecimal commit")
    head = _git(repo, "rev-parse", "HEAD")
    if head.lower() != selected_sha.lower():
        raise ReleaseEvidenceError("selected SHA does not match exact checkout HEAD")
    if _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ReleaseEvidenceError("release candidate requires a clean checkout")
    _git(repo, "cat-file", "-e", f"{selected_sha}^{{commit}}")
    return head.lower()


def _component_name(requirement: str) -> tuple[str, str | None]:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)\s*(?:==|>=|<=|~=|!=|>|<)?\s*([^;\s,]+)?", requirement)
    if not match:
        raise ReleaseEvidenceError(f"cannot parse dependency declaration: {requirement}")
    return match.group(1).lower().replace("_", "-"), match.group(2)


def generate_sbom(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    pyproject_path = repo / "pyproject.toml"
    lock_path = repo / "requirements-dev.lock"
    if not pyproject_path.is_file() or not lock_path.is_file():
        raise ReleaseEvidenceError(
            "committed pyproject.toml and requirements-dev.lock are required"
        )
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]
    direct = {_component_name(item)[0]: item for item in project.get("dependencies", [])}
    locked: dict[str, str] = {}
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "==" not in stripped:
            raise ReleaseEvidenceError(f"unlocked development dependency: {stripped}")
        name, version = stripped.split("==", 1)
        locked[name.lower().replace("_", "-")] = version
    components = []
    for name, version in sorted(locked.items()):
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "bom-ref": f"pkg:pypi/{name}@{version}",
                "properties": [
                    {"name": "swos:dependency-authority", "value": "requirements-dev.lock"},
                    {
                        "name": "swos:direct-runtime-dependency",
                        "value": str(name in direct).lower(),
                    },
                ],
            }
        )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": project["name"],
                "version": project["version"],
            },
            "properties": [
                {"name": "swos:pyproject-sha256", "value": file_digest(pyproject_path)},
                {"name": "swos:lock-sha256", "value": file_digest(lock_path)},
            ],
        },
        "components": components,
    }


def _payload_files(candidate: Path) -> list[Path]:
    excluded = {CHECKSUM_FILE, GATE_FILE}
    return sorted(
        path for path in candidate.rglob("*") if path.is_file() and path.name not in excluded
    )


def write_checksums(candidate: str | Path) -> Path:
    root = Path(candidate)
    lines = [
        f"{file_digest(path)}  {path.relative_to(root).as_posix()}" for path in _payload_files(root)
    ]
    output = root / CHECKSUM_FILE
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def verify_checksums(candidate: str | Path) -> list[str]:
    root = Path(candidate)
    sums = root / CHECKSUM_FILE
    if not sums.is_file():
        return ["checksum inventory is missing"]
    entries: dict[str, str] = {}
    errors: list[str] = []
    for line in sums.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            errors.append("checksum inventory contains a malformed line")
            continue
        digest, relative = match.groups()
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or "\\" in relative or relative in entries:
            errors.append(f"checksum inventory path is unsafe or duplicated: {relative}")
            continue
        entries[relative] = digest
    expected = {path.relative_to(root).as_posix() for path in _payload_files(root)}
    if set(entries) != expected:
        errors.append("checksum inventory does not exactly cover candidate payload files")
    for relative, digest in entries.items():
        path = root / relative
        if path.is_file() and file_digest(path) != digest:
            errors.append(f"checksum mismatch: {relative}")
    return errors


def build_release_candidate(
    *,
    repo_root: str | Path,
    selected_sha: str,
    proof_dir: str | Path,
    reproduction_path: str | Path,
    release_record_path: str | Path,
    out_dir: str | Path,
    built_at: str,
) -> dict[str, Any]:
    try:
        datetime.fromisoformat(built_at.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ReleaseEvidenceError("built_at must be an ISO 8601 timestamp") from exc

    exact_sha = assert_exact_clean_head(repo_root, selected_sha)
    proof = Path(proof_dir)
    proof_errors = verify_public_proof(proof)
    if proof_errors:
        raise ReleaseEvidenceError("public proof failed: " + "; ".join(proof_errors))
    reproduction = _json(Path(reproduction_path))
    if reproduction.get("decision") != "pass" or reproduction.get("reasons"):
        raise ReleaseEvidenceError("independent public proof reproduction did not pass")
    record_errors = verify_release_record(
        release_record_path,
        selected_sha=exact_sha,
        proof_dir=proof,
        reproduction_path=reproduction_path,
    )
    if record_errors:
        raise ReleaseEvidenceError("release record did not pass: " + "; ".join(record_errors))

    output = Path(out_dir)
    if output.exists():
        raise ReleaseEvidenceError("release candidate output already exists; use a new directory")
    output.mkdir(parents=True)
    public = output / "public-proof"
    shutil.copytree(proof, public, ignore=shutil.ignore_patterns("approval"))
    shutil.copy2(Path(reproduction_path), public / "reproduction-report.json")
    shutil.copy2(Path(release_record_path), output / RECORD_FILE)
    record_gate = {
        "gate_version": "swos.release-record-gate.v1",
        "decision": "allow",
        "selected_sha": exact_sha,
        "release_record": RECORD_FILE,
        "reasons": [],
    }
    _write_json(output / GATE_FILE, record_gate)
    _write_json(output / "sbom.cdx.json", generate_sbom(repo_root))

    inputs = {
        "pyproject.toml": file_digest(Path(repo_root) / "pyproject.toml"),
        "requirements-dev.lock": file_digest(Path(repo_root) / "requirements-dev.lock"),
        "proof-result.json": file_digest(proof / "proof-result.json"),
        "reproduction-report.json": file_digest(Path(reproduction_path)),
        RECORD_FILE: file_digest(Path(release_record_path)),
    }
    provenance = {
        "provenance_version": "swos.build-provenance.v1",
        "selected_sha": exact_sha,
        "repository": "https://github.com/rezanet/SWOS",
        "clean_checkout": True,
        "builder": {"name": "swos-release-evidence", "version": "1.1.0"},
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
        },
        "built_at": built_at,
        "inputs": inputs,
    }
    _write_json(output / "build-provenance.json", provenance)
    conformance = {
        "conformance_version": "swos.conformance.v1",
        "selected_sha": exact_sha,
        "profiles": [
            {
                "profile": "deterministic_pr",
                "status": "passed",
                "evidence": ["public-proof/proof-result.json"],
            },
            {
                "profile": "offline_public_release",
                "status": "passed",
                "evidence": ["public-proof/reproduction-report.json"],
            },
            {"profile": "portability_release", "status": "not_claimed", "evidence": []},
            {"profile": "live_compatible_release", "status": "not_claimed", "evidence": []},
        ],
        "release_record": RECORD_FILE,
        "release_recommendation": "ready_for_public_release",
    }
    _write_json(output / "conformance-report.json", conformance)
    limitations = """# Known Limitations

- Public source evidence is a bounded, hash-pinned snapshot; upstream freshness requires a separate manual refresh check.
- The deterministic provider demonstrates governance and reproducibility, not empirical language-model quality.
- Reviewer execution records truthful limited independence; they do not establish organizational independence.
- Portability release and live-compatible release profiles are not claimed by this candidate.
- Detached package signing is not required for this source release; it remains an optional future enhancement if SWOS distributes packages or gains multiple maintainers.
"""
    (output / "KNOWN-LIMITATIONS.md").write_text(limitations, encoding="utf-8", newline="\n")
    required = [
        "public-proof/proof-result.json",
        "public-proof/project.json",
        "public-proof/evaluation-result.json",
        "public-proof/run/run-manifest.json",
        "public-proof/run/integrity-chain.jsonl",
        "public-proof/reproduction-report.json",
        RECORD_FILE,
        GATE_FILE,
        "sbom.cdx.json",
        "build-provenance.json",
        "conformance-report.json",
        "KNOWN-LIMITATIONS.md",
    ]
    manifest = {
        "candidate_version": "swos.release-candidate.v1",
        "selected_sha": exact_sha,
        "state": "ready_for_public_release",
        "release_record": RECORD_FILE,
        "required_artifacts": required,
        "checksum_file": CHECKSUM_FILE,
    }
    _write_json(output / "candidate-manifest.json", manifest)
    write_checksums(output)
    return manifest


def verify_release_candidate(*, candidate_dir: str | Path) -> dict[str, Any]:
    """Verify a candidate without provider credentials or signing machinery."""

    root = Path(candidate_dir)
    reasons = verify_checksums(root)
    manifest: dict[str, Any] = {}
    try:
        manifest = _json(root / "candidate-manifest.json")
        provenance = _json(root / "build-provenance.json")
        conformance = _json(root / "conformance-report.json")
        sbom = _json(root / "sbom.cdx.json")
        record_gate = _json(root / GATE_FILE)
        public = root / "public-proof"
        reasons.extend(f"public proof: {reason}" for reason in verify_public_proof(public))
        proof_result = _json(public / "proof-result.json")
        reproduction = _json(public / "reproduction-report.json")
        if (
            reproduction.get("decision") != "pass"
            or reproduction.get("reasons")
            or reproduction.get("primary_fingerprint") != proof_result.get("proof_fingerprint")
            or reproduction.get("reproduced_fingerprint") != proof_result.get("proof_fingerprint")
        ):
            reasons.append("independent public proof reproduction does not verify")

        selected = manifest.get("selected_sha")
        reasons.extend(
            f"release record: {reason}"
            for reason in verify_release_record(
                root / RECORD_FILE,
                selected_sha=selected or "",
                proof_dir=public,
                reproduction_path=public / "reproduction-report.json",
            )
        )
        if selected != provenance.get("selected_sha") or selected != conformance.get(
            "selected_sha"
        ):
            reasons.append("candidate selected SHA bindings do not agree")
        if selected != record_gate.get("selected_sha"):
            reasons.append("release record gate selected SHA does not verify")
        if record_gate.get("decision") != "allow":
            reasons.append("release record gate does not allow the candidate")
        if manifest.get("state") != "ready_for_public_release":
            reasons.append("candidate state is invalid")
        if manifest.get("release_record") != RECORD_FILE:
            reasons.append("candidate release record binding is invalid")
        required = set(manifest.get("required_artifacts", []))
        expected_required = {
            "public-proof/proof-result.json",
            "public-proof/project.json",
            "public-proof/evaluation-result.json",
            "public-proof/run/run-manifest.json",
            "public-proof/run/integrity-chain.jsonl",
            "public-proof/reproduction-report.json",
            RECORD_FILE,
            GATE_FILE,
            "sbom.cdx.json",
            "build-provenance.json",
            "conformance-report.json",
            "KNOWN-LIMITATIONS.md",
        }
        if required != expected_required:
            reasons.append("candidate required artifact set is invalid")
        if not required or any(not (root / path).is_file() for path in required):
            reasons.append("candidate required artifact set is incomplete")
        profiles = {item.get("profile"): item for item in conformance.get("profiles", [])}
        for profile in ("deterministic_pr", "offline_public_release"):
            if profiles.get(profile, {}).get("status") != "passed":
                reasons.append(f"required conformance profile did not pass: {profile}")
        for profile in ("portability_release", "live_compatible_release"):
            if profiles.get(profile, {}).get("status") != "not_claimed":
                reasons.append(f"unsupported conformance profile was overclaimed: {profile}")
        if sbom.get("bomFormat") != "CycloneDX" or not sbom.get("components"):
            reasons.append("CycloneDX SBOM is missing or empty")
        limitations = root / "KNOWN-LIMITATIONS.md"
        if not limitations.is_file() or not limitations.read_text(encoding="utf-8").strip():
            reasons.append("known-limitations statement is empty")
    except (ReleaseEvidenceError, OSError, TypeError) as exc:
        reasons.append(str(exc))

    record: dict[str, Any] = {}
    try:
        record = _json(root / RECORD_FILE)
    except ReleaseEvidenceError:
        pass
    approved_by = record.get("approved_by", {}) if isinstance(record, dict) else {}
    return {
        "gate_version": "swos.release-candidate-verifier.v1",
        "decision": "deny" if reasons else "allow",
        "selected_sha": manifest.get("selected_sha"),
        "approved_by": approved_by.get("id") if isinstance(approved_by, dict) else None,
        "reasons": sorted(set(reasons)),
    }
