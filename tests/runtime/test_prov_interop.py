"""PROV-JSON, PROV-N, and PROV-O/TriG losslessness tests."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from swos_runtime.prov_interop import parse_prov, serialize_prov
from swos_runtime.prov_model import ResourceLimits
from swos_runtime.prov_validation import canonical_fingerprint
from tests.runtime.test_epg_v2 import sample_epg


class ProvInteropTests(unittest.TestCase):
    def test_all_advertised_formats_roundtrip_without_dropping_bundles_or_extensions(self) -> None:
        from swos_runtime.prov_interop import epg_to_prov

        document = epg_to_prov(sample_epg(), base_iri="https://example.org/prov/")
        for format_name in ("prov-json", "prov-n", "prov-o-trig"):
            with self.subTest(format=format_name):
                encoded = serialize_prov(document, format_name)
                decoded = parse_prov(encoded, format_name, ResourceLimits())
                self.assertEqual(document.semantic_normal_form(), decoded.semantic_normal_form())
                self.assertEqual(document.fingerprint().semantic_digest, decoded.fingerprint().semantic_digest)

    def test_cross_format_matrix_is_stable(self) -> None:
        from swos_runtime.prov_interop import epg_to_prov

        document = epg_to_prov(sample_epg(), base_iri="https://example.org/prov/")
        current = document
        for format_name in ("prov-json", "prov-n", "prov-o-trig", "prov-json"):
            current = parse_prov(serialize_prov(current, format_name), format_name, ResourceLimits())
        self.assertEqual(document.fingerprint().semantic_digest, current.fingerprint().semantic_digest)

    def test_resource_limits_fail_closed(self) -> None:
        from swos_runtime.prov_interop import epg_to_prov

        document = epg_to_prov(sample_epg(), base_iri="https://example.org/prov/")
        with self.assertRaises(ValueError):
            parse_prov(serialize_prov(document, "prov-json"), "prov-json", ResourceLimits(max_bytes=10))

    def test_rpm_export_requires_matching_certified_epg(self) -> None:
        from swos_runtime.prov_interop import epg_to_prov
        from swos_runtime.rpm_exchange import ExchangeError, RPMExchange

        document = epg_to_prov(sample_epg(), base_iri="https://example.org/prov/")
        exchange = RPMExchange.__new__(RPMExchange)
        with TemporaryDirectory() as directory:
            with self.assertRaises(ExchangeError):
                exchange.export_certified_epg(document, {"status": "not_run"}, Path(directory) / "blocked")
            output = Path(directory) / "certified"
            exchange.export_certified_epg(
                document,
                {"status": "certified", "input_digest": canonical_fingerprint(document).semantic_digest},
                output,
            )
            self.assertTrue((output / "epg-v2.json").is_file())


if __name__ == "__main__":
    unittest.main()
