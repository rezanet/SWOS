from __future__ import annotations

import unittest

from swos_prose.models import DeltaType, VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.verify.deterministic import deterministic_deltas


def prop(
    prop_id: str,
    text: str,
    *,
    subject: str | None = None,
    relation: str | None = None,
    object_: str | None = None,
    modality: str | None = None,
    modality_scope: str | None = None,
    attribution: dict | None = None,
    causal_force: str | None = "none",
    temporal_relation: str | None = None,
    normative_stance: str | None = "neutral",
    relation_sign: str | None = "neutral",
) -> dict:
    return {
        "id": prop_id,
        "text": text,
        "subject": subject,
        "relation": relation,
        "object": object_,
        "modality": modality,
        "modality_scope": modality_scope,
        "attribution": attribution,
        "causal_force": causal_force,
        "temporal_relation": temporal_relation,
        "normative_stance": normative_stance,
        "relation_sign": relation_sign,
    }


def one_to_one(source_prop: dict, candidate_prop: dict) -> dict:
    return {
        "equivalent": True,
        "source_propositions": [source_prop],
        "candidate_propositions": [candidate_prop],
        "source_to_candidate": [
            {
                "source_id": source_prop["id"],
                "candidate_ids": [candidate_prop["id"]],
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
                "candidate_id": candidate_prop["id"],
                "source_ids": [source_prop["id"]],
                "licensed": True,
                "new_claim": False,
            }
        ],
        "unresolved": [],
    }


class Slice3SchemaHardeningTests(unittest.TestCase):
    def test_many_to_many_conjunction_split_can_pass(self):
        source = "The intervention improved retention and reduced dropout."
        candidate = "The intervention improved retention. It also reduced dropout."
        payload = {
            "equivalent": True,
            "source_propositions": [
                prop("p1", source, subject="intervention", relation="improved/reduced")
            ],
            "candidate_propositions": [
                prop(
                    "c1",
                    "The intervention improved retention.",
                    subject="intervention",
                    relation="improved",
                    object_="retention",
                ),
                prop(
                    "c2",
                    "It also reduced dropout.",
                    subject="intervention",
                    relation="reduced",
                    object_="dropout",
                ),
            ],
            "source_to_candidate": [
                {
                    "source_id": "p1",
                    "candidate_ids": ["c1", "c2"],
                    "preserved": True,
                    "modality_preserved": True,
                    "scope_preserved": True,
                    "attribution_preserved": True,
                    "causal_force_preserved": True,
                    "relational_direction_preserved": True,
                }
            ],
            "candidate_to_source": [
                {"candidate_id": "c1", "source_ids": ["p1"], "licensed": True, "new_claim": False},
                {"candidate_id": "c2", "source_ids": ["p1"], "licensed": True, "new_claim": False},
            ],
            "unresolved": [],
        }
        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=StaticSemanticVerifierProvider(payload),
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_nonreciprocal_many_to_many_mapping_is_rejected_in_strict_mode(self):
        source = "The intervention improved retention and reduced dropout."
        candidate = "The intervention improved retention. It also reduced dropout."
        payload = {
            "equivalent": True,
            "source_propositions": [prop("p1", source)],
            "candidate_propositions": [
                prop("c1", "The intervention improved retention."),
                prop("c2", "It also reduced dropout."),
            ],
            "source_to_candidate": [
                {
                    "source_id": "p1",
                    "candidate_ids": ["c1", "c2"],
                    "preserved": True,
                    "modality_preserved": True,
                    "scope_preserved": True,
                    "attribution_preserved": True,
                    "causal_force_preserved": True,
                    "relational_direction_preserved": True,
                }
            ],
            "candidate_to_source": [
                {"candidate_id": "c1", "source_ids": ["p1"], "licensed": True, "new_claim": False},
                {"candidate_id": "c2", "source_ids": [], "licensed": True, "new_claim": False},
            ],
            "unresolved": [],
        }
        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=StaticSemanticVerifierProvider(payload),
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(
            DeltaType.MALFORMED_PROVIDER_RESPONSE, [d.delta_type for d in result.semantic_deltas]
        )

    def test_modal_proposition_without_scope_cannot_pass(self):
        source = "The data may suggest that X causes Y."
        candidate = "The data might suggest that X causes Y."
        payload = one_to_one(
            prop("p1", source, modality="may", modality_scope=None, causal_force="causal"),
            prop(
                "c1",
                candidate,
                modality="might",
                modality_scope="suggestion",
                causal_force="causal",
            ),
        )
        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=StaticSemanticVerifierProvider(payload),
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE, [d.delta_type for d in result.semantic_deltas]
        )

    def test_signed_correlation_flip_is_rejected_even_when_relation_is_symmetric(self):
        source = "A is positively correlated with B."
        candidate = "B is negatively correlated with A."
        payload = one_to_one(
            prop(
                "p1",
                source,
                subject="A",
                relation="correlated with",
                object_="B",
                causal_force="association",
                relation_sign="positive",
            ),
            prop(
                "c1",
                candidate,
                subject="B",
                relation="correlated with",
                object_="A",
                causal_force="association",
                relation_sign="negative",
            ),
        )
        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=StaticSemanticVerifierProvider(payload),
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(
            DeltaType.RELATION_SIGN_CHANGED, [d.delta_type for d in result.semantic_deltas]
        )

    def test_attribution_speech_act_change_routes_to_repair_before_provider(self):
        source = "Smith argues that the policy is effective."
        candidate = "Smith states that the policy is effective."
        payload = one_to_one(
            prop("p1", source, attribution={"agent": "Smith", "act": "argues"}),
            prop("c1", candidate, attribution={"agent": "Smith", "act": "states"}),
        )
        provider = StaticSemanticVerifierProvider(payload)
        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REPAIR)
        self.assertEqual(
            result.verifier_skip_reason, "deterministic_repairable:attribution_changed"
        )
        self.assertEqual(provider.calls, 0)
        self.assertIn(DeltaType.ATTRIBUTION_CHANGED, [d.delta_type for d in result.semantic_deltas])

    def test_attribution_drop_is_already_a_deterministic_blocker(self):
        provider = StaticSemanticVerifierProvider({"equivalent": True})
        result = verify_rewrite(
            source="Smith argues that the policy is effective.",
            candidate="The policy is effective.",
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertEqual(provider.calls, 0)
        self.assertIn(DeltaType.ATTRIBUTION_CHANGED, [d.delta_type for d in result.semantic_deltas])

    def test_digit_to_spelled_integer_is_not_a_number_change(self):
        _, _, deltas = deterministic_deltas(
            "The study included 200 participants.",
            "The study included two hundred participants.",
        )
        self.assertNotIn(DeltaType.NUMBER_CHANGED, [d.delta_type for d in deltas])

    def test_spelled_integer_to_digit_is_not_a_number_change(self):
        _, _, deltas = deterministic_deltas(
            "The study included two hundred participants.",
            "The study included 200 participants.",
        )
        self.assertNotIn(DeltaType.NUMBER_CHANGED, [d.delta_type for d in deltas])

    def test_numeric_canonicalizer_does_not_match_prefix_of_larger_word_number(self):
        _, _, deltas = deterministic_deltas(
            "The study included 200 participants.",
            "The study included two hundred and one participants.",
        )
        self.assertIn(DeltaType.NUMBER_CHANGED, [d.delta_type for d in deltas])


if __name__ == "__main__":
    unittest.main()
