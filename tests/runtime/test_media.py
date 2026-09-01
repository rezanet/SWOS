"""Object/media/rights/accessibility separation tests."""

from __future__ import annotations

import unittest

from swos_runtime.media import (
    AccessibilityRecord,
    MediaAssetRecord,
    ObjectInspectionActivity,
    ObjectRecord,
    derive_asset,
    redact_asset_for_export,
    validate_media_asset,
)


class MediaTests(unittest.TestCase):
    def _asset(self, **changes):
        values = {
            "asset_id": "asset-1",
            "object_id": "object-1",
            "role": "surrogate",
            "mime_type": "image/jpeg",
            "byte_size": 4,
            "width": 100,
            "height": 50,
            "byte_digest": "a" * 64,
            "acquisition_uri": "https://example.org/a.jpg",
            "rights": {"view": {"status": "allowed"}, "analyse": {"status": "allowed"}, "transform": {"status": "denied"}, "create_derivative": {"status": "unknown"}, "quote": {"status": "allowed"}, "cache": {"status": "allowed"}, "export": {"status": "denied"}, "redistribute": {"status": "denied"}},
        }
        values.update(changes)
        return MediaAssetRecord(**values)

    def test_object_media_and_inspection_are_distinct_and_rights_are_purpose_specific(self) -> None:
        obj = ObjectRecord(object_id="object-1", object_type="painting", label="Work")
        inspection = ObjectInspectionActivity(inspection_id="inspection-1", object_id=obj.object_id, actor_id="person-1", observed_scope="surface")
        asset = self._asset(inspection_activity_ids=(inspection.inspection_id,))
        self.assertNotEqual(obj.object_id, asset.asset_id)
        result = validate_media_asset(asset)
        self.assertTrue(result.valid)
        self.assertFalse(result.allowed("transform"))
        self.assertTrue(result.allowed("analyse"))

    def test_derivative_inherits_restrictive_rights_and_accessibility_is_invalidated(self) -> None:
        parent = self._asset(
            rights={
                **self._asset().rights,
                "create_derivative": {"status": "allowed", "grant_id": "grant-1", "evidence": "rights-record-1"},
            },
            content_credentials={"status": "valid", "credential_digest": "c" * 64},
            accessibility=AccessibilityRecord(asset_digest="a" * 64, purpose="evidentiary", short_alternative="A work", origin="human", review_status="reviewed", language="en"),
        )
        child = derive_asset(parent, asset_id="asset-2", byte_digest="b" * 64, transform="crop")
        self.assertFalse(child.action_allowed("transform"))
        self.assertEqual("invalidated_derivative", child.accessibility.invalidation_reason)
        self.assertEqual("valid", child.content_credentials["parent_status"])
        self.assertEqual("invalidated_derivative", child.content_credentials["status"])

    def test_derivative_creation_requires_analysis_and_a_derivative_right(self) -> None:
        with self.assertRaises(PermissionError):
            derive_asset(self._asset(), asset_id="asset-2", byte_digest="b" * 64, transform="crop")

    def test_export_redacts_barred_bytes_but_keeps_limitation(self) -> None:
        exported = redact_asset_for_export(self._asset())
        self.assertTrue(exported["redacted"])
        self.assertNotIn("bytes", exported)
        self.assertTrue(exported["limitations"])


if __name__ == "__main__":
    unittest.main()
