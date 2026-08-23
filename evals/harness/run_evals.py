#!/usr/bin/env python3
"""SWOS eight-plane evaluation harness.

Contract mode checks fixture conformance. `--system autonomous-swos` binds the
same fixtures to production Autonomous SWOS controls and is the release mode used
by CI for the reference runtime.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
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
    found = []
    for dirname in FIXTURE_DIRS.get(plane, []):
        directory = FIXTURES / dirname
        if directory.exists():
            for path in sorted(directory.glob("*.json")):
                found.append(json.loads(path.read_text(encoding="utf-8")))
    return found


def _contract_plane(plane, fixtures):
    failures = []
    if not fixtures and plane in FIXTURE_DIRS:
        return {
            "plane": plane,
            "gate_result": "fail",
            "fixtures_run": 0,
            "metrics": [],
            "failures": [{"fixture_id": "-", "reason": "No fixtures found."}],
            "mode": "contract_mode",
        }
    for fixture in fixtures:
        missing = [key for key in ("fixture_id", "description") if key not in fixture]
        if not any(key in fixture for key in ("pass_condition", "expected", "baseline_metrics")):
            missing.append("pass_condition or expected")
        if missing:
            failures.append(
                {
                    "fixture_id": fixture.get("fixture_id", "?"),
                    "reason": f"malformed fixture, missing: {', '.join(missing)}",
                }
            )
    return {
        "plane": plane,
        "gate_result": "fail" if failures else ("warn" if not fixtures else "pass"),
        "fixtures_run": len(fixtures),
        "metrics": [],
        "failures": failures,
        "mode": "contract_mode",
        "note": "Fixture conformance only; quality is not measured without a bound system.",
    }


def _bound_plane(plane, fixtures, system_under_test):
    if system_under_test != "autonomous-swos":
        return {
            "plane": plane,
            "gate_result": "fail",
            "fixtures_run": 0,
            "metrics": [],
            "failures": [
                {"fixture_id": "-", "reason": f"Unknown system adapter: {system_under_test}"}
            ],
            "mode": "bound_sut",
        }
    from evals.harness.autonomous_sut import evaluate_fixture

    observations = [evaluate_fixture(plane, fixture) for fixture in fixtures]
    failures = [
        {"fixture_id": item["fixture_id"], "reason": item["observation"]}
        for item in observations
        if not item["passed"]
    ]
    return {
        "plane": plane,
        "gate_result": "fail" if failures or not fixtures else "pass",
        "fixtures_run": len(fixtures),
        "metrics": [
            {
                "metric": "bound_fixture_pass_rate",
                "value": (sum(1 for item in observations if item["passed"]) / len(observations))
                if observations
                else 0.0,
            }
        ],
        "failures": failures,
        "observations": observations,
        "mode": "bound_sut",
        "system": system_under_test,
    }


def run_plane(plane, system_under_test=None):
    fixtures = load_fixtures(plane)
    if system_under_test is None:
        return _contract_plane(plane, fixtures)
    return _bound_plane(plane, fixtures, system_under_test)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--planes", default="")
    parser.add_argument("--fail-on-gate", action="store_true")
    parser.add_argument("--system", default=None, help="Bound system under test adapter id")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    selected = (
        PLANES
        if args.all or not args.planes
        else [p.strip() for p in args.planes.split(",") if p.strip()]
    )
    unknown = [plane for plane in selected if plane not in PLANES]
    if unknown:
        print(f"error: unknown plane(s): {', '.join(unknown)}")
        return 2

    results = [run_plane(plane, args.system) for plane in selected]
    blocking = [
        result["plane"] for result in results if result["gate_result"] in ("fail", "not_run")
    ]
    decision = "block" if blocking else "release"
    document = {
        "schema_version": "1.0.0",
        "work_id": "work-00000000-0000-0000-0000-000000000000",
        "run_id": f"evl-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "harness_version": "1.1.0",
        "system_under_test": args.system,
        "planes": results,
        "release_decision": {
            "decision": decision,
            "blocking_planes": blocking,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    if args.out:
        Path(args.out).write_text(json.dumps(document, indent=2), encoding="utf-8")

    width = max(len(plane) for plane in selected)
    print("SWOS evaluation harness 1.1.0")
    print("-" * (width + 34))
    for result in results:
        mark = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "not_run": "SKIP"}[
            result["gate_result"]
        ]
        print(f"  {result['plane']:<{width}}  {mark}   fixtures: {result['fixtures_run']}")
        for failure in result.get("failures", []):
            print(f"      ! {failure['fixture_id']}: {failure['reason']}")
    print("-" * (width + 34))
    print(f"  release decision: {decision.upper()}")
    print(f"  mode            : {'BOUND SUT ' + args.system if args.system else 'CONTRACT MODE'}")
    if blocking:
        print(f"  blocking planes : {', '.join(blocking)}")
    return 1 if args.fail_on_gate and decision == "block" else 0


if __name__ == "__main__":
    sys.exit(main())
