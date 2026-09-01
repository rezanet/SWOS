"""PROV certification matrix and certificate tests."""

from __future__ import annotations

import unittest

from swos_runtime.prov_model import ResourceLimits
from swos_runtime.prov_validation import certify_round_trip
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

    def test_invalid_oracle_cannot_be_certified(self) -> None:
        certificate = certify_round_trip(
            sample_epg(),
            ("prov-json",),
            oracle={"status": "failed"},
            limits=ResourceLimits(),
        )
        self.assertEqual("failed", certificate.status)


if __name__ == "__main__":
    unittest.main()
