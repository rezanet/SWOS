"""Production-path multimodal evaluator contract tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.image_analysis import DeterministicFakeImageProvider
from tools.run_multimodal_evals import evaluate_multimodal_cases, run_evals

ROOT = Path(__file__).resolve().parents[2]


class MultimodalEvaluationTests(unittest.TestCase):
    def test_missing_locked_corpus_is_not_run_and_has_no_fabricated_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_evals(ROOT / "evals" / "fixtures" / "multimodal" / "manifest.json", Path(tmp))
        self.assertEqual("NOT_RUN", report["status"])
        self.assertEqual("NOT_RUN", report["gate_result"])
        self.assertEqual(0, report["metrics"]["stability"]["denominator"])

    def test_cases_use_provider_interface_and_report_raw_numerators(self) -> None:
        case = {
            "case_id": "case-1",
            "object": {"object_id": "object-1"},
            "assets": [{"asset_id": "asset-1", "object_id": "object-1", "role": "surrogate", "mime_type": "image/jpeg", "byte_size": 1, "width": 10, "height": 10, "byte_digest": "a" * 64, "acquisition_uri": "https://example.org/a", "rights": {action: {"status": "allowed"} for action in ("view", "analyse", "transform", "create_derivative", "quote", "cache", "export", "redistribute")}}],
            "request": {"work_id": "work-1", "run_id": "run-1", "object_id": "object-1", "target_questions": ["What is visible?"]},
            "expected": {"status": "complete", "observation_count": 1, "accessibility_required": False},
        }
        report = evaluate_multimodal_cases([case], provider=DeterministicFakeImageProvider(), repetitions=3)
        self.assertEqual("evaluated", report["status"])
        self.assertEqual(1, report["metrics"]["agreement"]["numerator"])
        self.assertEqual(1, report["metrics"]["agreement"]["denominator"])
        self.assertEqual(1, report["metrics"]["stability"]["numerator"])
        self.assertIn("raw_case_results", report)
        json.dumps(report)


if __name__ == "__main__":
    unittest.main()
