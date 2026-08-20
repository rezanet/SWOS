from __future__ import annotations

import unittest

from swos_prose.models import VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.verify.negation_equivalence import REVIEWED_NEGATION_EQUIVALENCES


def _proposition(prop_id: str, text: str) -> dict:
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
        "claim_type": "other",
        "epistemic_type": "none",
    }


def _equivalent_payload(source: str, candidate: str) -> dict:
    return {
        "equivalent": True,
        "independent_of_rewriter": True,
        "source_propositions": [_proposition("p1", source)],
        "candidate_propositions": [_proposition("c1", candidate)],
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
            "reason": "Reviewed lexical-negation paraphrase preserves the proposition.",
        }],
        "candidate_to_source": [{
            "candidate_id": "c1",
            "source_ids": ["p1"],
            "licensed": True,
            "new_claim": False,
            "confidence": 0.99,
            "reason": "Candidate is fully licensed by the source.",
        }],
        "unresolved": [],
        "notes": [],
    }


class ReviewedNegationEquivalenceTests(unittest.TestCase):
    def test_table_begins_with_observed_reviewed_pair_only(self):
        self.assertEqual(
            REVIEWED_NEGATION_EQUIVALENCES,
            (("not sufficient", "insufficient"),),
        )

    def test_not_sufficient_and_insufficient_route_to_verifier_in_both_directions(self):
        pairs = (
            (
                "The available evidence is not sufficient to establish a causal relationship.",
                "The available evidence is insufficient to establish a causal relationship.",
            ),
            (
                "The available evidence is insufficient to establish a causal relationship.",
                "The available evidence is not sufficient to establish a causal relationship.",
            ),
        )

        for source, candidate in pairs:
            with self.subTest(source=source):
                verifier = StaticSemanticVerifierProvider(
                    _equivalent_payload(source, candidate)
                )
                result = verify_rewrite(
                    source=source,
                    candidate=candidate,
                    assurance="strict",
                    verifier_provider=verifier,
                )

                self.assertEqual(result.status, VerificationStatus.PASS)
                self.assertTrue(result.verifier_used)
                self.assertEqual(verifier.calls, 1)
                self.assertNotIn(
                    "negation_changed",
                    [delta.delta_type.value for delta in result.semantic_deltas],
                )

    def test_adding_reviewed_lexical_negation_remains_a_hard_blocker(self):
        source = "The available evidence is sufficient to establish the claim."
        candidate = "The available evidence is insufficient to establish the claim."
        verifier = StaticSemanticVerifierProvider(_equivalent_payload(source, candidate))

        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=verifier,
        )

        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertEqual(verifier.calls, 0)
        self.assertIn(
            "negation_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_generic_negative_prefix_is_not_inferred(self):
        source = "The result was not valuable."
        candidate = "The result was invaluable."
        verifier = StaticSemanticVerifierProvider(_equivalent_payload(source, candidate))

        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=verifier,
        )

        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertEqual(verifier.calls, 0)
        self.assertIn(
            "negation_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )


if __name__ == "__main__":
    unittest.main()
