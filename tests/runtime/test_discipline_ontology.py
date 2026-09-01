"""US2 structural and compatibility contracts for formal discipline packs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.discipline_ontology import (
    DISCIPLINE_IRI_BASE,
    SUPPORTED_DISCIPLINES,
    DisciplineOntologyRegistry,
    PackValidationError,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "discipline-packs" / "manifest-v2.json"


class DisciplineOntologyTests(unittest.TestCase):
    def test_all_nine_packs_have_stable_iris_and_bidirectional_mapping(self) -> None:
        registry = DisciplineOntologyRegistry().load(MANIFEST)
        self.assertEqual(9, len(SUPPORTED_DISCIPLINES))
        self.assertEqual(set(SUPPORTED_DISCIPLINES), set(registry.disciplines()))
        for discipline in SUPPORTED_DISCIPLINES:
            profile = registry.profile(discipline)
            self.assertEqual(f"{DISCIPLINE_IRI_BASE}{discipline}", profile.discipline_iri)
            self.assertEqual(discipline, profile.discipline)
            self.assertTrue(profile.required_criteria)
            self.assertTrue(profile.ontology_digest)
            report = registry.validate_pack(ROOT / profile.ontology_path)
            self.assertTrue(report.valid, report.errors)

    def test_v2_rejects_frozen_v1_enterprise_reporting_without_fallback(self) -> None:
        registry = DisciplineOntologyRegistry().load(MANIFEST)
        with self.assertRaises(PackValidationError) as raised:
            registry.profile("enterprise_reporting")
        self.assertIn("enterprise_reporting", str(raised.exception))
        self.assertNotIn("interdisciplinary", str(raised.exception))

    def test_validation_rejects_duplicate_dangling_cycle_and_bad_weight(self) -> None:
        bad = {
            "discipline": "engineering",
            "discipline_iri": f"{DISCIPLINE_IRI_BASE}engineering",
            "concepts": [
                {"iri": "urn:a", "notation": "dup"},
                {"iri": "urn:b", "notation": "dup"},
                {"iri": "urn:a", "notation": "cycle-a", "broader": ["urn:b"]},
                {"iri": "urn:b", "notation": "cycle-b", "broader": ["urn:a"]},
            ],
            "criteria": [{"iri": "urn:criterion", "weight": 2.0}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(PackValidationError) as raised:
                DisciplineOntologyRegistry().validate_pack(path)
        message = str(raised.exception)
        self.assertIn("duplicate", message)
        self.assertIn("cycle", message)
        self.assertIn("weight", message)

    def test_v1_warning_window_is_explicit_and_migration_is_reversible(self) -> None:
        registry = DisciplineOntologyRegistry().load(MANIFEST)
        self.assertTrue(registry.compatibility["v1_warning_window"])
        self.assertEqual("enterprise_reporting", registry.migrate_v1_discipline("enterprise_reporting"))
        self.assertEqual("engineering", registry.migrate_v1_discipline("engineering"))


if __name__ == "__main__":
    unittest.main()
