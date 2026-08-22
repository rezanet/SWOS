from __future__ import annotations

import unittest

from swos_prose.models import DeltaType, VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.mock import StaticSemanticVerifierProvider


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
        "claim_type": "empirical",
        "epistemic_type": "report",
    }


class ReviewedContextMappingCardinalityTests(unittest.TestCase):
    def test_split_mapping_touching_reviewed_context_requires_review(self):
        source = (
            "A was associated with B in the observed tests, but they do not "
            "claim that A caused B."
        )
        candidate = (
            "A was associated with B in the observed tests. They do not claim "
            "that memory usage caused B."
        )
        payload = {
            "equivalent": True,
            "independent_of_rewriter": True,
            "source_propositions": [_proposition("s1", source)],
            "candidate_propositions": [
                _proposition("c1", "A was associated with B in the observed tests."),
                _proposition("c2", "They do not claim that memory usage caused B."),
            ],
            "source_to_candidate": [{
                "source_id": "s1",
                "candidate_ids": ["c1", "c2"],
                "preserved": True,
                "modality_preserved": True,
                "scope_preserved": True,
                "attribution_preserved": True,
                "causal_force_preserved": True,
                "relational_direction_preserved": True,
                "confidence": 0.99,
                "reason": "Provider claims the split preserves the source proposition.",
            }],
            "candidate_to_source": [
                {
                    "candidate_id": "c1",
                    "source_ids": ["s1"],
                    "licensed": True,
                    "new_claim": False,
                    "confidence": 0.99,
                    "reason": "Provider claims the association is licensed.",
                },
                {
                    "candidate_id": "c2",
                    "source_ids": ["s1"],
                    "licensed": True,
                    "new_claim": False,
                    "confidence": 0.99,
                    "reason": "Provider claims the denial is licensed.",
                },
            ],
            "unresolved": [],
            "notes": [],
        }
        verifier = StaticSemanticVerifierProvider(payload)

        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=verifier,
        )

        self.assertTrue(result.verifier_used)
        self.assertEqual(verifier.calls, 1)
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in result.semantic_deltas],
        )


if __name__ == "__main__":
    unittest.main()
