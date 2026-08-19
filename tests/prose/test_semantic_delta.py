from __future__ import annotations

import unittest

from swos_prose.models import VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.base import ProviderAssessment


class EquivalentVerifier:
    def verify(self, **kwargs):
        return ProviderAssessment(
            equivalent=True,
            independent_of_rewriter=True,
            notes=["Test verifier judged propositions equivalent."],
        )


class SemanticDeltaTests(unittest.TestCase):
    def test_identical_text_passes_without_model(self):
        result = verify_rewrite(source="The result may vary.", candidate="The result may vary.")
        self.assertEqual(result.status, VerificationStatus.PASS)

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

    def test_negation_flip_is_rejected(self):
        result = verify_rewrite(
            source="The study did not demonstrate a benefit.",
            candidate="The study demonstrated a benefit.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("negation_changed", [d.delta_type.value for d in result.semantic_deltas])

    def test_weak_modal_removal_is_rejected(self):
        result = verify_rewrite(
            source="The treatment may improve retention.",
            candidate="The treatment improves retention.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("modality_strengthened", [d.delta_type.value for d in result.semantic_deltas])

    def test_suggestive_to_demonstrative_is_rejected(self):
        result = verify_rewrite(
            source="The pattern suggests a relationship.",
            candidate="The pattern demonstrates a relationship.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)

    def test_association_to_causation_is_rejected(self):
        result = verify_rewrite(
            source="Exposure was associated with higher fatigue.",
            candidate="Exposure caused higher fatigue.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn("causal_strength_changed", [d.delta_type.value for d in result.semantic_deltas])

    def test_quantifier_strengthening_is_rejected(self):
        result = verify_rewrite(
            source="Some participants reported fatigue.",
            candidate="Most participants reported fatigue.",
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
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
