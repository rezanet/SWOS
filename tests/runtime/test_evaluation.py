from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evals.harness.deterministic_subject import build_deterministic_subject
from evals.harness.run_evals import PLANES, load_fixtures
from swos_runtime.evaluation import (
    EvaluationError,
    EvaluationSubject,
    build_evaluation_result,
    validate_evaluation_result,
)

TIME = "2026-08-30T00:00:00+00:00"


class RuntimeEvaluationTests(unittest.TestCase):
    def _subject(self, root: Path) -> EvaluationSubject:
        outcome = build_deterministic_subject(root)
        self.assertEqual(outcome.status, "APPROVED", outcome.blocking_reasons)
        return EvaluationSubject.load(root)

    def _result(self, subject: EvaluationSubject):
        return build_evaluation_result(
            subject,
            {plane: load_fixtures(plane) for plane in PLANES},
            selected=PLANES,
            decided_at=TIME,
        )

    def test_all_eight_planes_bind_one_finalized_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = self._subject(Path(tmp))
            result = self._result(subject)

            self.assertEqual(validate_evaluation_result(result), [])
            self.assertEqual([item["plane"] for item in result["planes"]], PLANES)
            self.assertTrue(all(item["gate_result"] == "pass" for item in result["planes"]))
            self.assertEqual(result["release_decision"]["decision"], "release")
            self.assertEqual(result["subject_versions"]["subject_run_id"], subject.run_id)
            self.assertEqual(result["subject_versions"]["manifest_sha256"], subject.manifest_sha256)
            for plane in result["planes"]:
                metric_names = {metric["metric"] for metric in plane["metrics"]}
                self.assertIn("exact_subject_binding", metric_names)
                self.assertIn("production_control_provenance", metric_names)
                self.assertTrue(any(name.startswith("artifact_evidence:") for name in metric_names))

    def test_missing_or_mutated_subject_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(EvaluationError):
                EvaluationSubject.load(root)

            self._subject(root)
            matrix = json.loads((root / "evidence-matrix.json").read_text(encoding="utf-8"))
            matrix["rows"][0]["claim_text"] = "tampered"
            (root / "evidence-matrix.json").write_text(json.dumps(matrix), encoding="utf-8")
            with self.assertRaises(EvaluationError):
                EvaluationSubject.load(root)

    def test_duplicate_or_partial_plane_selection_cannot_recommend_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = self._subject(Path(tmp))
            fixtures = {plane: load_fixtures(plane) for plane in PLANES}
            with self.assertRaises(EvaluationError):
                build_evaluation_result(
                    subject,
                    fixtures,
                    selected=["citation", "citation"],
                    decided_at=TIME,
                )
            partial = build_evaluation_result(
                subject, fixtures, selected=["citation"], decided_at=TIME
            )
            self.assertEqual(partial["planes"][0]["gate_result"], "pass")
            self.assertEqual(partial["release_decision"]["decision"], "block")

    def test_unknown_reviewer_independence_blocks_governance_plane(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = self._subject(Path(tmp))
            subject.review_assurance["hostile_review"]["independence"] = "unknown"
            result = self._result(subject)
            governance = next(item for item in result["planes"] if item["plane"] == "governance")
            self.assertEqual(governance["gate_result"], "fail")


if __name__ == "__main__":
    unittest.main()
