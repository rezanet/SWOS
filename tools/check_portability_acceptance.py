#!/usr/bin/env python3
"""Validate SWOS v2 portability matrix definitions and accumulated acceptance evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

MATRIX = Path("acceptance/portability/matrix-v1.json")
EVIDENCE_DIR = Path("acceptance/portability/evidence")
EXPECTED_CASES = {
    "openai_api",
    "codex_chatgpt_subscription",
    "claude_code_subscription",
    "replay_host_bundle",
    "api_provider_changed",
    "model_changed_same_provider",
}
EXPECTED_OUTCOMES = {
    "valid_evidence_matrix",
    "valid_argument_graph",
    "verified_citations",
    "required_counter_evidence",
    "review_completed",
    "correct_scholarly_state_transitions",
    "no_unsupported_release",
    "complete_audit_package",
    "valid_integrity_chain",
    "correct_provenance",
    "approved_only_when_swos_requirements_pass",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _record_hash(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("record_sha256", None)
    return _canonical_hash(payload)


def _case_map(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in matrix.get("cases", [])
        if isinstance(item, dict) and item.get("id")
    }


def _validate_matrix(matrix: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if matrix.get("contract_id") != "swos.portability-acceptance.v1":
        failures.append("wrong portability contract_id")
    if matrix.get("status") != "frozen":
        failures.append("portability matrix is not frozen")
    if matrix.get("principle") != "SWOS owns the scholarly process. Models provide capabilities.":
        failures.append("constitutional portability principle changed")
    if matrix.get("equivalence_rule", {}).get("identical_article_text_required") is not False:
        failures.append("matrix incorrectly requires identical article text")

    outcomes = set(
        matrix.get("equivalence_rule", {}).get("required_governed_outcomes") or []
    )
    if outcomes != EXPECTED_OUTCOMES:
        failures.append(
            "governed equivalence outcomes differ from the hard v2 acceptance contract"
        )

    cases = _case_map(matrix)
    if set(cases) != EXPECTED_CASES:
        failures.append("portability matrix must contain exactly the six frozen acceptance cases")
    for case_id, case in cases.items():
        if case.get("expected") != "PASS":
            failures.append(f"{case_id} does not require PASS")

    gates = matrix.get("gates", {})
    if set(gates.get("G-HOST", {}).get("required_cases", [])) != {
        "openai_api",
        "codex_chatgpt_subscription",
    }:
        failures.append("G-HOST does not require API baseline + Codex subscription")
    if set(gates.get("G-PORT", {}).get("required_cases", [])) != {
        "claude_code_subscription",
        "replay_host_bundle",
        "api_provider_changed",
        "model_changed_same_provider",
    }:
        failures.append("G-PORT does not require the four frozen portability cases")
    return failures


def _validate_execution_constraint(
    case_id: str,
    case: dict[str, Any],
    record: dict[str, Any],
    records: dict[str, dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    execution = record.get("execution", {})
    constraints = case.get("constraints", {})

    for key in ("execution_mode", "api_key_used", "paid_api_calls"):
        if key in constraints and execution.get(key) != constraints[key]:
            failures.append(
                f"{case_id}: execution {key}={execution.get(key)!r}; expected {constraints[key]!r}"
            )

    family = constraints.get("adapter_family")
    if family and family.lower() not in str(execution.get("adapter") or "").lower():
        failures.append(f"{case_id}: adapter does not match required family {family!r}")

    different_adapter = constraints.get("adapter_must_differ_from_case")
    if different_adapter and different_adapter in records:
        if execution.get("adapter") == records[different_adapter].get("execution", {}).get("adapter"):
            failures.append(f"{case_id}: adapter did not change from {different_adapter}")

    same_provider = constraints.get("provider_must_match_case")
    if same_provider and same_provider in records:
        if execution.get("model_host") != records[same_provider].get("execution", {}).get("model_host"):
            failures.append(f"{case_id}: provider/host differs from {same_provider}")

    different_model = constraints.get("model_must_differ_from_case")
    if different_model and different_model in records:
        if execution.get("model") == records[different_model].get("execution", {}).get("model"):
            failures.append(f"{case_id}: model did not change from {different_model}")

    if case.get("api_key_policy") == "forbidden":
        environment = record.get("environment", {})
        if environment.get("forbidden_environment_variables_absent") is not True:
            failures.append(f"{case_id}: provider API credential absence was not proved")
        if environment.get("api_credit_dependency") is not False:
            failures.append(f"{case_id}: run still declares an API-credit dependency")

    return failures


def _validate_record(
    case_id: str,
    case: dict[str, Any],
    record: dict[str, Any],
    matrix: dict[str, Any],
    records: dict[str, dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    if record.get("record_version") != "swos.portability-evidence.v1":
        failures.append(f"{case_id}: wrong evidence record version")
    if record.get("contract_id") != matrix.get("contract_id"):
        failures.append(f"{case_id}: evidence record contract mismatch")
    if record.get("case_id") != case_id:
        failures.append(f"{case_id}: evidence record case mismatch")
    if record.get("result") != "PASS" or record.get("expected") != "PASS":
        failures.append(f"{case_id}: evidence is not PASS")
    if record.get("record_sha256") != _record_hash(record):
        failures.append(f"{case_id}: evidence record hash does not verify")

    request_hash = _canonical_hash(matrix.get("canonical_request", {}))
    if record.get("canonical_request_sha256") != request_hash:
        failures.append(f"{case_id}: canonical request fingerprint mismatch")
    if not record.get("run_manifest_sha256") or not record.get("integrity_final_hash"):
        failures.append(f"{case_id}: missing run-manifest or integrity-chain fingerprint")

    validation = record.get("validation", {})
    if validation.get("canonical_validator_passed") is not True:
        failures.append(f"{case_id}: canonical run validator did not pass")
    if validation.get("manifest_status") != "APPROVED" or validation.get("control_status") != "APPROVED":
        failures.append(f"{case_id}: governed run was not APPROVED")
    governed = validation.get("governed_outcomes", {})
    for outcome in EXPECTED_OUTCOMES:
        if governed.get(outcome) is not True:
            failures.append(f"{case_id}: governed outcome {outcome!r} was not proved")

    failures.extend(_validate_execution_constraint(case_id, case, record, records))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE_DIR)
    parser.add_argument("--definitions-only", action="store_true")
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()

    if args.definitions_only and args.release:
        parser.error("choose either --definitions-only or --release")

    matrix = _load(args.matrix)
    failures = _validate_matrix(matrix)
    cases = _case_map(matrix)
    records: dict[str, dict[str, Any]] = {}

    for case_id in sorted(EXPECTED_CASES):
        path = args.evidence_dir / f"{case_id}.json"
        if path.is_file():
            records[case_id] = _load(path)
        elif args.release:
            failures.append(f"{case_id}: required PASS evidence record is missing")

    for case_id, record in records.items():
        failures.extend(_validate_record(case_id, cases[case_id], record, matrix, records))

    gate_status: dict[str, bool] = {}
    for gate_name, gate in matrix.get("gates", {}).items():
        required = list(gate.get("required_cases") or [])
        gate_status[gate_name] = all(
            case_id in records and records[case_id].get("result") == "PASS"
            for case_id in required
        )
        if args.release and not gate_status[gate_name]:
            failures.append(f"{gate_name}: hard portability gate is not satisfied")

    if failures:
        print("SWOS PORTABILITY ACCEPTANCE: FAIL")
        for failure in failures:
            print(f"- {failure}")
        print(
            "gate_status="
            + json.dumps(gate_status, sort_keys=True, separators=(",", ":"))
        )
        return 1

    mode = "RELEASE" if args.release else "DEFINITIONS"
    print(f"SWOS PORTABILITY ACCEPTANCE: PASS ({mode})")
    print(
        "gate_status="
        + json.dumps(gate_status, sort_keys=True, separators=(",", ":"))
    )
    if not args.release:
        missing = sorted(EXPECTED_CASES - set(records))
        if missing:
            print("pending_evidence=" + ",".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
