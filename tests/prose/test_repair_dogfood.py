from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_prose.dogfood import collect_dogfood
from swos_prose.providers.rewrite_base import RewriteCandidate


class RepairingRewriteProvider:
    def __init__(self, defective: str, repaired: str):
        self.defective = defective
        self.repaired = repaired
        self.rewrite_calls = 0
        self.repair_calls = 0

    def rewrite(self, **kwargs) -> RewriteCandidate:
        self.rewrite_calls += 1
        return RewriteCandidate(candidate_text=self.defective)

    def repair(self, **kwargs) -> RewriteCandidate:
        self.repair_calls += 1
        return RewriteCandidate(
            candidate_text=self.repaired,
            notes=[
                "provider=dogfood-repair",
                "model=test-model",
                "prompt_version=test-v1",
                "input_sha256=test-input",
                "response_id=test-response",
            ],
            token_usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        )


class RepairDogfoodTests(unittest.TestCase):
    def test_record_and_summary_capture_repair_provenance(self):
        source = "The findings may indicate a relationship."
        defective = "The findings indicate a relationship."
        provider = RepairingRewriteProvider(defective, source)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus"
            results = root / "results"
            corpus.mkdir()
            (corpus / "repair.txt").write_text(source, encoding="utf-8")
            records = collect_dogfood(
                input_dir=corpus,
                output_dir=results,
                rewrite_provider=provider,
                verifier_provider=None,
                assurance="strict",
                run_diagnostics=False,
            )
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["status"], "PASS")
            self.assertTrue(record["repair_success"])
            self.assertIsNone(record["repair_failure_reason"])
            self.assertEqual(len(record["repair_attempts"]), 1)
            self.assertTrue(record["repair_attempts"][0]["success"])
            self.assertEqual(
                record["repair_attempts"][0]["provider_notes"],
                [
                    "provider=dogfood-repair",
                    "model=test-model",
                    "prompt_version=test-v1",
                    "input_sha256=test-input",
                    "response_id=test-response",
                ],
            )
            self.assertIn("response_id=test-response", record["notes"])
            self.assertEqual(provider.repair_calls, 1)

            summary = json.loads((results / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["repair"]["cases_attempted"], 1)
            self.assertEqual(summary["repair"]["total_attempts"], 1)
            self.assertEqual(summary["repair"]["successes"], 1)
            self.assertEqual(summary["repair"]["success_rate"], 1.0)
            self.assertEqual(summary["repair"]["average_attempts_per_repair"], 1.0)


if __name__ == "__main__":
    unittest.main()
