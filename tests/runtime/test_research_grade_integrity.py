"""Cross-story identity bindings across classifier, rights, ontology and EPG."""

from __future__ import annotations

import unittest
from pathlib import Path

from swos_runtime.citation_classifier import CitationPair, CitationSupportDecision
from swos_runtime.discipline_critique import DisciplineCritic
from swos_runtime.discipline_ontology import DisciplineOntologyRegistry
from swos_runtime.image_analysis import (
    DeterministicFakeImageProvider,
    ImageAnalysisRequest,
    evaluate_cross_modal_support,
)
from swos_runtime.media import MediaAssetRecord
from swos_runtime.prov_interop import epg_to_prov, prov_to_epg

ROOT = Path(__file__).resolve().parents[2]


class ResearchGradeIntegrityTests(unittest.TestCase):
    def test_rights_and_asset_digest_are_bound_into_image_request_and_observation(self) -> None:
        allowed = {"view": {"status": "allowed"}, "analyse": {"status": "allowed"}}
        asset = MediaAssetRecord(
            "asset-1",
            "object-1",
            "surrogate",
            "image/jpeg",
            1,
            10,
            10,
            "a" * 64,
            "https://example.org/a",
            rights=allowed,
        )
        first = ImageAnalysisRequest("work", "run", "object-1", (asset,), ("visible?",))
        altered = MediaAssetRecord(
            **{
                **asset.to_dict(),
                "rights": {"view": {"status": "allowed"}, "analyse": {"status": "denied"}},
            }
        )
        second = ImageAnalysisRequest("work", "run", "object-1", (altered,), ("visible?",))
        self.assertNotEqual(first.request_digest, second.request_digest)
        result = DeterministicFakeImageProvider().analyze(first)
        self.assertEqual("a" * 64, result.observations[0].asset_digest)
        self.assertEqual("a" * 64, result.observations[0].provenance["asset_digest"])

    def test_ontology_and_evidence_identity_survive_pack_critique_and_prov_roundtrip(self) -> None:
        registry = DisciplineOntologyRegistry().load(ROOT / "discipline-packs" / "manifest-v2.json")
        profile = registry.profile("art_history")
        report = DisciplineCritic(registry).critique(
            discipline=profile,
            research_plan={},
            evidence_matrix={
                "rows": [
                    {
                        "criterion_iri": profile.required_criteria[0]["iri"],
                        "evidence_refs": ["epg:e1"],
                    }
                ]
            },
            draft={"claims": [{"claim_id": "claim-1"}]},
        )
        self.assertEqual(profile.ontology_digest, report.ontology_digest)
        self.assertIn("epg:e1", report.criteria[0].evidence_refs)
        epg = {
            "schema_version": "2.0.0",
            "profile": "swos.prov-dm-round-trip.v2",
            "base_iri": "https://example.org/",
            "namespaces": {},
            "scope": {"work_id": "w"},
            "entities": {
                "https://example.org/e1": {
                    "type": "entity",
                    "attributes": {"evidence_digest": {"value": "e"}},
                }
            },
            "activities": {},
            "agents": {},
            "relations": [],
            "bundles": {},
            "extensions": [],
            "integrity": {"ontology_digest": profile.ontology_digest},
        }
        roundtripped = prov_to_epg(epg_to_prov(epg, base_iri=epg["base_iri"]))
        self.assertEqual(profile.ontology_digest, roundtripped["integrity"]["ontology_digest"])

    def test_classifier_decision_is_not_a_rights_or_ontology_authority(self) -> None:
        pair = CitationPair(
            pair_id="p",
            claim="Claim",
            passage="Quote",
            context="Context",
            source_id="s",
            span_start=0,
            span_end=5,
            discipline_iri="https://example.org/art-history",
        )
        decision = CitationSupportDecision(
            pair_id=pair.pair_id,
            status="classified",
            support_level="directly_supports",
            probabilities={
                "directly_supports": 0.9,
                "partially_supports": 0.03,
                "context_only": 0.02,
                "contradicts": 0.03,
                "not_supported": 0.02,
            },
            confidence=0.9,
            input={"claim": pair.claim, "source_id": pair.source_id},
            model_digest="m" * 64,
            calibration_digest="c" * 64,
            ontology_digest="d" * 64,
            input_digest=pair.canonical_input_digest,
            deterministic_checks={"passed": True},
        )
        self.assertEqual(pair.canonical_input_digest, decision.input_digest)
        self.assertNotIn("rights", decision.to_dict())
        blocked = evaluate_cross_modal_support(
            {"claim_id": "claim-1", "object_id": "object-1"},
            [],
            [{"claim_id": "claim-1", "support_level": "directly_supports"}],
        )
        self.assertEqual("blocked", blocked.status)


if __name__ == "__main__":
    unittest.main()
