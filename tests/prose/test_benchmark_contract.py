from __future__ import annotations

import unittest

from benchmark.runner import load_corpus, validate_corpus


class ProseBenchmarkContractTests(unittest.TestCase):
    def test_governed_corpus_has_exactly_fifty_six_unique_fixtures(self):
        fixtures = load_corpus()
        self.assertEqual(len(fixtures), 56)
        self.assertEqual(len({item["fixture_id"] for item in fixtures}), 56)

    def test_m1_repair_slice_contains_exactly_six_governed_cases(self):
        fixtures = load_corpus()
        repairs = [item for item in fixtures if item["benchmark_group"] == "repair"]
        self.assertEqual(len(repairs), 6)
        self.assertEqual({item["fixture_id"] for item in repairs}, {f"repair-{index:03d}" for index in range(1, 7)})
        self.assertTrue(all(item["semantic_relation"] == "material_change" for item in repairs))

    def test_diagnostics_contract_has_no_unsafe_abstentions(self):
        validation = validate_corpus(load_corpus(), expect_count=56)
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


if __name__ == "__main__":
    unittest.main()
