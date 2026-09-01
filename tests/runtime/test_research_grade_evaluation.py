"""Test-first production-interface boundary for Research Grade fixtures."""

from __future__ import annotations

import unittest
from pathlib import Path

from evals.harness.run_evals import evaluate_research_grade
from swos_runtime.evaluation import EvaluationSubject


class _InjectedInterface:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def evaluate(self, case: dict[str, object]) -> dict[str, object]:
        self.calls.append(case)
        return {"case_id": case["case_id"], "status": "evaluated", "label": "directly_supports"}


class ResearchGradeEvaluationTests(unittest.TestCase):
    def test_subject_carries_exact_artifact_identities(self) -> None:
        subject = EvaluationSubject(
            root=Path("."),
            manifest={"run_id": "run-1", "work_id": "work-1"},
            control={},
            evidence={},
            sources=[],
            argument={},
            reviews=[],
            review_assurance={},
            provenance={},
            manifest_sha256="m" * 64,
            integrity_chain_head="h" * 64,
            artifact_identities={"run-manifest.json": "m" * 64},
        )
        self.assertEqual("m" * 64, subject.artifact_identities["run-manifest.json"])
        self.assertEqual("m" * 64, subject.subject_versions()["artifact_identities"]["run-manifest.json"])

    def test_fixture_evaluation_invokes_the_injected_production_interface(self) -> None:
        interface = _InjectedInterface()
        result = evaluate_research_grade(
            [{"case_id": "case-1", "claim": "claim", "span": "span"}],
            classifier=interface,
        )
        self.assertEqual(1, len(interface.calls))
        self.assertEqual("case-1", interface.calls[0]["case_id"])
        self.assertEqual("evaluated", result["cases"][0]["status"])

    def test_missing_production_interface_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_research_grade([{"case_id": "case-1"}], classifier=None)


if __name__ == "__main__":
    unittest.main()
