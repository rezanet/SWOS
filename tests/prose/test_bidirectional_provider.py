from __future__ import annotations

import json
import unittest

from swos_prose.models import VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.mock import StaticSemanticVerifierProvider


def complete_equivalent_payload():
    return {
        "equivalent": True,
        "independent_of_rewriter": True,
        "source_propositions": [
            {"id": "p1", "text": "The sample was small."},
            {"id": "p2", "text": "The estimate was imprecise."},
        ],
        "candidate_propositions": [
            {"id": "c1", "text": "The sample was small."},
            {"id": "c2", "text": "The estimate was imprecise."},
        ],
        "source_to_candidate": [
            {
                "source_id": "p1",
                "candidate_ids": ["c1"],
                "preserved": True,
                "modality_preserved": True,
                "scope_preserved": True,
                "attribution_preserved": True,
                "causal_force_preserved": True,
            },
            {
                "source_id": "p2",
                "candidate_ids": ["c2"],
                "preserved": True,
                "modality_preserved": True,
                "scope_preserved": True,
                "attribution_preserved": True,
                "causal_force_preserved": True,
            },
        ],
        "candidate_to_source": [
            {
                "candidate_id": "c1",
                "source_ids": ["p1"],
                "licensed": True,
                "new_claim": False,
            },
            {
                "candidate_id": "c2",
                "source_ids": ["p2"],
                "licensed": True,
                "new_claim": False,
            },
        ],
        "unresolved": [],
        "notes": ["Static bidirectional report."],
    }


class BidirectionalProviderTests(unittest.TestCase):
    def test_strict_complete_bidirectional_report_can_pass(self):
        provider = StaticSemanticVerifierProvider(complete_equivalent_payload())
        result = verify_rewrite(
            source="Owing to the fact that the sample was small, the estimate was imprecise.",
            candidate="Because the sample was small, the estimate was imprecise.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertEqual(provider.calls, 1)
        self.assertTrue(result.verifier_used)

    def test_static_provider_accepts_json_payload(self):
        provider = StaticSemanticVerifierProvider(json.dumps(complete_equivalent_payload()))
        result = verify_rewrite(
            source="Owing to the fact that the sample was small, the estimate was imprecise.",
            candidate="Because the sample was small, the estimate was imprecise.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_provider_cannot_override_unlicensed_candidate_claim(self):
        payload = complete_equivalent_payload()
        payload["candidate_propositions"].append(
            {"id": "c3", "text": "The study was underpowered."}
        )
        payload["candidate_to_source"].append(
            {
                "candidate_id": "c3",
                "source_ids": [],
                "licensed": False,
                "new_claim": True,
            }
        )
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="The sample was small, and the estimate was imprecise.",
            candidate=(
                "The sample was small, and the estimate was imprecise. "
                "The study was underpowered."
            ),
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(
            "claim_added",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_provider_cannot_override_lost_source_claim(self):
        payload = complete_equivalent_payload()
        payload["source_to_candidate"][1]["preserved"] = False
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="The sample was small, and the estimate was imprecise.",
            candidate="The sample was small.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(
            "claim_removed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_explicit_modality_preservation_failure_blocks(self):
        payload = {
            "equivalent": True,
            "independent_of_rewriter": True,
            "source_propositions": [{"id": "p1", "text": "The treatment may help."}],
            "candidate_propositions": [{"id": "c1", "text": "The treatment could help."}],
            "source_to_candidate": [
                {
                    "source_id": "p1",
                    "candidate_ids": ["c1"],
                    "preserved": True,
                    "modality_preserved": False,
                    "scope_preserved": True,
                    "attribution_preserved": True,
                    "causal_force_preserved": True,
                }
            ],
            "candidate_to_source": [
                {
                    "candidate_id": "c1",
                    "source_ids": ["p1"],
                    "licensed": True,
                    "new_claim": False,
                }
            ],
            "unresolved": [],
        }
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="The treatment may help.",
            candidate="The treatment could help.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(
            "epistemic_type_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_unresolved_report_routes_to_review(self):
        payload = complete_equivalent_payload()
        payload["unresolved"] = ["Whether the reordered clause preserves scope."]
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="Owing to the fact that the sample was small, the estimate was imprecise.",
            candidate="Because the sample was small, the estimate was imprecise.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(
            "unresolved_equivalence",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_strict_bare_equivalence_is_not_enough(self):
        provider = StaticSemanticVerifierProvider({
            "equivalent": True,
            "independent_of_rewriter": True,
        })
        result = verify_rewrite(
            source="The experiment was difficult to reproduce.",
            candidate="The experiment proved difficult to reproduce.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)

    def test_deterministic_blocker_short_circuits_provider(self):
        provider = StaticSemanticVerifierProvider(complete_equivalent_payload())
        result = verify_rewrite(
            source="The response rate was 18.7%.",
            candidate="The response rate was 19%.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertEqual(provider.calls, 0)

    def test_missing_candidate_mapping_routes_to_review(self):
        payload = complete_equivalent_payload()
        payload["candidate_to_source"] = payload["candidate_to_source"][:1]
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="Owing to the fact that the sample was small, the estimate was imprecise.",
            candidate="Because the sample was small, the estimate was imprecise.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)


if __name__ == "__main__":
    unittest.main()
