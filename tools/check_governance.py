#!/usr/bin/env python3
"""Validate the governance control plane: policies, gates and crosswalk coverage.

Usage:  python3 tools/check_governance.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / "governance" / "policies"

# The six controls that had to be mechanised. A named control without a policy
# file is governance theatre.
REQUIRED_GATES = {
    "source_rights": "source-rights.policy.json",
    "memory_write_approval": "memory-write.policy.json",
    "human_approval_threshold": "human-approval.policy.json",
    "provenance_completeness": "provenance-completeness.policy.json",
    "release": "release-gate.policy.json",
    "incident_correction": "incident-correction.policy.json",
}

NIST_FUNCTIONS = ("GOVERN", "MAP", "MEASURE", "MANAGE")


def main():
    errors, checked = [], 0

    for gate_type, filename in REQUIRED_GATES.items():
        path = POLICIES / filename
        if not path.exists():
            errors.append(f"MISSING POLICY for required gate '{gate_type}': {filename}")
            continue
        pol = json.loads(path.read_text(encoding="utf-8"))
        checked += 1

        if pol.get("gate_type") != gate_type:
            errors.append(
                f"{filename}: gate_type is '{pol.get('gate_type')}', expected '{gate_type}'"
            )

        if pol.get("default_effect") not in ("deny", "escalate"):
            errors.append(f"{filename}: default_effect must be deny or escalate (fail closed)")

        if not pol.get("rules"):
            errors.append(f"{filename}: no rules defined. A policy with no rules enforces nothing.")

        refs = pol.get("nist_ai_rmf", [])
        if not refs:
            errors.append(
                f"{filename}: no NIST AI RMF references. Gate records must carry them for audit mapping."
            )
        for ref in refs:
            if not any(ref.startswith(fn) for fn in NIST_FUNCTIONS):
                errors.append(f"{filename}: '{ref}' is not a recognised AI RMF function reference")

        if not pol.get("escalation") and pol.get("default_effect") == "deny":
            errors.append(f"{filename}: deny-by-default policy needs an escalation path")

    # Every risk in the register must name a detection method.
    register = (ROOT / "governance" / "risk-register.md").read_text(encoding="utf-8")
    for risk in (
        "Citation laundering",
        "False originality",
        "Over-association",
        "Method blindness",
        "Memory contamination",
        "Evaluation gaming",
        "Privacy and IP exposure",
        "Agent autonomy drift",
    ):
        if risk not in register:
            errors.append(f"risk-register.md: named risk '{risk}' is missing")
    checked += 1

    # The crosswalk must cover all four AI RMF functions.
    crosswalk = (ROOT / "governance" / "nist-ai-rmf-crosswalk.md").read_text(encoding="utf-8")
    for fn in NIST_FUNCTIONS:
        if fn not in crosswalk:
            errors.append(f"nist-ai-rmf-crosswalk.md: function '{fn}' not covered")
    checked += 1

    if errors:
        print(f"FAIL  {len(errors)} governance problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK    {checked} governance artefact(s) validated. All six mechanised controls present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
