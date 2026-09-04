#!/usr/bin/env python3
"""Fail-closed preflight for T127 portability/approval closure and T128 audit pack.

This script validates evidence that already exists. It cannot create a portability
PASS, maintainer/steward approval, independent exact-head review, hosted CI result,
coverage report, external audit certification, or owner decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED_PORTABILITY = (
    "openai_api",
    "codex_chatgpt_subscription",
    "claude_code_subscription",
    "replay_host_bundle",
    "api_provider_changed",
    "model_changed_same_provider",
)
EXTERNAL_RECORD_SCHEMA = "swos.external-evidence-record.v1"
HEAD_FIELDS = (
    "exact_head",
    "exact_code_head",
    "code_sha",
    "head_sha",
    "candidate_head",
    "reviewed_head",
)
EVIDENCE_MARKER_FIELDS = (
    "status",
    "result",
    "decision",
    "outcome",
    "approval",
    "approvals",
    "review",
    "checks",
    "workflows",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(argv: list[str], root: Path) -> dict[str, Any]:
    p = subprocess.run(
        argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
    )
    return {
        "argv": argv,
        "exit_code": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }


def file_record(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "NOT_SUPPLIED"}
    if path.is_symlink():
        return {"status": "INVALID_SYMLINK", "path": str(path)}
    if not path.is_file():
        return {"status": "MISSING", "path": str(path)}
    return {
        "status": "PRESENT",
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def _head_value(payload: dict[str, Any]) -> str | None:
    for key in HEAD_FIELDS:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        for key in HEAD_FIELDS:
            value = metadata.get(key)
            if isinstance(value, str):
                return value
    return None


def validate_external_record(payload: Any, label: str, expected_head: str | None) -> list[str]:
    """Validate the minimum immutable external-record contract before gate use."""
    failures: list[str] = []
    if not isinstance(payload, dict):
        return [f"{label}: external record must be a JSON object"]
    if payload.get("schema_version") != EXTERNAL_RECORD_SCHEMA:
        failures.append(f"{label}: wrong external record schema_version")
    if not isinstance(payload.get("record_type"), str) or not payload["record_type"]:
        failures.append(f"{label}: missing external record_type")
    actual_head = _head_value(payload)
    if actual_head is None:
        failures.append(f"{label}: missing exact-head binding")
    elif len(actual_head) != 40 or any(c not in "0123456789abcdef" for c in actual_head):
        failures.append(f"{label}: exact-head binding is not a lowercase full Git SHA")
    elif expected_head is not None and actual_head != expected_head:
        failures.append(f"{label}: exact-head binding does not match the candidate head")
    if not any(field in payload for field in EVIDENCE_MARKER_FIELDS):
        failures.append(f"{label}: missing approval/review/CI disposition")
    immutable_uri = payload.get("immutable_uri")
    if not isinstance(immutable_uri, str) or not immutable_uri.startswith("https://"):
        failures.append(f"{label}: missing HTTPS immutable external URI")
    return failures


def external_record(path: Path | None, label: str, expected_head: str | None) -> dict[str, Any]:
    """Load and validate one external evidence record without trusting its presence alone."""
    record = file_record(path)
    if record.get("status") != "PRESENT" or path is None:
        record["validated"] = False
        return record
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        record.update(
            {
                "status": "INVALID",
                "validated": False,
                "validation_failures": [f"{label}: cannot parse JSON: {exc}"],
            }
        )
        return record
    failures = validate_external_record(payload, label, expected_head)
    record.update(
        {
            "status": "PRESENT" if not failures else "INVALID",
            "validated": not failures,
            "validation_failures": failures,
            "schema_version": payload.get("schema_version"),
            "record_type": payload.get("record_type"),
            "bound_exact_head": _head_value(payload),
        }
    )
    return record


def coverage_record(path: Path) -> dict[str, Any]:
    """Require a genuine coverage.py-style report; placeholders are not evidence."""
    record = file_record(path)
    if record.get("status") != "PRESENT":
        record["validated"] = False
        return record
    failures: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"coverage: cannot parse JSON: {exc}")
        payload = None
    if not isinstance(payload, dict):
        failures.append("coverage: report must be a JSON object")
    else:
        if payload.get("status") == "placeholder" or payload.get("placeholder") is True:
            failures.append("coverage: placeholder reports are not accepted")
        if not isinstance(payload.get("meta"), dict):
            failures.append("coverage: missing coverage metadata")
        files = payload.get("files")
        if not isinstance(files, dict) or not files:
            failures.append("coverage: genuine non-empty files map is required")
        totals = payload.get("totals")
        if not isinstance(totals, dict):
            failures.append("coverage: totals object is required")
        else:
            for key in ("covered_lines", "num_statements", "percent_covered"):
                if key not in totals:
                    failures.append(f"coverage: totals.{key} is required")
            percent = totals.get("percent_covered")
            if (
                isinstance(percent, bool)
                or not isinstance(percent, (int, float))
                or not math.isfinite(float(percent))
                or not 0 <= percent <= 100
            ):
                failures.append("coverage: totals.percent_covered must be between 0 and 100")
    record.update(
        {
            "status": "PRESENT" if not failures else "INVALID",
            "validated": not failures,
            "validation_failures": failures,
        }
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--expected-head", default=None)
    parser.add_argument(
        "--approvals-record",
        type=Path,
        default=None,
        help="External immutable record containing the named T127 schema/ontology/fixture/adapter/reviewer-criteria approvals.",
    )
    parser.add_argument("--independent-review-record", type=Path, default=None)
    parser.add_argument("--hosted-ci-record", type=Path, default=None)
    parser.add_argument("--audit-pack", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    root = args.repo.resolve()
    failures: list[str] = []
    head_result = run(["git", "rev-parse", "HEAD"], root)
    head = head_result["stdout"] if head_result["exit_code"] == 0 else None
    if not head:
        failures.append("unable to determine repository HEAD")
    if args.expected_head and head != args.expected_head:
        failures.append(f"exact-head mismatch: {head} != {args.expected_head}")

    evidence_dir = root / "acceptance" / "portability" / "evidence"
    portability_files = {}
    for case_id in EXPECTED_PORTABILITY:
        path = evidence_dir / f"{case_id}.json"
        portability_files[case_id] = file_record(path)
        if portability_files[case_id]["status"] != "PRESENT":
            failures.append(f"portability case missing: {case_id}")
    portability_check = run(
        [sys.executable, "tools/check_portability_acceptance.py", "--release"], root
    )
    if portability_check["exit_code"] != 0:
        failures.append("release portability checker did not pass")

    approvals = external_record(
        args.approvals_record.resolve() if args.approvals_record else None,
        "named T127 approvals",
        head,
    )
    independent_review = external_record(
        args.independent_review_record.resolve() if args.independent_review_record else None,
        "independent exact-head review",
        head,
    )
    hosted_ci = external_record(
        args.hosted_ci_record.resolve() if args.hosted_ci_record else None,
        "hosted CI record",
        head,
    )
    for name, record in (
        ("named T127 approvals", approvals),
        ("independent exact-head review", independent_review),
        ("hosted CI record", hosted_ci),
    ):
        if record["status"] != "PRESENT" or record.get("validated") is not True:
            failures.append(f"{name} is not supplied as an immutable external record")

    coverage = coverage_record(root / "reports" / "coverage.json")
    if coverage["status"] != "PRESENT":
        failures.append("genuine reports/coverage.json is missing; do not create a placeholder")
    elif coverage.get("validated") is not True:
        failures.append("reports/coverage.json is not a genuine coverage report")

    audit_pack = None
    audit_verify = None
    if args.audit_pack:
        pack = args.audit_pack.resolve()
        audit_pack = {"status": "PRESENT" if pack.is_dir() else "MISSING", "path": str(pack)}
        if pack.is_dir():
            argv = [
                sys.executable,
                "tools/assemble_research_grade_audit_pack.py",
                "--verify",
                str(pack),
            ]
            if head:
                argv += ["--expected-code-sha", head]
            audit_verify = run(argv, root)
            if audit_verify["exit_code"] != 0:
                failures.append("strict audit-pack byte verification failed")
        else:
            failures.append("audit pack directory is missing")
    else:
        audit_pack = {"status": "NOT_SUPPLIED"}
        failures.append("final T128 audit pack not supplied")

    report = {
        "schema_version": "research-handoff.t127-t128.preflight.v1",
        "status": "READY_FOR_INDEPENDENT_EXTERNAL_AUDIT" if not failures else "BLOCKED_FAIL_CLOSED",
        "exact_head": head,
        "expected_head": args.expected_head,
        "t127": {
            "portability_records": portability_files,
            "portability_release_check": portability_check,
            "named_approvals_external_record": approvals,
            "hosted_ci_external_record": hosted_ci,
            "independent_exact_head_review_record": independent_review,
        },
        "t128": {
            "coverage": coverage,
            "audit_pack": audit_pack,
            "strict_audit_pack_verification": audit_verify,
            "deterministic_verification": {
                "strict_audit_pack_verification": audit_verify,
                "portability_release_check": portability_check,
            },
            "independent_external_audit_certification": "NOT_RUN",
        },
        "failures": failures,
        "prohibitions": [
            "Do not hand-author portability PASS records.",
            "Do not create placeholder coverage.",
            "Do not self-issue independent review/audit certification.",
            "If the candidate head changes after final review, restart the exact-head T127/T128 sequence.",
        ],
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
