from __future__ import annotations

import unittest

from swos_prose.models import VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.base import ProviderAssessment
from swos_prose.providers.mock import StaticSemanticVerifierProvider


class EquivalentVerifier:
    def verify(self, **kwargs):
        return ProviderAssessment(
            equivalent=True,
            independent_of_rewriter=True,
            notes=["Test verifier judged propositions equivalent."],
        )


def _structured_equivalence(source: str, candidate: str) -> dict:
    def proposition(prop_id: str, value: str) -> dict:
        return {
            "id": prop_id,
            "text": value,
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
            "claim_type": "other",
            "epistemic_type": "none",
        }

    return {
        "equivalent": True,
        "independent_of_rewriter": True,
        "source_propositions": [proposition("p1", source)],
        "candidate_propositions": [proposition("c1", candidate)],
        "source_to_candidate": [{
            "source_id": "p1",
            "candidate_ids": ["c1"],
            "preserved": True,
            "modality_preserved": True,
            "scope_preserved": True,
            "attribution_preserved": True,
            "causal_force_preserved": True,
            "relational_direction_preserved": True,
            "confidence": 0.99,
            "reason": "Equivalent proposition and referential scope.",
        }],
        "candidate_to_source": [{
            "candidate_id": "c1",
            "source_ids": ["p1"],
            "licensed": True,
            "new_claim": False,
            "confidence": 0.99,
            "reason": "Fully licensed by source.",
        }],
        "unresolved": [],
        "notes": ["Structured independent equivalence witness."],
    }


