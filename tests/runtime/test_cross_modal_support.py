"""Cross-modal observation, evidence, and attribution guardrail tests."""

from __future__ import annotations

import unittest

from swos_runtime.image_analysis import VisualObservation, evaluate_cross_modal_support


class CrossModalSupportTests(unittest.TestCase):
    def test_weakest_leg_blocks_when_textual_support_is_missing(self) -> None:
        observation = VisualObservation(
            observation_id="obs-1",
            object_id="object-1",
            asset_id="asset-1",
            asset_digest="a" * 64,
            description="a visible blue mark",
            origin="machine",
            supports_claim_ids=("claim-1",),
        )
        result = evaluate_cross_modal_support(
            {
                "claim_id": "claim-1",
                "object_id": "object-1",
                "asset_id": "asset-1",
                "claim_type": "observation",
            },
            [observation],
            [],
        )
        self.assertEqual("blocked", result.status)
        self.assertEqual("blocked", result.weakest_leg)

    def test_false_attribution_and_originality_are_never_machine_verified(self) -> None:
        observation = VisualObservation(
            observation_id="obs-1",
            object_id="object-1",
            asset_id="asset-1",
            asset_digest="a" * 64,
            description="visible forms",
            origin="machine",
            supports_claim_ids=("claim-1",),
            review_status="reviewed",
        )
        result = evaluate_cross_modal_support(
            {
                "claim_id": "claim-1",
                "object_id": "object-1",
                "asset_id": "asset-1",
                "claim_type": "attribution",
                "attribution": "Unknown artist",
            },
            [observation],
            [{"claim_id": "claim-1", "support_level": "directly_supports"}],
        )
        self.assertNotEqual("verified", result.status)
        self.assertTrue(result.limitations)


if __name__ == "__main__":
    unittest.main()
