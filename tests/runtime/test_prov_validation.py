"""PROV profile, canonicalization, and validation tests."""

from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch

from swos_runtime.prov_interop import epg_to_prov
from swos_runtime.prov_validation import canonical_fingerprint, validate_prov
from tests.runtime.test_epg_v2 import sample_epg


class ProvValidationTests(unittest.TestCase):
    def test_valid_profile_has_semantic_jcs_and_rdf_fingerprints(self) -> None:
        document = epg_to_prov(sample_epg(), base_iri="https://example.org/prov/")
        report = validate_prov(document, profile="swos.prov-dm-round-trip.v2")
        self.assertEqual("valid", report.status)
        fingerprint = canonical_fingerprint(document)
        self.assertEqual(report.semantic_digest, fingerprint.semantic_digest)
        self.assertTrue(fingerprint.jcs_digest)
        self.assertTrue(fingerprint.rdfc10_digest)
        self.assertIn(report.shacl["status"], {"valid", "not_applicable_without_rdflib_pyshacl"})

    def test_missing_shacl_dependencies_fail_closed(self) -> None:
        document = epg_to_prov(sample_epg(), base_iri="https://example.org/prov/")
        with patch.dict("sys.modules", {"pyshacl": None, "rdflib": None}):
            report = validate_prov(document, profile="swos.prov-dm-round-trip.v2")
        self.assertFalse(report.shacl["passed"])
        self.assertIn("not_applicable", report.shacl["status"])

    def test_invalid_relation_and_unknown_extension_are_not_silently_accepted(self) -> None:
        epg = sample_epg()
        epg["relations"].append({"type": "unknownRelation", "subject": "https://example.org/e1"})
        document = epg_to_prov(epg, base_iri="https://example.org/prov/")
        report = validate_prov(document, profile="swos.prov-dm-round-trip.v2")
        self.assertIn(report.status, {"invalid", "unsupported"})
        self.assertTrue(report.violations)

    def test_prov_constraints_require_relation_participants(self) -> None:
        epg = sample_epg()
        epg["relations"].append({"type": "wasGeneratedBy"})
        document = epg_to_prov(epg, base_iri="https://example.org/prov/")

        report = validate_prov(document, profile="swos.prov-dm-round-trip.v2")

        self.assertEqual("invalid", report.status)
        self.assertFalse(report.prov_constraints["passed"])
        self.assertEqual("w3c-prov-constraints/2013", report.prov_constraints["ruleset"])
        self.assertTrue(
            any(
                "wasGeneratedBy" in violation and "entity" in violation
                for violation in report.violations
            )
        )

    def test_validation_rejects_wrong_document_profile_or_schema(self) -> None:
        document = epg_to_prov(sample_epg(), base_iri="https://example.org/prov/")
        for field, value in (
            ("schema_version", "1.0.0"),
            ("profile", "unapproved-profile"),
        ):
            with self.subTest(field=field):
                report = validate_prov(replace(document, **{field: value}))
                self.assertEqual("invalid", report.status)
                self.assertTrue(report.violations)


if __name__ == "__main__":
    unittest.main()
