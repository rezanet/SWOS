from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from benchmark.runner import (
    ACTIVE_CORPUS_COUNT,
    BENCHMARK_VERSION,
    _base_report,
    _combined_result_usage,
    load_corpus,
    validate_corpus,
)

ROOT = Path(__file__).resolve().parents[2]


class ProseBenchmarkContractTests(unittest.TestCase):
    def test_governed_corpus_has_exactly_fifty_six_unique_fixtures(self):
        fixtures = load_corpus()
        self.assertEqual(len(fixtures), ACTIVE_CORPUS_COUNT)
        self.assertEqual(len({item["fixture_id"] for item in fixtures}), ACTIVE_CORPUS_COUNT)

    def test_m1_repair_slice_contains_exactly_six_governed_cases(self):
        fixtures = load_corpus()
        repairs = [item for item in fixtures if item["benchmark_group"] == "repair"]
        self.assertEqual(len(repairs), 6)
        self.assertEqual(
            {item["fixture_id"] for item in repairs},
            {f"repair-{index:03d}" for index in range(1, 7)},
        )
        self.assertTrue(all(item["semantic_relation"] == "material_change" for item in repairs))

    def test_diagnostics_contract_has_no_unsafe_abstentions(self):
        validation = validate_corpus(load_corpus(), expect_count=ACTIVE_CORPUS_COUNT)
        self.assertEqual(validation["shape_errors"], [])
        self.assertEqual(validation["duplicate_fixture_ids"], [])
        self.assertEqual(validation["json_schema_errors"], [])
        self.assertEqual(validation["unsafe_abstentions"], [])
        self.assertEqual(validation["diagnostics_expectation_mismatches"], [])
        self.assertEqual(validation["missing_expected_signals"], [])
        self.assertTrue(validation["valid"])

    def test_stability_subset_remains_the_inherited_eleven_case_suite(self):
        fixtures = load_corpus()
        self.assertEqual(sum(1 for item in fixtures if item["stability_probe"]), 11)

    def test_active_report_has_m1_identity_and_frozen_evidence_stays_v02(self):
        report = _base_report(load_corpus(), "validate")
        self.assertEqual(report["benchmark_version"], "0.3.0-m1")
        self.assertEqual(report["benchmark_version"], BENCHMARK_VERSION)
        self.assertEqual(report["corpus"]["fixture_count"], ACTIVE_CORPUS_COUNT)

        frozen = json.loads((ROOT / "benchmark" / "baseline.json").read_text(encoding="utf-8"))
        self.assertEqual(frozen["benchmark_version"], "0.2.0-rc1")
        self.assertEqual(frozen["corpus"]["fixture_count"], 50)
        frozen_at = (ROOT / "benchmark" / "FROZEN_AT").read_text(encoding="utf-8")
        self.assertIn("benchmark_version: 0.2.0-rc1", frozen_at)

    def test_combined_usage_includes_repair_attempt_tokens(self):
        result = SimpleNamespace(
            rewrite_token_usage={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
            repair_attempts=[
                SimpleNamespace(
                    token_usage={"input_tokens": 30, "output_tokens": 5, "total_tokens": 35}
                ),
                SimpleNamespace(token_usage=None),
            ],
            verification=SimpleNamespace(
                token_usage={"input_tokens": 40, "output_tokens": 10, "total_tokens": 50},
            ),
        )

        self.assertEqual(
            _combined_result_usage(result),
            {"input_tokens": 170, "output_tokens": 35, "total_tokens": 205},
        )


if __name__ == "__main__":
    unittest.main()
