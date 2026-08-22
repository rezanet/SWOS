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
                "relational_direction_preserved": True,
            },
            {
                "source_id": "p2",
                "candidate_ids": ["c2"],
                "preserved": True,
                "modality_preserved": True,
                "scope_preserved": True,
                "attribution_preserved": True,
                "causal_force_preserved": True,
                "relational_direction_preserved": True,
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
                "The sample was small, and the estimate was imprecise. The study was underpowered."
            ),
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("claim_added", [d.delta_type.value for d in result.semantic_deltas])

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
        self.assertIn("claim_removed", [d.delta_type.value for d in result.semantic_deltas])

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
                    "relational_direction_preserved": True,
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
            "epistemic_type_changed", [d.delta_type.value for d in result.semantic_deltas]
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
            "unresolved_equivalence", [d.delta_type.value for d in result.semantic_deltas]
        )

    def test_strict_bare_equivalence_is_not_enough(self):
        provider = StaticSemanticVerifierProvider(
            {
                "equivalent": True,
                "independent_of_rewriter": True,
            }
        )
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

    def test_strict_missing_source_mapping_is_rejected_as_incomplete_report(self):
        payload = complete_equivalent_payload()
        payload["source_to_candidate"] = payload["source_to_candidate"][:1]
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="The sample was small, and the estimate was imprecise.",
            candidate="The sample was small, and the estimate was imprecise in this dataset.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(
            "malformed_provider_response", [d.delta_type.value for d in result.semantic_deltas]
        )

    def test_standard_missing_source_mapping_routes_to_review(self):
        payload = complete_equivalent_payload()
        payload["source_to_candidate"] = payload["source_to_candidate"][:1]
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="The sample was small, and the estimate was imprecise.",
            candidate="The sample was small, and the estimate was imprecise in this dataset.",
            assurance="standard",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)

    def test_orphan_candidate_without_licensing_mapping_is_rejected(self):
        payload = complete_equivalent_payload()
        payload["candidate_propositions"].append(
            {"id": "c3", "text": "The hypothesis was confirmed."}
        )
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="The sample was small, and the estimate was imprecise.",
            candidate="The sample was small. The estimate was imprecise. The hypothesis was confirmed.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("claim_added", [d.delta_type.value for d in result.semantic_deltas])

    def test_unknown_candidate_id_in_mapping_never_crashes_and_routes_to_review(self):
        payload = complete_equivalent_payload()
        payload["source_to_candidate"][0]["candidate_ids"] = ["c-999"]
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="The sample was small, and the estimate was imprecise.",
            candidate="The sample was small, while the estimate remained imprecise.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(
            "malformed_provider_response", [d.delta_type.value for d in result.semantic_deltas]
        )

    def test_unknown_source_id_in_mapping_never_crashes_and_routes_to_review(self):
        payload = complete_equivalent_payload()
        payload["candidate_to_source"][0]["source_ids"] = ["p-999"]
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="The sample was small, and the estimate was imprecise.",
            candidate="The sample was small, while the estimate remained imprecise.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(
            "malformed_provider_response", [d.delta_type.value for d in result.semantic_deltas]
        )

    def test_core_detects_relation_direction_reversal_even_if_provider_says_preserved(self):
        payload = {
            "equivalent": True,
            "independent_of_rewriter": True,
            "source_propositions": [
                {"id": "p1", "text": "Depression is associated with a sedentary lifestyle."}
            ],
            "candidate_propositions": [
                {"id": "c1", "text": "A sedentary lifestyle is associated with depression."}
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
                    "relational_direction_preserved": True,
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
        }
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="Depression is associated with a sedentary lifestyle.",
            candidate="A sedentary lifestyle is associated with depression.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("direction_reversal", [d.delta_type.value for d in result.semantic_deltas])

    def test_provider_direction_fields_cannot_disagree_with_core_parse_silently(self):
        payload = complete_equivalent_payload()
        payload["source_propositions"] = [
            {
                "id": "p1",
                "text": "A is associated with B.",
                "subject": "B",
                "relation": "associated with",
                "object": "A",
            }
        ]
        payload["candidate_propositions"] = [{"id": "c1", "text": "A is associated with B."}]
        payload["source_to_candidate"] = [
            {
                "source_id": "p1",
                "candidate_ids": ["c1"],
                "preserved": True,
                "modality_preserved": True,
                "scope_preserved": True,
                "attribution_preserved": True,
                "causal_force_preserved": True,
                "relational_direction_preserved": True,
            }
        ]
        payload["candidate_to_source"] = [
            {
                "candidate_id": "c1",
                "source_ids": ["p1"],
                "licensed": True,
                "new_claim": False,
            }
        ]
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source="A is associated with B.",
            candidate="A is associated with B with the same interpretation.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(
            "malformed_provider_response", [d.delta_type.value for d in result.semantic_deltas]
        )

    def test_empty_source_and_candidate_is_explicit_no_change_pass(self):
        result = verify_rewrite(source="", candidate="", assurance="strict")
        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertIn("no change recommended", result.notes[0].casefold())

    def test_empty_source_with_added_candidate_is_rejected(self):
        result = verify_rewrite(source="", candidate="A new claim.", assurance="strict")
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("claim_added", [d.delta_type.value for d in result.semantic_deltas])

    def test_changed_heading_with_empty_proposition_report_routes_to_review(self):
        provider = StaticSemanticVerifierProvider(
            {
                "equivalent": True,
                "source_propositions": [],
                "candidate_propositions": [],
                "source_to_candidate": [],
                "candidate_to_source": [],
            }
        )
        result = verify_rewrite(
            source="Chapter 3: Methodology",
            candidate="Chapter 3: Methods",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)

    def test_malformed_provider_payload_does_not_crash(self):
        provider = StaticSemanticVerifierProvider(
            {
                "equivalent": True,
                "source_propositions": [{"id": "p1"}],
            }
        )
        result = verify_rewrite(
            source="The sample was small.",
            candidate="The sample remained small.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(
            "malformed_provider_response", [d.delta_type.value for d in result.semantic_deltas]
        )


if __name__ == "__main__":
    unittest.main()