class SemanticDeltaTests(unittest.TestCase):
    def test_identical_text_passes_without_model(self):
        result = verify_rewrite(source="The result may vary.", candidate="The result may vary.")
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_terminal_newline_only_is_no_change_before_verifier(self):
        result = verify_rewrite(
            source="The claim is unchanged.\n",
            candidate="The claim is unchanged.",
            verifier_provider=EquivalentVerifier(),
            assurance="strict",
        )

        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertFalse(result.verifier_used)
        self.assertEqual(result.verifier_skip_reason, "terminal_newline_only")
        self.assertEqual(result.semantic_deltas, [])

    def test_terminal_spaces_are_not_silently_normalized(self):
        result = verify_rewrite(
            source="The claim is unchanged. ",
            candidate="The claim is unchanged.",
            assurance="strict",
        )

        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertEqual(result.verifier_skip_reason, "no_verifier_bound")

    def test_changed_text_without_semantic_verifier_requires_review(self):
        result = verify_rewrite(
            source="The experiment was difficult to reproduce.",
            candidate="The experiment proved difficult to reproduce.",
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn("unresolved_equivalence", [d.delta_type.value for d in result.semantic_deltas])

    def test_safe_changed_text_can_pass_with_independent_verifier(self):
        result = verify_rewrite(
            source="Owing to the fact that the sample was small, the estimate was imprecise.",
            candidate="Because the sample was small, the estimate was imprecise.",
            verifier_provider=EquivalentVerifier(),
        )
        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertTrue(result.verifier_used)
        self.assertTrue(result.verifier_independent)

    def test_number_change_is_rejected(self):
        result = verify_rewrite(
            source="The response rate was 18.7%.",
            candidate="The response rate was 19%.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("number_changed", [d.delta_type.value for d in result.semantic_deltas])

    def test_quote_change_is_rejected(self):
        result = verify_rewrite(
            source='The paper states “no clear effect was observed”.',
            candidate='The paper states “a clear effect was observed”.',
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("quotation_changed", [d.delta_type.value for d in result.semantic_deltas])

    def test_citation_removal_is_rejected(self):
        result = verify_rewrite(
            source="The result was replicated [17].",
            candidate="The result was replicated.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("citation_removed", [d.delta_type.value for d in result.semantic_deltas])

    def test_simple_negation_flip_routes_to_repair(self):
        result = verify_rewrite(
            source="The study did not demonstrate a benefit.",
            candidate="The study demonstrated a benefit.",
        )
        self.assertEqual(result.status, VerificationStatus.REPAIR)
        self.assertEqual(result.verifier_skip_reason, "deterministic_repairable:negation_changed")
        self.assertIn("negation_changed", [d.delta_type.value for d in result.semantic_deltas])

    def test_weak_modal_removal_routes_to_repair(self):
        result = verify_rewrite(
            source="The treatment may improve retention.",
            candidate="The treatment improves retention.",
        )
        self.assertEqual(result.status, VerificationStatus.REPAIR)
        self.assertEqual(result.verifier_skip_reason, "deterministic_repairable:modality_strengthened")
        self.assertIn("modality_strengthened", [d.delta_type.value for d in result.semantic_deltas])

    def test_suggestive_to_demonstrative_is_rejected(self):
        result = verify_rewrite(
            source="The pattern suggests a relationship.",
            candidate="The pattern demonstrates a relationship.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)

    def test_simple_association_to_causation_routes_to_repair(self):
        result = verify_rewrite(
            source="Exposure was associated with higher fatigue.",
            candidate="Exposure caused higher fatigue.",
        )
        self.assertEqual(result.status, VerificationStatus.REPAIR)
        self.assertEqual(result.verifier_skip_reason, "deterministic_repairable:causal_strength_changed")
        self.assertIn("causal_strength_changed", [d.delta_type.value for d in result.semantic_deltas])

    def test_anaphoric_all_routes_to_verifier_and_can_pass(self):
        source = (
            "The verifier, rewriter, deterministic checks and provider contracts "
            "each perform different roles, and these roles are important."
        )
        candidate = (
            "The verifier, rewriter, deterministic checks, and provider contracts "
            "each serve different roles, all of which are important."
        )
        verifier = StaticSemanticVerifierProvider(
            _structured_equivalence(source, candidate)
        )

        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=verifier,
        )

        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertTrue(result.verifier_used)
        self.assertIsNone(result.verifier_skip_reason)
        self.assertNotIn(
            "quantifier_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_anaphoric_all_without_verifier_requires_review(self):
        source = (
            "The verifier and rewriter perform different roles, "
            "and these roles are important."
        )
        candidate = (
            "The verifier and rewriter perform different roles, "
            "all of which are important."
        )

        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
        )

        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertFalse(result.verifier_used)
        self.assertEqual(result.verifier_skip_reason, "no_verifier_bound")
        self.assertIn(
            "quantifier_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_bare_all_strengthening_remains_rejected(self):
        result = verify_rewrite(
            source="Participants reported fatigue.",
            candidate="All participants reported fatigue.",
            assurance="strict",
        )

        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertEqual(
            result.verifier_skip_reason,
            "deterministic_blocker:quantifier_changed",
        )

    def test_quantifier_strengthening_routes_to_repair(self):
        result = verify_rewrite(
            source="Some participants reported fatigue.",
            candidate="Most participants reported fatigue.",
        )
        self.assertEqual(result.status, VerificationStatus.REPAIR)
        self.assertEqual(result.verifier_skip_reason, "deterministic_repairable:quantifier_changed")
        self.assertIn("quantifier_changed", [d.delta_type.value for d in result.semantic_deltas])

    def test_scope_removal_never_auto_passes(self):
        result = verify_rewrite(
            source="In this sample, attendance improved.",
            candidate="Attendance improved.",
            verifier_provider=EquivalentVerifier(),
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn("scope_broadened", [d.delta_type.value for d in result.semantic_deltas])

    def test_attribution_removal_is_rejected(self):
        result = verify_rewrite(
            source="Ahmed argues that the classification is unstable.",
            candidate="The classification is unstable.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("attribution_changed", [d.delta_type.value for d in result.semantic_deltas])


if __name__ == "__main__":
    unittest.main()
