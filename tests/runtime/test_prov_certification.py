"""PROV certification matrix and certificate tests."""

from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch

from swos_runtime.prov_interop import epg_to_prov
from swos_runtime.prov_model import ProvDocument, ResourceLimits
from swos_runtime.prov_validation import canonical_fingerprint, certify_round_trip
from tests.runtime.test_epg_v2 import sample_epg


class ProvCertificationTests(unittest.TestCase):
    def test_required_conversion_matrix_and_second_round_stability(self) -> None:
        certificate = certify_round_trip(
            sample_epg(),
            ("prov-json", "prov-n", "prov-o-trig"),
            oracle={"status": "not_run", "reason": "independent oracle is not installed"},
            limits=ResourceLimits(),
        )
        self.assertEqual("not_run", certificate.status)
        self.assertTrue(certificate.legs)
        self.assertIn("EPG -> PROV-JSON -> EPG", certificate.paths)
        self.assertTrue(all(item["semantic_equivalent"] for item in certificate.legs))

    def test_round_trip_semantic_comparisons_receive_resource_deadlines(self) -> None:
        observed_deadlines = []
        original = ProvDocument.semantic_normal_form

        def observe(document: ProvDocument, **kwargs):
            observed_deadlines.append(kwargs.get("deadline"))
            return original(document, **kwargs)

        with patch.object(ProvDocument, "semantic_normal_form", observe):
            certify_round_trip(
                sample_epg(),
                ("prov-json",),
                oracle={"status": "not_run"},
                limits=ResourceLimits(),
            )

        self.assertTrue(observed_deadlines)
        self.assertTrue(all(deadline is not None for deadline in observed_deadlines))

    def test_accepted_oracle_requires_a_pinned_licence(self) -> None:
        epg = sample_epg()
        fingerprint = canonical_fingerprint(
            epg_to_prov(epg, base_iri=epg["base_iri"]), ResourceLimits()
        )
        oracle = {
            "status": "accepted",
            "implementation": "ProvToolbox",
            "version": "3.0.0",
            "artifact_sha256": "a" * 64,
            "profile": epg["profile"],
            "formats": ["prov-json"],
            "input_digest": fingerprint.semantic_digest,
        }

        certificate = certify_round_trip(
            epg, ("prov-json",), oracle=oracle, limits=ResourceLimits()
        )

        self.assertNotEqual("certified", certificate.status)

    def test_invalid_oracle_cannot_be_certified(self) -> None:
        certificate = certify_round_trip(
            sample_epg(),
            ("prov-json",),
            oracle={"status": "failed"},
            limits=ResourceLimits(),
        )
        self.assertEqual("failed", certificate.status)

    def test_oracle_acceptance_must_bind_input_profile_formats_and_processor(self) -> None:
        epg = sample_epg()
        fingerprint = canonical_fingerprint(
            epg_to_prov(epg, base_iri=epg["base_iri"]), ResourceLimits()
        )
        oracle = {
            "status": "accepted",
            "implementation": "ProvToolbox",
            "version": "3.0.0",
            "licence": "Apache-2.0",
            "artifact_sha256": "a" * 64,
            "profile": epg["profile"],
            "formats": ["prov-json"],
            "input_digest": "0" * 64,
        }
        certificate = certify_round_trip(
            epg, ("prov-json",), oracle=oracle, limits=ResourceLimits()
        )
        self.assertNotEqual("certified", certificate.status)

        oracle["input_digest"] = fingerprint.semantic_digest
        certificate = certify_round_trip(
            epg, ("prov-json",), oracle=oracle, limits=ResourceLimits()
        )
        self.assertNotEqual("certified", certificate.status)

        oracle["artifact_verified"] = True
        oracle["verification"] = {
            "status": "verified",
            "artifact_sha256": oracle["artifact_sha256"],
            "execution_status": "passed",
        }
        certificate = certify_round_trip(
            epg, ("prov-json",), oracle=oracle, limits=ResourceLimits()
        )
        self.assertEqual("certified", certificate.status)

    def test_second_cross_format_route_is_executed_not_hard_coded(self) -> None:
        epg = sample_epg()
        fingerprint = canonical_fingerprint(
            epg_to_prov(epg, base_iri=epg["base_iri"]), ResourceLimits()
        )
        oracle = {
            "status": "accepted",
            "implementation": "ProvToolbox",
            "version": "3.0.0",
            "licence": "Apache-2.0",
            "artifact_sha256": "a" * 64,
            "profile": epg["profile"],
            "formats": ["prov-json", "prov-n", "prov-o-trig"],
            "input_digest": fingerprint.semantic_digest,
        }
        from swos_runtime import prov_interop

        original_parse = prov_interop.parse_prov
        calls = {"count": 0}

        def lossy_parse(data, format_name, limits=None):
            calls["count"] += 1
            document = original_parse(data, format_name, limits)
            if calls["count"] == 11:
                return replace(document, extensions=())
            return document

        with patch.object(prov_interop, "parse_prov", side_effect=lossy_parse):
            certificate = certify_round_trip(
                epg,
                ("prov-json", "prov-n", "prov-o-trig"),
                oracle=oracle,
                limits=ResourceLimits(),
            )
        self.assertNotEqual("certified", certificate.status)
        self.assertEqual(11, calls["count"])

    def test_full_matrix_requires_rdf_shacl_validation(self) -> None:
        epg = sample_epg()
        fingerprint = canonical_fingerprint(
            epg_to_prov(epg, base_iri=epg["base_iri"]), ResourceLimits()
        )
        oracle = {
            "status": "accepted",
            "implementation": "ProvToolbox",
            "version": "3.0.0",
            "licence": "Apache-2.0",
            "artifact_sha256": "a" * 64,
            "artifact_verified": True,
            "verification": {
                "status": "verified",
                "artifact_sha256": "a" * 64,
                "execution_status": "passed",
            },
            "profile": epg["profile"],
            "formats": ["prov-json", "prov-n", "prov-o-trig"],
            "input_digest": fingerprint.semantic_digest,
        }
        certificate = certify_round_trip(
            epg,
            ("prov-json", "prov-n", "prov-o-trig"),
            oracle=oracle,
            limits=ResourceLimits(),
        )
        self.assertNotEqual("certified", certificate.status)
        trig_legs = [
            leg
            for leg in certificate.legs
            if isinstance(leg.get("validation"), dict)
            and leg["validation"].get("format") == "prov-o-trig"
        ]
        self.assertTrue(trig_legs)
        self.assertFalse(trig_legs[0]["validation"]["report"]["shacl"]["passed"])


if __name__ == "__main__":
    unittest.main()
