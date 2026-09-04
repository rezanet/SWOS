"""Certify the frozen EPG/PROV conversion matrix without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.models import canonical_digest  # noqa: E402
from swos_runtime.prov_interop import epg_to_prov  # noqa: E402
from swos_runtime.prov_model import EPG_VERSION, PROV_PROFILE, ResourceLimits  # noqa: E402
from swos_runtime.prov_validation import canonical_fingerprint, certify_round_trip  # noqa: E402

REQUIRED_CORPUS_CATEGORIES = frozenset(
    {"valid", "invalid", "large", "adversarial", "hostile_blank_node"}
)
ORACLE_MAX_OUTPUT_BYTES = 64 * 1024
ORACLE_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
ORACLE_ENVIRONMENT_KEYS = frozenset(
    {"LANG", "LC_ALL", "PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR", "TZ"}
)
ORACLE_PLACEHOLDERS = ("{artifact}", "{input}", "{profile}", "{formats}", "{output}")


def _read(path: Path, limits: ResourceLimits | None = None) -> bytes:
    if limits is None:
        return path.read_bytes()
    with path.open("rb") as stream:
        raw = stream.read(limits.max_bytes + 1)
    limits.check_bytes(len(raw))
    return raw


def _sha256_bounded_file(path: Path, maximum: int) -> str:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(block)
            if total > maximum:
                raise ValueError("independent oracle artifact exceeds its package-size limit")
            digest.update(block)
    return digest.hexdigest()


def _load_json_with_digest(
    path: Path, limits: ResourceLimits | None = None
) -> tuple[dict[str, Any], str]:
    raw = _read(path, limits)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"PROV certification input must be a JSON object: {path}")
    return dict(payload), hashlib.sha256(raw).hexdigest()


def _load(path: Path, limits: ResourceLimits | None = None) -> dict[str, Any]:
    return _load_json_with_digest(path, limits)[0]


def _load_oracle_manifest(path: Path, limits: ResourceLimits) -> dict[str, Any]:
    """Load oracle evidence and verify the referenced artifact before trusting it."""

    oracle = _load(path, limits)
    status = str(oracle.get("status") or "not_run").lower()
    if status not in {"pass", "passed", "valid", "accepted"}:
        return oracle
    artifact_uri = oracle.get("artifact_uri")
    if not isinstance(artifact_uri, str) or not artifact_uri.strip():
        raise ValueError("accepted oracle manifest requires a local artifact_uri")
    artifact_path = Path(artifact_uri)
    if artifact_path.is_absolute() or "://" in artifact_uri:
        raise ValueError("accepted oracle artifact_uri must be a relative local path")
    manifest_root = path.parent.resolve()
    artifact_path = (manifest_root / artifact_path).resolve()
    if not artifact_path.is_relative_to(manifest_root):
        raise ValueError("accepted oracle artifact_uri escapes its manifest directory")
    if not artifact_path.is_file():
        raise ValueError("accepted oracle artifact does not exist")
    expected_sha256 = oracle.get("artifact_sha256")
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or expected_sha256.lower() != expected_sha256
        or any(character not in "0123456789abcdef" for character in expected_sha256)
    ):
        raise ValueError("accepted oracle manifest requires a lowercase artifact_sha256")
    actual_sha256 = _sha256_bounded_file(artifact_path, ORACLE_MAX_ARTIFACT_BYTES)
    if actual_sha256 != expected_sha256:
        raise ValueError("accepted oracle artifact checksum mismatch")
    command = oracle.get("command")
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(item, str) or not item.strip() for item in command)
    ):
        raise ValueError("accepted oracle manifest requires an execution command")
    missing_placeholders = [
        item for item in ORACLE_PLACEHOLDERS if not any(item in token for token in command)
    ]
    if missing_placeholders:
        raise ValueError(
            "accepted oracle command must bind placeholders: " + ", ".join(missing_placeholders)
        )
    oracle["artifact_verified"] = True
    oracle["verification"] = {
        "status": "verified",
        "method": "sha256-file",
        "artifact_sha256": actual_sha256,
        "execution_status": "not_run",
        "artifact_path": artifact_path.relative_to(manifest_root).as_posix(),
    }
    return oracle


def _capture_stream(stream: Any, maximum: int, result: dict[str, Any], key: str) -> None:
    data = bytearray()
    overflow = False
    while True:
        chunk = stream.read(16 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > maximum:
            overflow = True
            break
    result[key] = (bytes(data[:maximum]), overflow)


def _safe_oracle_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if key.upper() in ORACLE_ENVIRONMENT_KEYS
    }
    environment.update({"PYTHONHASHSEED": "0", "PYTHONNOUSERSITE": "1"})
    return environment


def _local_input_digest(epg: Mapping[str, Any], limits: ResourceLimits) -> str:
    document = epg_to_prov(epg, base_iri=str(epg.get("base_iri") or ""))
    return canonical_fingerprint(document, limits).semantic_digest


def _execute_oracle(
    oracle: Mapping[str, Any],
    *,
    input_path: Path,
    expected_input_digest: str,
    profile_path: Path,
    profile_id: str,
    formats: tuple[str, ...],
    artifact_dir: Path,
    manifest_root: Path,
    limits: ResourceLimits,
) -> dict[str, Any]:
    """Execute the pinned oracle and bind its result to this exact input."""

    command = oracle.get("command")
    if not isinstance(command, list):
        raise ValueError("accepted oracle manifest requires an execution command")
    artifact_path = (manifest_root / str(oracle["artifact_uri"])).resolve()
    output_path = artifact_dir / f"oracle-execution-{expected_input_digest}.json"
    if output_path.exists():
        raise RuntimeError(f"oracle execution output already exists: {output_path}")
    replacements = {
        "{artifact}": str(artifact_path),
        "{input}": str(input_path.resolve()),
        "{profile}": str(profile_path.resolve()),
        "{formats}": ",".join(formats),
        "{output}": str(output_path.resolve()),
    }
    argv = [token for token in command]
    for index, token in enumerate(argv):
        for placeholder, value in replacements.items():
            token = token.replace(placeholder, value)
        argv[index] = token
    command_digest = hashlib.sha256(
        json.dumps(argv, sort_keys=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    captured: dict[str, Any] = {}
    try:
        process = subprocess.Popen(
            argv,
            cwd=manifest_root,
            env=_safe_oracle_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except (OSError, ValueError) as exc:
        raise ValueError(f"unable to execute pinned oracle: {exc}") from exc
    threads = [
        threading.Thread(
            target=_capture_stream,
            args=(stream, ORACLE_MAX_OUTPUT_BYTES, captured, key),
            daemon=True,
        )
        for stream, key in ((process.stdout, "stdout"), (process.stderr, "stderr"))
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + limits.timeout_seconds
    timed_out = False
    while process.poll() is None:
        if any(captured.get(key, (b"", False))[1] for key in ("stdout", "stderr")):
            process.kill()
            break
        if time.monotonic() > deadline:
            timed_out = True
            process.kill()
            break
        time.sleep(0.01)
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=1)
    for thread in threads:
        thread.join(timeout=1)
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            stream.close()
    if timed_out:
        raise ValueError("pinned oracle execution exceeded timeout_seconds")
    if any(captured.get(key, (b"", False))[1] for key in ("stdout", "stderr")):
        raise ValueError("pinned oracle execution exceeded the output limit")
    if process.returncode != 0:
        raise ValueError(f"pinned oracle execution failed with exit code {process.returncode}")
    if not output_path.is_file():
        raise ValueError("pinned oracle execution did not produce its declared output")
    output = _load(output_path, limits)
    if str(output.get("status") or "").lower() not in {"pass", "passed", "valid", "accepted"}:
        raise ValueError("pinned oracle execution did not accept the exact input")
    if output.get("input_digest") != expected_input_digest:
        raise ValueError("pinned oracle output is not bound to the exact input digest")
    if output.get("profile") != profile_id:
        raise ValueError("pinned oracle output is not bound to the exact profile")
    output_formats = output.get("formats")
    if (
        not isinstance(output_formats, list)
        or tuple(str(item) for item in output_formats) != formats
    ):
        raise ValueError("pinned oracle output is not bound to the exact format matrix")
    stdout = captured.get("stdout", (b"", False))[0]
    stderr = captured.get("stderr", (b"", False))[0]
    execution = {
        "status": "passed",
        "exit_code": process.returncode,
        "command_sha256": command_digest,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "output_path": output_path.relative_to(artifact_dir).as_posix(),
    }
    result = dict(oracle)
    result["input_digest"] = expected_input_digest
    result["profile"] = profile_id
    result["formats"] = list(formats)
    result["execution"] = execution
    result["oracle_output"] = output
    result["verification"] = {
        **dict(result.get("verification") or {}),
        "execution_status": "passed",
        "execution_output_sha256": execution["output_sha256"],
    }
    return result


def _limits(path: Path) -> ResourceLimits:
    payload = _load(path)
    values = payload.get("limits")
    if not isinstance(values, Mapping):
        raise ValueError("PROV resource-limits manifest requires an explicit limits object")
    required = ("max_bytes", "max_statements", "max_literal_length", "max_depth", "timeout_seconds")
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError("PROV resource-limits manifest is missing: " + ", ".join(missing))
    integer_keys = ("max_bytes", "max_statements", "max_literal_length", "max_depth")
    if any(type(values[key]) is not int for key in integer_keys):
        raise ValueError("PROV resource-limits integer bounds must be JSON integers")
    if isinstance(values["timeout_seconds"], bool) or not isinstance(
        values["timeout_seconds"], (int, float)
    ):
        raise ValueError("PROV resource-limits timeout_seconds must be a JSON number")
    try:
        return ResourceLimits(
            max_bytes=values["max_bytes"],
            max_statements=values["max_statements"],
            max_literal_length=values["max_literal_length"],
            max_depth=values["max_depth"],
            timeout_seconds=values["timeout_seconds"],
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("PROV resource-limits manifest contains invalid bounds") from exc


def certify(
    *,
    epg_path: Path | None,
    corpus_manifest: Path | None,
    profile_path: Path,
    formats: tuple[str, ...],
    oracle_path: Path,
    limits_path: Path,
    artifact_dir: Path,
    certificate_out: Path,
) -> dict[str, Any]:
    if (epg_path is None) == (corpus_manifest is None):
        raise ValueError("exactly one of --epg and --corpus-manifest is required")
    limits = _limits(limits_path)
    profile = _load(profile_path, limits)
    if profile.get("profile_id") != PROV_PROFILE:
        raise ValueError("PROV profile manifest has an unsupported profile_id")
    oracle = _load_oracle_manifest(oracle_path, limits)
    if tuple(formats) != tuple(dict.fromkeys(formats)):
        raise ValueError("PROV formats must not be duplicated")
    if not set(formats).issubset({"prov-json", "prov-n", "prov-o-trig"}):
        raise ValueError("unsupported PROV format in certification matrix")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if epg_path is not None:
        epg = _load(epg_path, limits)
        if str(oracle.get("status") or "").lower() in {"pass", "passed", "valid", "accepted"}:
            oracle = _execute_oracle(
                oracle,
                input_path=epg_path,
                expected_input_digest=_local_input_digest(epg, limits),
                profile_path=profile_path,
                profile_id=str(profile["profile_id"]),
                formats=formats,
                artifact_dir=artifact_dir,
                manifest_root=oracle_path.parent.resolve(),
                limits=limits,
            )
        certificate = certify_round_trip(epg, formats, oracle=oracle, limits=limits)
        report = certificate.to_dict()
    else:
        manifest, manifest_sha256 = _load_json_with_digest(corpus_manifest, limits)
        cases = manifest.get("cases")
        if not isinstance(cases, list):
            raise ValueError("PROV corpus manifest requires a cases list")
        if manifest.get("schema_version") != EPG_VERSION:
            raise ValueError("PROV corpus manifest requires schema_version=2.0.0")
        if manifest.get("checksum_algorithm") != "sha256":
            raise ValueError("PROV corpus manifest requires checksum_algorithm=sha256")
        if cases:
            if manifest.get("status") != "frozen":
                raise ValueError("PROV corpus manifest status must be frozen for non-empty cases")
            required_categories = manifest.get("required_categories")
            if (
                not isinstance(required_categories, list)
                or not all(isinstance(item, str) for item in required_categories)
                or set(required_categories) != REQUIRED_CORPUS_CATEGORIES
                or len(required_categories) != len(REQUIRED_CORPUS_CATEGORIES)
            ):
                raise ValueError("PROV corpus manifest has incomplete required_categories")
        certificates = []
        bindings = []
        oracle_executions = []
        seen_ids = set()
        seen_categories = set()
        seen_case_paths: set[Path] = set()
        seen_case_sha256 = set()
        root = corpus_manifest.parent.resolve()
        for index, case in enumerate(cases):
            if not isinstance(case, dict) or not isinstance(case.get("epg"), str):
                raise ValueError(f"PROV corpus case {index} lacks an EPG path")
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError(f"PROV corpus case {index} lacks an id")
            if case_id in seen_ids:
                raise ValueError(f"PROV corpus has duplicate case id: {case_id}")
            seen_ids.add(case_id)
            category = case.get("category")
            if not isinstance(category, str) or category not in REQUIRED_CORPUS_CATEGORIES:
                raise ValueError(f"PROV corpus case {index} has an unsupported category")
            seen_categories.add(category)
            case_path = (root / case["epg"]).resolve()
            if not case_path.is_relative_to(root):
                raise ValueError(f"PROV corpus case escapes its manifest directory: {case['epg']}")
            if not case_path.is_file():
                raise ValueError(f"PROV corpus EPG does not exist: {case_path}")
            if case_path in seen_case_paths:
                raise ValueError(f"PROV corpus reuses case path: {case['epg']}")
            seen_case_paths.add(case_path)
            expected_sha256 = case.get("sha256")
            if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
                raise ValueError(f"PROV corpus case {index} lacks a SHA-256 checksum")
            if any(character not in "0123456789abcdef" for character in expected_sha256):
                raise ValueError(f"PROV corpus case {index} has an invalid SHA-256 checksum")
            epg, actual_sha256 = _load_json_with_digest(case_path, limits)
            if actual_sha256 != expected_sha256:
                raise ValueError(f"PROV corpus case checksum mismatch: {case['epg']}")
            if actual_sha256 in seen_case_sha256:
                raise ValueError(f"PROV corpus has duplicate case payload digest: {actual_sha256}")
            seen_case_sha256.add(actual_sha256)
            case_oracle = oracle
            if str(oracle.get("status") or "").lower() in {"pass", "passed", "valid", "accepted"}:
                case_oracle = _execute_oracle(
                    oracle,
                    input_path=case_path,
                    expected_input_digest=_local_input_digest(epg, limits),
                    profile_path=profile_path,
                    profile_id=str(profile["profile_id"]),
                    formats=formats,
                    artifact_dir=artifact_dir,
                    manifest_root=oracle_path.parent.resolve(),
                    limits=limits,
                )
                oracle_executions.append(case_oracle["execution"])
            certificate = certify_round_trip(
                epg, formats, oracle=case_oracle, limits=limits
            ).to_dict()
            certificates.append(certificate)
            bindings.append(
                {
                    "id": str(case.get("id") or index),
                    "epg": case["epg"],
                    "sha256": actual_sha256,
                    "category": category,
                    "source_sha": certificate["source_sha"],
                    "input_digest": certificate["input_digest"],
                }
            )
        if cases and seen_categories != REQUIRED_CORPUS_CATEGORIES:
            missing = sorted(REQUIRED_CORPUS_CATEGORIES - seen_categories)
            raise ValueError("PROV corpus is missing required categories: " + ", ".join(missing))
        statuses = {str(item.get("status")) for item in certificates}
        status = (
            "certified"
            if certificates and statuses == {"certified"}
            else ("failed" if "failed" in statuses else "not_run")
        )
        corpus_binding = {"manifest_sha256": manifest_sha256, "cases": bindings}
        source_sha = canonical_digest(corpus_binding)
        input_digest = canonical_digest(
            {
                "corpus_source_sha": source_sha,
                "case_input_digests": [item["input_digest"] for item in bindings],
            }
        )
        report_oracle = dict(oracle)
        if oracle_executions:
            report_oracle["executions"] = oracle_executions
        report = {
            "certificate_version": "2.0.0",
            "status": status,
            "profile": profile.get("profile_id", "swos.prov-dm-round-trip.v2"),
            "source_sha": source_sha,
            "input_digest": input_digest,
            "paths": list(formats),
            "legs": certificates,
            "oracle": report_oracle,
            "limitations": []
            if status == "certified"
            else ["The corpus or independent oracle is not release-complete."],
            "limits": limits.__dict__,
        }
    if certificate_out.exists():
        raise RuntimeError(f"immutable certificate already exists: {certificate_out}")
    certificate_out.parent.mkdir(parents=True, exist_ok=True)
    certificate_out.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--epg", type=Path)
    source.add_argument("--corpus-manifest", type=Path)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--formats", nargs="+", required=True)
    parser.add_argument("--oracle-manifest", type=Path, required=True)
    parser.add_argument("--limits", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--certificate-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = certify(
            epg_path=args.epg,
            corpus_manifest=args.corpus_manifest,
            profile_path=args.profile,
            formats=tuple(args.formats),
            oracle_path=args.oracle_manifest,
            limits_path=args.limits,
            artifact_dir=args.artifact_dir,
            certificate_out=args.certificate_out,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        TypeError,
        OverflowError,
        json.JSONDecodeError,
    ) as exc:
        print(json.dumps({"status": "not_run", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {"status": result.get("status"), "certificate": str(args.certificate_out)},
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "certified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
