#!/usr/bin/env python3
"""Evaluate a SWOS governance policy against a runtime context.

The runner is intentionally small and deterministic: it loads one frozen policy,
evaluates its rules against a JSON context, and emits a governance-gate record.

Usage:
  python3 tools/run_gate.py --policy governance/policies/release-gate.policy.json \
    --context examples/worked-example/gate-context.json --work-id work-123 \
    --gate-id gate-123 --evaluated-by swos-governance-officer
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

RECOGNISED_RULE_EFFECTS = {"allow", "continue", "deny", "escalate", "require_approval", "require"}
RECOGNISED_CONDITION_OPS = {"equals", "in", "not_in", "exists", "min_items", "max_items", "gt", "gte", "lt", "lte"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def resolve_path(data: Any, dotted_path: str) -> tuple[bool, Any]:
    current = data
    for segment in dotted_path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return False, None
    return True, current


def is_condition_mapping(value: Any) -> bool:
    return isinstance(value, dict) and any(key in RECOGNISED_CONDITION_OPS for key in value)


def compare_condition(actual: Any, condition: Any) -> tuple[bool, str | None]:
    if isinstance(condition, dict):
        if "exists" in condition:
            expected = bool(condition["exists"])
            present = actual is not None
            return present is expected, None if present is expected else f"exists={expected}"
        if "equals" in condition:
            expected = condition["equals"]
            return actual == expected, None if actual == expected else f"equals {expected!r}"
        if "in" in condition:
            allowed = condition["in"]
            if isinstance(actual, list):
                passed = any(item in allowed for item in actual)
            else:
                passed = actual in allowed
            return passed, None if passed else f"in {allowed!r}"
        if "not_in" in condition:
            disallowed = condition["not_in"]
            if isinstance(actual, list):
                passed = all(item not in disallowed for item in actual)
            else:
                passed = actual not in disallowed
            return passed, None if passed else f"not_in {disallowed!r}"
        if "min_items" in condition:
            minimum = int(condition["min_items"])
            passed = isinstance(actual, list) and len(actual) >= minimum
            return passed, None if passed else f"min_items {minimum}"
        if "max_items" in condition:
            maximum = int(condition["max_items"])
            passed = isinstance(actual, list) and len(actual) <= maximum
            return passed, None if passed else f"max_items {maximum}"
        if "gt" in condition:
            threshold = condition["gt"]
            passed = actual is not None and actual > threshold
            return passed, None if passed else f"gt {threshold!r}"
        if "gte" in condition:
            threshold = condition["gte"]
            passed = actual is not None and actual >= threshold
            return passed, None if passed else f"gte {threshold!r}"
        if "lt" in condition:
            threshold = condition["lt"]
            passed = actual is not None and actual < threshold
            return passed, None if passed else f"lt {threshold!r}"
        if "lte" in condition:
            threshold = condition["lte"]
            passed = actual is not None and actual <= threshold
            return passed, None if passed else f"lte {threshold!r}"

        if not isinstance(actual, dict):
            return False, "nested condition expected object"
        for key, nested_condition in condition.items():
            nested_present, nested_actual = resolve_path(actual, key)
            if not nested_present:
                return False, key
            passed, detail = compare_condition(nested_actual, nested_condition)
            if not passed:
                return False, detail or key
        return True, None

    return actual == condition, None if actual == condition else f"equals {condition!r}"


def condition_matches(context: dict[str, Any], when_clause: dict[str, Any]) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    for path, expected in when_clause.items():
        present, actual = resolve_path(context, path)
        if is_condition_mapping(expected):
            passed, _ = compare_condition(actual if present else None, expected)
            if not passed:
                return False, evidence
            evidence.append(f"{path} satisfies {json.dumps(expected, sort_keys=True)}")
            continue

        if isinstance(expected, dict):
            passed, _ = compare_condition(actual if present else None, expected)
            if not passed:
                return False, evidence
            evidence.append(f"{path} satisfies {json.dumps(expected, sort_keys=True)}")
            continue

        if not present or actual != expected:
            return False, evidence
        evidence.append(f"{path} = {expected!r}")

    return True, evidence


def validate_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("policy_id", "version", "gate_type", "default_effect", "rules", "nist_ai_rmf"):
        if field not in policy:
            errors.append(f"policy missing required field: {field}")
    if policy.get("default_effect") not in ("deny", "escalate"):
        errors.append("policy default_effect must be deny or escalate")
    if not isinstance(policy.get("rules"), list) or not policy["rules"]:
        errors.append("policy must contain at least one rule")
    for index, rule in enumerate(policy.get("rules", []), start=1):
        if not isinstance(rule, dict):
            errors.append(f"rule {index} is not an object")
            continue
        if "id" not in rule or "when" not in rule or "effect" not in rule:
            errors.append(f"rule {index} missing id/when/effect")
            continue
        if rule["effect"] not in RECOGNISED_RULE_EFFECTS:
            errors.append(f"rule {rule['id']}: unsupported effect {rule['effect']!r}")
        if not isinstance(rule["when"], dict) or not rule["when"]:
            errors.append(f"rule {rule['id']}: when clause must be a non-empty object")
    return errors


def evaluate_policy(policy: dict[str, Any], context: dict[str, Any], *, gate_id: str, work_id: str, evaluated_by: str) -> dict[str, Any]:
    evidence: list[str] = []
    final_result = "pass"
    waiver = context.get("waiver")
    approval = context.get("approval")
    matched_any_rule = False

    for rule in policy["rules"]:
        matched, rule_evidence = condition_matches(context, rule["when"])
        if not matched:
            continue

        matched_any_rule = True
        rule_id = rule["id"]
        effect = rule["effect"]
        reason = rule.get("reason") or rule.get("else", {}).get("reason") or f"rule {rule_id} matched"
        evidence.extend([f"{rule_id}: {item}" for item in rule_evidence] or [f"{rule_id}: matched"])

        if effect in {"allow", "continue"}:
            continue

        if effect == "require":
            required_fields = rule.get("requires", [])
            missing_fields = [field for field in required_fields if not resolve_path(context, field)[0]]
            if missing_fields:
                final_result = "fail"
                evidence.append(f"{rule_id}: required fields missing - {', '.join(missing_fields)}")
                break
            evidence.append(f"{rule_id}: required fields present")
            continue

        if effect == "deny":
            final_result = "fail"
            evidence.append(f"{rule_id}: denied - {reason}")
            break

        if effect in {"escalate", "require_approval"}:
            if approval and approval.get("approved"):
                evidence.append(f"{rule_id}: approval recorded")
                continue
            final_result = "escalated"
            evidence.append(f"{rule_id}: escalation required - {reason}")
            break

    if final_result == "pass" and policy.get("default_effect") == "deny" and not matched_any_rule:
        final_result = "fail"
        evidence.append("default_effect: deny")

    if final_result == "pass" and waiver:
        required_fields = ("reason", "approved_by", "expires_on", "sdl_decision_id")
        if all(field in waiver for field in required_fields):
            final_result = "waived"
            evidence.append("waiver: valid waiver record present")

    record: dict[str, Any] = {
        "schema_version": policy.get("version", "1.0.0"),
        "gate_id": gate_id,
        "gate_type": policy["gate_type"],
        "work_id": work_id,
        "policy_id": policy["policy_id"],
        "policy_version": policy.get("version", "1.0.0"),
        "nist_ai_rmf_refs": list(policy.get("nist_ai_rmf", [])),
        "result": final_result,
        "evidence": evidence,
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evaluated_by": {"actor_type": "agent", "actor_id": evaluated_by},
    }

    if final_result == "waived" and waiver:
        record["waiver"] = waiver

    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a SWOS governance policy.")
    parser.add_argument("--policy", required=True, help="Path to a frozen governance policy JSON file")
    parser.add_argument("--context", required=True, help="Path to the runtime context JSON file")
    parser.add_argument("--gate-id", default="gate-00000000-0000-4000-8000-000000000000")
    parser.add_argument("--work-id", required=True)
    parser.add_argument("--evaluated-by", default="swos-governance-officer")
    parser.add_argument("--out", default=None, help="Write the gate record to a file")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = (ROOT / policy_path).resolve()
    context_path = Path(args.context)
    if not context_path.is_absolute():
        context_path = (ROOT / context_path).resolve()

    policy = load_json(policy_path)
    context = load_json(context_path)

    errors = validate_policy(policy)
    if errors:
        print("FAIL  policy validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    record = evaluate_policy(
        policy,
        context,
        gate_id=args.gate_id,
        work_id=args.work_id,
        evaluated_by=args.evaluated_by,
    )

    payload = json.dumps(record, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload)

    if record["result"] in {"pass", "waived", "not_applicable"}:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())