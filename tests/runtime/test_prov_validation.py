"""PROV profile, canonicalization, and validation tests."""

from __future__ import annotations

import unittest
from dataclasses import replace

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

    def test_invalid_relation_and_unknown_extension_are_not_silently_accepted(self) -> None:
        epg = sample_epg()
        epg["relations"].append({"type": "unknownRelation", "subject": "https://example.org/e1"})
        document = epg_to_prov(epg, base_iri="https://example.org/prov/")
        report = validate_prov(document, profile="swos.prov-dm-round-trip.v2")
        self.assertIn(report.status, {"invalid", "unsupported"})
        self.assertTrue(report.violations)

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
