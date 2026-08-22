from __future__ import annotations

import os
import unittest

from swos_prose.models import VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.openai_responses import OpenAIResponsesSemanticVerifierProvider


RUN_LIVE = (
    os.environ.get("SWOS_PROSE_RUN_LIVE_OPENAI") == "1"
    and bool(os.environ.get("OPENAI_API_KEY"))
)


@unittest.skipUnless(
    RUN_LIVE,
    "Set SWOS_PROSE_RUN_LIVE_OPENAI=1 and OPENAI_API_KEY to run live provider tests.",
)
class OpenAILiveAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = OpenAIResponsesSemanticVerifierProvider()

    def verify(self, source: str, candidate: str):
        return verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=self.provider,
        )

    def test_entailment_not_topical_similarity(self):
        result = self.verify("X caused Y.", "X was associated with Y.")
        self.assertNotEqual(result.status, VerificationStatus.PASS)

    def test_modal_scope_relocation_never_passes(self):
        result = self.verify(
            "The data may suggest that X causes Y.",
            "The data suggests that X may cause Y.",
        )
        self.assertNotEqual(result.status, VerificationStatus.PASS)

    def test_temporal_inverse_wording_is_equivalent(self):
        result = self.verify(
            "The intervention preceded the outcome.",
            "The outcome followed the intervention.",
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_normative_lexical_paraphrase_is_equivalent(self):
        result = self.verify(
            "The model performs poorly under these conditions.",
            "The model underperforms under these conditions.",
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_methodological_lexical_variant_is_equivalent(self):
        result = self.verify(
            "The analysis was performed using a t-test.",
            "The analysis used a t-test.",
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_pure_sequence_marker_change_is_equivalent(self):
        result = self.verify(
            "First, the results indicate an effect.",
            "To begin, the results indicate an effect.",
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_lexical_negation_paraphrase_is_equivalent(self):
        result = self.verify(
            "The treatment was ineffective.",
            "The treatment was not effective.",
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_reviewed_not_sufficient_paraphrase_reaches_verifier(self):
        result = self.verify(
            "The available evidence is not sufficient to establish a causal relationship.",
            "The available evidence is insufficient to establish a causal relationship.",
        )

        self.assertTrue(result.verifier_used)
        self.assertIn(result.status, {VerificationStatus.PASS, VerificationStatus.REVIEW})
        self.assertNotIn(
            "negation_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_denied_causal_dogfood_pair_reaches_verifier(self):
        source = (
            "Chen et al. report that processor load was associated with longer "
            "response times in the observed tests, but they do not claim that "
            "processor load caused the delay."
        )
        candidate = (
            "Chen et al. report an association between processor load and longer "
            "response times in the observed tests, but do not claim that processor "
            "load caused the delay."
        )
        result = self.verify(source, candidate)

        self.assertTrue(result.verifier_used)
        self.assertIn(result.status, {VerificationStatus.PASS, VerificationStatus.REVIEW})
        self.assertNotIn(
            "causal_strength_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_hypothesis_to_expectation_never_passes(self):
        result = self.verify(
            "We hypothesized that the drug would reduce symptoms.",
            "The drug was expected to reduce symptoms.",
        )
        self.assertNotEqual(result.status, VerificationStatus.PASS)

    def test_parenthetical_surprising_modifier_may_be_nonmaterial(self):
        result = self.verify(
            "The findings, which were surprising, suggest a new approach.",
            "The findings suggest a new approach.",
        )
        # Slice 4 permits PASS only if the verifier classifies the parenthetical
        # evaluation as non-material. REVIEW is also acceptable if materiality is
        # uncertain; a hard REJECT is not required by the core.
        self.assertIn(result.status, {VerificationStatus.PASS, VerificationStatus.REVIEW})


if __name__ == "__main__":
    unittest.main()
