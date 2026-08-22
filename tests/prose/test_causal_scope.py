from __future__ import annotations

import unittest

from swos_prose.models import VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.verify.causal_scope import (
    causal_polarity_signals,
    reviewed_association_markers,
)


def _proposition(
    prop_id: str,
    text: str,
    *,
    attribution: dict[str, str] | None = None,
) -> dict:
    return {
        "id": prop_id,
        "text": text,
        "subject": None,
        "relation": None,
        "object": None,
        "modality": None,
        "modality_scope": None,
        "attribution": attribution,
        "causal_force": "none",
        "temporal_relation": None,
        "normative_stance": "neutral",
        "relation_sign": "neutral",
        "claim_type": "other",
        "epistemic_type": "none",
    }


def _equivalent_payload(
    source: str,
    candidate: str,
    *,
    attribution: dict[str, str] | None = None,
) -> dict:
    return {
        "equivalent": True,
        "independent_of_rewriter": True,
        "source_propositions": [
            _proposition("p1", source, attribution=attribution)
        ],
        "candidate_propositions": [
            _proposition("c1", candidate, attribution=attribution)
        ],
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
            "reason": "Equivalent attribution/causality paraphrase.",
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


class CausalScopeTests(unittest.TestCase):
    def test_reviewed_nominal_association_is_recognized(self):
        self.assertEqual(
            reviewed_association_markers(
                "The analysis reports an association between load and latency."
            ),
            ("association between",),
        )

    def test_reviewed_denial_heads_partition_embedded_causality(self):
        for sentence in (
            "The authors do not claim that X caused Y.",
            "The analysis does not demonstrate that X caused Y.",
        ):
            with self.subTest(sentence=sentence):
                signals = causal_polarity_signals(sentence)
                self.assertEqual(signals.affirmative, ())
                self.assertEqual(signals.denied, ("caused",))

    def test_exact_dogfood_pair_routes_to_review_without_causal_blocker(self):
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
        attribution = {"agent": "Chen et al.", "act": "report"}
        verifier = StaticSemanticVerifierProvider(
            _equivalent_payload(
                source,
                candidate,
                attribution=attribution,
            )
        )

        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=verifier,
        )

        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertTrue(result.verifier_used)
        self.assertEqual(verifier.calls, 1)
        delta_types = [delta.delta_type.value for delta in result.semantic_deltas]
        self.assertIn("unresolved_equivalence", delta_types)
        self.assertNotIn("causal_strength_changed", delta_types)
        self.assertNotIn("malformed_provider_response", delta_types)

    def test_simple_affirmative_association_to_causation_routes_to_repair(self):
        source = "Exposure was associated with higher fatigue."
        candidate = "Exposure caused higher fatigue."
        verifier = StaticSemanticVerifierProvider(_equivalent_payload(source, candidate))

        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=verifier,
        )

        self.assertEqual(result.status, VerificationStatus.REPAIR)
        self.assertEqual(result.verifier_skip_reason, "deterministic_repairable:causal_strength_changed")
        self.assertEqual(verifier.calls, 0)
        self.assertIn(
            "causal_strength_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_changed_denied_causal_content_requires_review(self):
        source = "The authors do not claim that exposure caused fatigue."
        candidate = "The authors do not claim that exposure produced fatigue."
        verifier = StaticSemanticVerifierProvider(_equivalent_payload(source, candidate))

        result = verify_rewrite(
            source=source,
            candidate=candidate,
            assurance="strict",
            verifier_provider=verifier,
        )

        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertTrue(result.verifier_used)
        self.assertIn(
            "causal_strength_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )

    def test_contrasting_clause_is_outside_denial_scope(self):
        source = (
            "The report does not claim that X caused Y, but Z was associated with W."
        )
        candidate = (
            "The report does not claim that X caused Y, but Z caused W."
        )
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
            "causal_strength_changed",
            [delta.delta_type.value for delta in result.semantic_deltas],
        )


if __name__ == "__main__":
    unittest.main()
