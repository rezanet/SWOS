from __future__ import annotations

import unittest

from swos_prose.models import DeltaType, VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.providers.openai_responses import SEMANTIC_VERIFIER_INSTRUCTIONS
from swos_prose.verify.deterministic import deterministic_deltas


def prop(
    prop_id: str,
    text: str,
    *,
    claim_type: str | None = None,
    epistemic_type: str | None = None,
):
    return {
        "id": prop_id,
        "text": text,
        "subject": None,
        "relation": None,
        "object": None,
        "modality": None,
        "modality_scope": None,
        "attribution": None,
        "causal_force": "none",
        "temporal_relation": None,
        "normative_stance": "neutral",
        "relation_sign": "neutral",
        "claim_type": claim_type,
        "epistemic_type": epistemic_type,
    }


def one_to_one(source_prop: dict, candidate_prop: dict) -> dict:
    return {
        "equivalent": True,
        "independent_of_rewriter": True,
        "source_propositions": [source_prop],
        "candidate_propositions": [candidate_prop],
        "source_to_candidate": [{
            "source_id": source_prop["id"],
            "candidate_ids": [candidate_prop["id"]],
            "preserved": True,
            "modality_preserved": True,
            "scope_preserved": True,
            "attribution_preserved": True,
            "causal_force_preserved": True,
            "relational_direction_preserved": True,
            "confidence": 0.99,
            "reason": "Mapped for Slice 4 coverage test.",
        }],
        "candidate_to_source": [{
            "candidate_id": candidate_prop["id"],
            "source_ids": [source_prop["id"]],
            "licensed": True,
            "new_claim": False,
            "confidence": 0.99,
            "reason": "Licensed by source.",
        }],
        "unresolved": [],
        "notes": [],
    }


class Slice4CoverageTests(unittest.TestCase):
    def test_prompt_distinguishes_materiality_and_discourse_relations(self):
        lowered = " ".join(SEMANTIC_VERIFIER_INSTRUCTIONS.casefold().split())
        self.assertIn("purely rhetorical modifier", lowered)
        self.assertIn("first", lowered)
        self.assertIn("therefore", lowered)
        self.assertIn("claim_type", lowered)
        self.assertIn("epistemic_type", lowered)
        self.assertIn("do not infer negation from a prefix mechanically", lowered)

    def test_nonmaterial_parenthetical_evaluation_can_be_omitted(self):
        source = "The findings, which were surprising, suggest a new approach."
        candidate = "The findings suggest a new approach."
        material = "The findings suggest a new approach."
        provider = StaticSemanticVerifierProvider(one_to_one(
            prop("p1", material, claim_type="interpretive", epistemic_type="inference"),
            prop("c1", material, claim_type="interpretive", epistemic_type="inference"),
        ))
        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=provider,
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_material_evaluative_proposition_cannot_be_silently_dropped(self):
        source = "The findings were surprising and challenged the prevailing model."
        candidate = "The findings challenged the prevailing model."
        payload = {
            "equivalent": False,
            "independent_of_rewriter": True,
            "source_propositions": [
                prop("p1", "The findings challenged the prevailing model.", claim_type="interpretive", epistemic_type="inference"),
                prop("p2", "The findings were surprising.", claim_type="evaluative", epistemic_type="evaluation"),
            ],
            "candidate_propositions": [
                prop("c1", "The findings challenged the prevailing model.", claim_type="interpretive", epistemic_type="inference"),
            ],
            "source_to_candidate": [
                {"source_id": "p1", "candidate_ids": ["c1"], "preserved": True, "modality_preserved": True, "scope_preserved": True, "attribution_preserved": True, "causal_force_preserved": True, "relational_direction_preserved": True},
                {"source_id": "p2", "candidate_ids": [], "preserved": False, "modality_preserved": True, "scope_preserved": True, "attribution_preserved": True, "causal_force_preserved": True, "relational_direction_preserved": True},
            ],
            "candidate_to_source": [
                {"candidate_id": "c1", "source_ids": ["p1"], "licensed": True, "new_claim": False},
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
        self.assertIn(DeltaType.CLAIM_REMOVED, [d.delta_type for d in result.semantic_deltas])

    def test_methodological_lexical_variant_preserves_classification(self):
        source = "The analysis was performed using a t-test."
        candidate = "The analysis used a t-test."
        provider = StaticSemanticVerifierProvider(one_to_one(
            prop("p1", source, claim_type="methodological", epistemic_type="method"),
            prop("c1", candidate, claim_type="methodological", epistemic_type="method"),
        ))
        result = verify_rewrite(source=source, candidate=candidate, assurance="strict", verifier_provider=provider)
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_claim_type_mismatch_routes_to_review(self):
        source = "The analysis used a t-test."
        candidate = "A t-test was used in the analysis."
        provider = StaticSemanticVerifierProvider(one_to_one(
            prop("p1", source, claim_type="methodological", epistemic_type="method"),
            prop("c1", candidate, claim_type="interpretive", epistemic_type="method"),
        ))
        result = verify_rewrite(source=source, candidate=candidate, assurance="strict", verifier_provider=provider)
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(DeltaType.UNRESOLVED_EQUIVALENCE, [d.delta_type for d in result.semantic_deltas])

    def test_pure_sequence_marker_change_does_not_create_a_proposition(self):
        source = "First, the results indicate an effect."
        candidate = "To begin, the results indicate an effect."
        proposition_text = "The results indicate an effect."
        provider = StaticSemanticVerifierProvider(one_to_one(
            prop("p1", proposition_text, claim_type="empirical", epistemic_type="observation"),
            prop("c1", proposition_text, claim_type="empirical", epistemic_type="observation"),
        ))
        result = verify_rewrite(source=source, candidate=candidate, assurance="strict", verifier_provider=provider)
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_ineffective_and_not_effective_share_negation_presence(self):
        _, _, deltas = deterministic_deltas(
            "The treatment was ineffective.",
            "The treatment was not effective.",
        )
        self.assertNotIn(DeltaType.NEGATION_CHANGED, [d.delta_type for d in deltas])

    def test_ineffective_to_effective_is_a_negation_change(self):
        _, _, deltas = deterministic_deltas(
            "The treatment was ineffective.",
            "The treatment was effective.",
        )
        self.assertIn(DeltaType.NEGATION_CHANGED, [d.delta_type for d in deltas])

    def test_hypothesis_to_assumption_is_rejected(self):
        source = "We hypothesized that the drug would reduce symptoms."
        candidate = "The drug was expected to reduce symptoms."
        provider = StaticSemanticVerifierProvider(one_to_one(
            prop("p1", source, claim_type="interpretive", epistemic_type="hypothesis"),
            prop("c1", candidate, claim_type="interpretive", epistemic_type="assumption"),
        ))
        result = verify_rewrite(source=source, candidate=candidate, assurance="strict", verifier_provider=provider)
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(DeltaType.EPISTEMIC_TYPE_CHANGED, [d.delta_type for d in result.semantic_deltas])

    def test_unresolved_epistemic_classification_never_passes_strict(self):
        source = "The evidence supports the proposed explanation."
        candidate = "The evidence is consistent with the proposed explanation."
        provider = StaticSemanticVerifierProvider(one_to_one(
            prop("p1", source, claim_type="interpretive", epistemic_type="inference"),
            prop("c1", candidate, claim_type="interpretive", epistemic_type="unknown"),
        ))
        result = verify_rewrite(source=source, candidate=candidate, assurance="strict", verifier_provider=provider)
        self.assertEqual(result.status, VerificationStatus.REVIEW)


if __name__ == "__main__":
    unittest.main()
