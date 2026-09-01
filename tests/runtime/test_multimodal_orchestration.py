"""Pack-only staged multimodal critique and specialist route tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from swos_runtime.discipline_critique import DisciplineCritic
from swos_runtime.discipline_ontology import DisciplineOntologyRegistry
from swos_runtime.image_analysis import VisualObservation
from swos_runtime.orchestrator import specialist_route

ROOT = Path(__file__).resolve().parents[2]


class MultimodalOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = DisciplineOntologyRegistry().load(ROOT / "discipline-packs" / "manifest-v2.json")
        self.observation = VisualObservation(
            observation_id="observation-1",
            object_id="object-1",
            asset_id="asset-1",
            asset_digest="a" * 64,
            description="A bounded visible blue mark.",
            origin="machine",
            selector={"selector_type": "iiif_pixel", "normalized": [1, 2, 3, 4]},
        )

    def test_stages_art_history_before_art_criticism_and_preserves_limits(self) -> None:
        result = DisciplineCritic(self.registry).staged_multimodal_critique(
            research_plan={"methods": ["close observation"], "criteria": {}},
            evidence_matrix={"rows": []},
            draft={"claims": [{"claim_id": "claim-1", "text": "A visible mark is present."}]},
            observations=[self.observation],
            interpretations=[],
        )
        self.assertEqual(("art_history", "art_criticism"), result.stage_order)
        self.assertEqual(2, len(result.sections))
        self.assertEqual("swos-discipline-art-history", result.art_history.pack_id)
        self.assertEqual("swos-discipline-art-criticism", result.art_criticism.pack_id)
        self.assertEqual("machine_proposed", result.review_state)
        self.assertIn("observation-1", result.observation_ids)
        self.assertTrue(result.to_dict()["pack_only_fallback"])

    def test_invalid_visual_anchor_cannot_be_laundered_into_critique_support(self) -> None:
        invalid = VisualObservation(
            observation_id="observation-invalid",
            object_id="object-1",
            asset_id="asset-1",
            asset_digest="a" * 64,
            description="Unbounded provider text.",
            origin="machine",
        )
        result = DisciplineCritic(self.registry).staged_multimodal_critique(
            research_plan={}, evidence_matrix={"rows": []}, draft={"claims": []}, observations=[invalid]
        )
        self.assertTrue(result.limitations)
        self.assertTrue(result.art_history.mandatory_failures)

    def test_specialist_routes_are_disabled_and_pack_fallback_is_executable(self) -> None:
        self.assertEqual("pack_only", specialist_route("art_history", promoted=False)["mode"])
        self.assertEqual("pack_only", specialist_route("art_criticism", promoted=False)["mode"])
        self.assertEqual("pack_only", specialist_route("art_history", promoted=True)["fallback"])
        for name in ("art-history", "art-criticism"):
            payload = json.loads((ROOT / "agents" / "research-grade" / f"{name}.agent.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["enabled"])
            self.assertEqual("2.0.0", payload["version"])
            self.assertNotIn("export", payload["permissions"])


if __name__ == "__main__":
    unittest.main()
