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


if __name__ == "__main__":
    unittest.main()
