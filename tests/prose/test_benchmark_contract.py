from __future__ import annotations

import unittest

from benchmark.runner import load_corpus, validate_corpus


class ProseBenchmarkContractTests(unittest.TestCase):
    def test_governed_corpus_has_exactly_fifty_unique_fixtures(self):
        fixtures = load_corpus()
        self.assertEqual(len(fixtures), 50)
        self.assertEqual(len({item["fixture_id"] for item in fixtures}), 50)

    def test_diagnostics_contract_has_no_unsafe_abstentions(self):
        validation = validate_corpus(load_corpus(), expect_count=50)
        self.assertEqual(validation["shape_errors"], [])
        self.assertEqual(validation["duplicate_fixture_ids"], [])
        self.assertEqual(validation["json_schema_errors"], [])
        self.assertEqual(validation["unsafe_abstentions"], [])
        self.assertEqual(validation["diagnostics_expectation_mismatches"], [])
        self.assertEqual(validation["missing_expected_signals"], [])
        self.assertTrue(validation["valid"])

    def test_stability_subset_is_the_inherited_eleven_case_suite(self):
        fixtures = load_corpus()
        self.assertEqual(sum(1 for item in fixtures if item["stability_probe"]), 11)


if __name__ == "__main__":
    unittest.main()
