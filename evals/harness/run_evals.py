#!/usr/bin/env python3
"""SWOS eight-plane evaluation harness.

Contract mode checks fixture conformance. `--system autonomous-swos` binds the
same fixtures to production Autonomous SWOS controls and is the release mode used
by CI for the reference runtime.
"""

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

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


class ProductionEvaluationInterface(Protocol):
    """Minimal adapter boundary used by Research Grade fixture evaluation."""

    def evaluate(self, case: dict[str, Any]) -> dict[str, Any]:
        """Evaluate one case without reading fixture expectations."""


def evaluate_research_grade(
    cases: list[dict[str, Any]], *, classifier: ProductionEvaluationInterface
) -> dict[str, Any]:
    """Evaluate cases through an injected production interface.

    This adapter intentionally does not inspect fixture names or expected
    labels.  The supplied interface owns classification/evaluation; the
    harness records its returned evidence for later scoring and gating.
    """

    if classifier is None or not (
        callable(getattr(classifier, "evaluate", None))
        or callable(getattr(classifier, "classify", None))
    ):
        raise ValueError("a production evaluation interface is required")
    if not isinstance(cases, list):
        raise ValueError("evaluation cases must be a list")
    evaluated = []
    for case in cases:
        if not isinstance(case, dict) or not case.get("case_id"):
            raise ValueError("each evaluation case requires case_id")
        if callable(getattr(classifier, "evaluate", None)):
            result = classifier.evaluate(case)
        else:
            result = classifier.classify(case)
        if not isinstance(result, dict):
            raise ValueError("production evaluation interface must return an object")
        evaluated.append(result)
    return {"cases": evaluated, "count": len(evaluated), "interface": type(classifier).__name__}


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


def _bound_plane(plane, fixtures, system_under_test, run_dir):
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
    if not run_dir:
        return {
            "plane": plane,
            "gate_result": "fail",
            "fixtures_run": 0,
            "metrics": [],
            "failures": [{"fixture_id": "-", "reason": "Runtime-bound mode requires --run-dir"}],
            "mode": "bound_sut",
        }
    from swos_runtime.evaluation import EvaluationSubject, evaluate_plane

    return evaluate_plane(EvaluationSubject.load(run_dir), plane, fixtures)


def run_plane(plane, system_under_test=None, run_dir=None):
    fixtures = load_fixtures(plane)
    if system_under_test is None:
        return _contract_plane(plane, fixtures)
    return _bound_plane(plane, fixtures, system_under_test, run_dir)


def _execute(args, selected, run_dir):
    if args.system:
        from swos_runtime.evaluation import (
            EvaluationSubject,
            build_evaluation_result,
            validate_evaluation_result,
        )

        subject = EvaluationSubject.load(run_dir)
        fixtures = {plane: load_fixtures(plane) for plane in selected}
        document = build_evaluation_result(
            subject,
            fixtures,
            selected=selected,
            decided_at=datetime.now(timezone.utc).isoformat(),
        )
        schema_errors = validate_evaluation_result(document)
        if schema_errors:
            raise RuntimeError("evaluation result schema failure: " + "; ".join(schema_errors))
        return document

    results = [run_plane(plane) for plane in selected]
    blocking = [
        result["plane"] for result in results if result["gate_result"] in ("fail", "not_run")
    ]
    return {
        "schema_version": "1.0.0",
        "work_id": "work-00000000-0000-0000-0000-000000000000",
        "run_id": f"evl-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "harness_version": "1.1.0",
        "planes": results,
        "release_decision": {
            "decision": "block" if blocking else "release",
            "blocking_planes": blocking,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--all",
        "--all-planes",
        dest="all_planes",
        action="store_true",
        help="Run every registered evaluation plane",
    )
    parser.add_argument("--planes", default="")
    parser.add_argument("--fail-on-gate", action="store_true")
    parser.add_argument("--system", default=None, help="Bound system under test adapter id")
    parser.add_argument("--run-dir", default=None, help="Finalized runtime subject directory")
    parser.add_argument(
        "--deterministic-subject",
        action="store_true",
        help="Build a credential-free real runtime subject for deterministic CI",
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    selected = (
        PLANES
        if args.all_planes or not args.planes
        else [p.strip() for p in args.planes.split(",") if p.strip()]
    )
    unknown = [plane for plane in selected if plane not in PLANES]
    if unknown:
        print(f"error: unknown plane(s): {', '.join(unknown)}")
        return 2

    if args.system and not args.run_dir and not args.deterministic_subject:
        print("error: runtime-bound mode requires --run-dir")
        return 2
    if args.run_dir and args.deterministic_subject:
        print("error: choose --run-dir or --deterministic-subject, not both")
        return 2

    temporary = None
    run_dir = args.run_dir
    if args.deterministic_subject:
        from evals.harness.deterministic_subject import build_deterministic_subject

        temporary = tempfile.TemporaryDirectory()
        run_dir = temporary.name
        outcome = build_deterministic_subject(run_dir)
        if outcome.status != "APPROVED":
            print("error: deterministic runtime subject did not pass automated assurance")
            temporary.cleanup()
            return 1
    try:
        document = _execute(args, selected, run_dir)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}")
        if temporary:
            temporary.cleanup()
        return 1
    results = document["planes"]
    blocking = [
        result["plane"] for result in results if result["gate_result"] in ("fail", "not_run")
    ]
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
    recommendation = document["release_decision"]["decision"]
    print(f"  release recommendation: {recommendation.upper()}")
    print(f"  mode            : {'BOUND SUT ' + args.system if args.system else 'CONTRACT MODE'}")
    if blocking:
        print(f"  blocking planes : {', '.join(blocking)}")
    if temporary:
        temporary.cleanup()
    return 1 if args.fail_on_gate and blocking else 0


if __name__ == "__main__":
    sys.exit(main())
