"""Digest-bound IIIF and bounded SVG selector tests."""

from __future__ import annotations

import unittest

from swos_runtime.media import MediaAssetRecord, RegionSelector, normalize_selector


class RegionSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.asset = MediaAssetRecord(
            asset_id="a",
            object_id="o",
            role="detail",
            mime_type="image/jpeg",
            byte_size=10,
            width=1000,
            height=500,
            byte_digest="a" * 64,
            acquisition_uri="https://example.org/a",
        )

    def test_pixel_and_percent_selectors_normalize_deterministically(self) -> None:
        pixel = normalize_selector(
            RegionSelector("iiif_pixel", "10,20,300,100", "a" * 64), self.asset
        )
        percent = normalize_selector(
            RegionSelector("iiif_percent", "pct:10,20,30,40", "a" * 64), self.asset
        )
        self.assertEqual((10, 20, 300, 100), pixel.normalized)
        self.assertEqual((100, 100, 300, 200), percent.normalized)
        self.assertEqual(
            pixel.to_dict(),
            normalize_selector(
                RegionSelector("iiif_pixel", "10,20,300,100", "a" * 64), self.asset
            ).to_dict(),
        )

    def test_digest_out_of_bounds_and_ambiguous_svg_fail(self) -> None:
        with self.assertRaises(ValueError):
            normalize_selector(RegionSelector("iiif_pixel", "10,20,300,100", "b" * 64), self.asset)
        with self.assertRaises(ValueError):
            normalize_selector(RegionSelector("iiif_pixel", "900,20,300,100", "a" * 64), self.asset)
        svg = '<svg><rect x="1" y="2" width="3" height="4"/><rect x="5" y="6" width="7" height="8"/></svg>'
        with self.assertRaises(ValueError):
            normalize_selector(RegionSelector("svg", svg, "a" * 64), self.asset)


if __name__ == "__main__":
    unittest.main()
