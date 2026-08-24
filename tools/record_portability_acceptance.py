#!/usr/bin/env python3
"""Create a tamper-evident portability evidence record from a validated SWOS run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from tools.validate_autonomous_run import CANONICAL_REQUEST, load, validate_run

DEFAULT_MATRIX = Path("acceptance/portability/matrix-v1.json")
DEFAULT_EVIDENCE_DIR = Path("acceptance/portability/evidence")


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case(matrix: dict[str, Any], case_id: str) -> dict[str, Any]:
    for item in matrix.get("cases", []):
        if item.get("id") == case_id:
            return item
    raise ValueError(f"unknown portability case: {case_id}")


def _model_from_run(root: Path, control: dict[str, Any]) -> str:
    for item in reversed(control.get("capability_events", [])):
        model = (item.get("provenance") or {}).get("model")
        if model:
            return str(model)
    provenance = load(root / "provenance.json")
    for item in provenance.get("agents", []):
        if item.get("agent_kind") == "model" and item.get("label"):
            return str(item["label"])
    return "unreported-model"


def _integrity_final_hash(path: Path) -> str:
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not entries or not entries[-1].get("hash"):
        raise ValueError("integrity chain has no final hash")
    return str(entries[-1]["hash"])


def _load_reference(case_id: str, evidence_dir: Path) -> dict[str, Any]:
    path = evidence_dir / f"{case_id}.json"
    if not path.is_file():
        raise ValueError(
            f"reference portability evidence {case_id!r} must exist before this case can be recorded"
        )
    return load(path)


def _check_case_constraints(
    case: dict[str, Any],
    execution: dict[str, Any],
    *,
    evidence_dir: Path,
) -> None:
    constraints = case.get("constraints", {})
    if "execution_mode" in constraints and execution.get("execution_mode") != constraints["execution_mode"]:
        raise ValueError(
            f"execution_mode={execution.get('execution_mode')!r}; expected {constraints['execution_mode']!r}"
        )
    if "api_key_used" in constraints and execution.get("api_key_used") is not constraints["api_key_used"]:
        raise ValueError(
            f"api_key_used={execution.get('api_key_used')!r}; expected {constraints['api_key_used']!r}"
        )
    if "paid_api_calls" in constraints and execution.get("paid_api_calls") != constraints["paid_api_calls"]:
        raise ValueError(
            f"paid_api_calls={execution.get('paid_api_calls')!r}; expected {constraints['paid_api_calls']!r}"
        )
    family = constraints.get("adapter_family")
    if family and family.lower() not in str(execution.get("adapter") or "").lower():
        raise ValueError(
            f"adapter {execution.get('adapter')!r} does not identify required family {family!r}"
        )

    different_adapter = constraints.get("adapter_must_differ_from_case")
    if different_adapter:
        reference = _load_reference(str(different_adapter), evidence_dir)
        if execution.get("adapter") == reference.get("execution", {}).get("adapter"):
            raise ValueError("provider-change case reused the baseline adapter")

    same_provider = constraints.get("provider_must_match_case")
    if same_provider:
        reference = _load_reference(str(same_provider), evidence_dir)
        if execution.get("model_host") != reference.get("execution", {}).get("model_host"):
            raise ValueError("model-swap case did not preserve the baseline provider/host")

    different_model = constraints.get("model_must_differ_from_case")
    if different_model:
        reference = _load_reference(str(different_model), evidence_dir)
        if execution.get("model") == reference.get("execution", {}).get("model"):
            raise ValueError("model-swap case reused the baseline model")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    matrix = load(args.matrix)
    case = _case(matrix, args.case_id)
    failures = validate_run(args.run_dir, canonical=True)
    if failures:
        print("PORTABILITY EVIDENCE: REFUSED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    forbidden_env = list(case.get("forbidden_environment_variables") or [])
    present = [name for name in forbidden_env if os.environ.get(name)]
    if present:
        print("PORTABILITY EVIDENCE: REFUSED")
        print("- forbidden provider API credential(s) are present: " + ", ".join(present))
        return 1

    control = load(args.run_dir / "run-control.json")
    manifest = load(args.run_dir / "run-manifest.json")
    execution = dict(control.get("execution") or {})
    execution["model"] = _model_from_run(args.run_dir, control)

    try:
        _check_case_constraints(case, execution, evidence_dir=args.evidence_dir)
    except ValueError as exc:
        print("PORTABILITY EVIDENCE: REFUSED")
        print(f"- {exc}")
        return 1

    required_outcomes = list(
        matrix.get("equivalence_rule", {}).get("required_governed_outcomes") or []
    )
    record = {
        "record_version": "swos.portability-evidence.v1",
        "contract_id": matrix.get("contract_id"),
        "case_id": args.case_id,
        "expected": case.get("expected"),
        "result": "PASS",
        "canonical_request_sha256": _canonical_hash(CANONICAL_REQUEST),
        "run_id": control.get("run_id"),
        "work_id": control.get("work_id"),
        "run_manifest_sha256": _file_hash(args.run_dir / "run-manifest.json"),
        "integrity_final_hash": _integrity_final_hash(args.run_dir / "integrity-chain.jsonl"),
        "execution": execution,
        "environment": {
            "forbidden_environment_variables": forbidden_env,
            "forbidden_environment_variables_absent": True,
            "api_credit_dependency": False
            if case.get("api_key_policy") == "forbidden"
            else "not_applicable",
        },
        "validation": {
            "canonical_validator_passed": True,
            "governed_outcomes": {name: True for name in required_outcomes},
            "manifest_status": manifest.get("status"),
            "control_status": control.get("status"),
        },
    }
    record["record_sha256"] = _canonical_hash(record)

    output = args.output or args.evidence_dir / f"{args.case_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PORTABILITY EVIDENCE: PASS -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
