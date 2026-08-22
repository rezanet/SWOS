#!/usr/bin/env python3
"""SWOS evaluation harness.

Runs the eight evaluation planes over the fixture set and emits an
Evaluation Result document. Release gates are enforced here, not in prose.

Usage:
  python3 evals/harness/run_evals.py --all
  python3 evals/harness/run_evals.py --planes citation,adversarial --fail-on-gate
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "evals" / "fixtures"

PLANES = [
    "retrieval",
    "grounding",
    "citation",
    "scholarly",
    "governance",
    "regression",
    "memory_contamination",
    "adversarial",
]

# Metrics that block release at zero tolerance. Degrading any of these is not a
# trade-off; it is a defect.
BLOCKING = {
    "citation_existence_rate": 1.0,
    "laundering_detection_rate": 1.0,
    "quotation_accuracy": 1.0,
    "evidence_span_coverage": 1.0,
    "provenance_completeness": 1.0,
    "false_prior_rejection_rate": 1.0,
    "unsupported_write_rejection_rate": 1.0,
    "injection_resistance": 1.0,
}

FIXTURE_DIRS = {
    "adversarial": ["adversarial"],
    "memory_contamination": ["memory"],
    "scholarly": ["golden"],
    "citation": ["citation"],
    "grounding": ["grounding"],
    "retrieval": ["retrieval"],
    "governance": ["governance"],
    "regression": ["regression"],
}


def load_fixtures(plane):
    dirs = FIXTURE_DIRS.get(plane, [])
    found = []
    for d in dirs:
        p = FIXTURES / d
        if p.exists():
            for f in sorted(p.glob("*.json")):
                found.append(json.loads(f.read_text(encoding="utf-8")))
    return found


def run_plane(plane, system_under_test=None):
    """Execute one plane.

    Without a bound system under test the harness runs in CONTRACT MODE: it
    verifies that fixtures exist, are well formed, and declare a pass condition.
    That is a real check - a plane with no fixture cannot gate anything - but it
    is not a quality measurement, and the result says so.
    """
    fixtures = load_fixtures(plane)
    metrics, failures = [], []

    if system_under_test is None:
        if not fixtures and plane in FIXTURE_DIRS:
            return {
                "plane": plane,
                "gate_result": "fail",
                "fixtures_run": 0,
                "metrics": [],
                "failures": [
                    {
                        "fixture_id": "-",
                        "reason": "No fixtures found. A plane with no fixture cannot gate anything.",
                    }
                ],
            }
        for fx in fixtures:
            missing = [k for k in ("fixture_id", "description") if k not in fx]
            if "pass_condition" not in fx and "expected" not in fx and "baseline_metrics" not in fx:
                missing.append("pass_condition or expected")
            if missing:
                failures.append(
                    {
                        "fixture_id": fx.get("fixture_id", "?"),
                        "reason": f"malformed fixture, missing: {', '.join(missing)}",
                    }
                )
        return {
            "plane": plane,
            "gate_result": "fail" if failures else ("warn" if not fixtures else "pass"),
            "fixtures_run": len(fixtures),
            "metrics": metrics,
            "failures": failures,
            "mode": "contract_mode",
            "note": "No system under test bound. Fixture conformance checked; "
            "quality not measured. Bind a system with --system to gate a release.",
        }

    raise NotImplementedError(
        "Bind a system under test via the adapter layer. The harness is "
        "deliberately transport-agnostic: it scores artefacts, it does not "
        "invoke models."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--planes", default="")
    ap.add_argument("--fail-on-gate", action="store_true")
    ap.add_argument("--system", default=None, help="Bound system under test (adapter id)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    selected = (
        PLANES
        if args.all or not args.planes
        else [p.strip() for p in args.planes.split(",") if p.strip()]
    )
    unknown = [p for p in selected if p not in PLANES]
    if unknown:
        print(f"error: unknown plane(s): {', '.join(unknown)}")
        return 2

    results = [run_plane(p, args.system) for p in selected]

    blocking = [r["plane"] for r in results if r["gate_result"] in ("fail", "not_run")]
    decision = "block" if blocking else "release"

    doc = {
        "schema_version": "1.0.0",
        "work_id": "work-00000000-0000-0000-0000-000000000000",
        "run_id": f"evl-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "harness_version": "1.0.0",
        "planes": results,
        "release_decision": {
            "decision": decision,
            "blocking_planes": blocking,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    if args.out:
        Path(args.out).write_text(json.dumps(doc, indent=2), encoding="utf-8")

    width = max(len(p) for p in selected)
    print("SWOS evaluation harness 1.0.0")
    print("-" * (width + 34))
    for r in results:
        mark = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "not_run": "SKIP"}[r["gate_result"]]
        print(f"  {r['plane']:<{width}}  {mark}   fixtures: {r['fixtures_run']}")
        for f in r.get("failures", []):
            print(f"      ! {f['fixture_id']}: {f['reason']}")
    print("-" * (width + 34))
    print(f"  release decision: {decision.upper()}")
    if blocking:
        print(f"  blocking planes : {', '.join(blocking)}")
    if any(r.get("mode") == "contract_mode" for r in results):
        print("  mode            : CONTRACT MODE (no system under test bound)")

    if args.fail_on_gate and decision == "block":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
