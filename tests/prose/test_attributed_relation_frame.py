from __future__ import annotations

import unittest

from swos_prose.models import DeltaType, VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.base import Attribution, Proposition
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.verify.propositions import _provider_frame_mismatches


SOURCE = (
    "Chen et al. report that processor load was associated with longer response "
    "times in the observed tests, but they do not claim that processor load "
    "caused the delay."
)
CANDIDATE = (
    "Chen et al. report that processor load was associated with longer response "
    "times in the observed tests, but they do not claim that it caused the delay."
)
ASSOCIATION = (
    "Chen et al. report that processor load was associated with longer response "
    "times in the observed tests."
)


def _proposition(
    prop_id: str,
    text: str,
    *,
    subject: str | None = None,
    relation: str | None = None,
    object_: str | None = None,
    attribution: dict | None = None,
    causal_force: str = "none",
) -> dict:
    return {
        "id": prop_id,
        "text": text,
        "subject": subject,
        "relation": relation,
        "object": object_,
        "modality": None,
        "modality_scope": None,
        "attribution": attribution,
        "causal_force": causal_force,
        "temporal_relation": None,
        "normative_stance": "neutral",
        "relation_sign": "neutral",
        "claim_type": "empirical",
        "epistemic_type": "report",
    }


def _mapping(source_id: str, candidate_id: str) -> tuple[dict, dict]:
    return (
        {
            "source_id": source_id,
            "candidate_ids": [candidate_id],
            "preserved": True,
            "modality_preserved": True,
            "scope_preserved": True,
            "attribution_preserved": True,
            "causal_force_preserved": True,
            "relational_direction_preserved": True,
            "confidence": 0.99,
            "reason": "Equivalent proposition.",
        },
        {
            "candidate_id": candidate_id,
            "source_ids": [source_id],
            "licensed": True,
            "new_claim": False,
            "confidence": 0.99,
            "reason": "Candidate proposition is licensed by source.",
        },
    )


def _exact_chen_payload(*, candidate_subject: str = "processor load", candidate_agent: str = "Chen et al.") -> dict:
    s1_to_c1, c1_to_s1 = _mapping("s1", "c1")
    s2_to_c2, c2_to_s2 = _mapping("s2", "c2")
    attribution = {"agent": "Chen et al.", "act": "report"}
    candidate_attribution = {"agent": candidate_agent, "act": "report"}
    denied_source = "They do not claim that processor load caused the delay."
    denied_candidate = "They do not claim that it caused the delay."

    return {
        "equivalent": True,
        "independent_of_rewriter": True,
        "source_propositions": [
            _proposition(
                "s1",
                ASSOCIATION,
                subject="processor load",
                relation="associated with",
                object_="longer response times",
                attribution=attribution,
                causal_force="association",
            ),
            _proposition("s2", denied_source, causal_force="none"),
        ],
        "candidate_propositions": [
            _proposition(
                "c1",
                ASSOCIATION,
                subject=candidate_subject,
                relation="associated with",
                object_="longer response times",
                attribution=candidate_attribution,
                causal_force="association",
            ),
            _proposition("c2", denied_candidate, causal_force="none"),
        ],
        "source_to_candidate": [s1_to_c1, s2_to_c2],
        "candidate_to_source": [c1_to_s1, c2_to_s2],
        "unresolved": [],
        "notes": [],
    }


class AttributedRelationFrameTests(unittest.TestCase):
    def test_exact_chen_pair_does_not_fail_on_attributed_relation_subject_object(self):
        provider = StaticSemanticVerifierProvider(_exact_chen_payload())

        result = verify_rewrite(
            source=SOURCE,
            candidate=CANDIDATE,
            assurance="strict",
            verifier_provider=provider,
        )

        malformed = [
            delta for delta in result.semantic_deltas
            if delta.delta_type == DeltaType.MALFORMED_PROVIDER_RESPONSE
        ]
        self.assertEqual(malformed, [])
        self.assertTrue(result.verifier_used)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_contradictory_inner_subject_is_still_malformed(self):
        provider = StaticSemanticVerifierProvider(
            _exact_chen_payload(candidate_subject="memory usage")
        )

        result = verify_rewrite(
            source=SOURCE,
            candidate=CANDIDATE,
            assurance="strict",
            verifier_provider=provider,
        )

        self.assertIn(
            DeltaType.MALFORMED_PROVIDER_RESPONSE,
            [delta.delta_type for delta in result.semantic_deltas],
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)

    def test_attribution_mismatch_remains_independently_detectable(self):
        provider = StaticSemanticVerifierProvider(
            _exact_chen_payload(candidate_agent="Lee")
        )

        result = verify_rewrite(
            source=SOURCE,
            candidate=CANDIDATE,
            assurance="strict",
            verifier_provider=provider,
        )

        types = [delta.delta_type for delta in result.semantic_deltas]
        self.assertIn(DeltaType.ATTRIBUTION_CHANGED, types)
        self.assertIn(DeltaType.MALFORMED_PROVIDER_RESPONSE, types)
        self.assertNotEqual(result.status, VerificationStatus.PASS)

    def test_conflicting_relation_context_is_not_normalized_away(self):
        proposition = Proposition(
            proposition_id="p1",
            text="Mortality was associated with exposure in the study.",
            subject="Mortality",
            relation="associated with",
            object="exposure in the population",
            relation_sign="neutral",
        )

        self.assertIn("object", _provider_frame_mismatches(proposition))

    def test_comma_led_observed_test_context_keeps_inner_subject(self):
        proposition = Proposition(
            proposition_id="p2",
            text=(
                "Chen et al. report that, in the observed tests, processor load "
                "was associated with longer response times."
            ),
            subject="processor load",
            relation="associated with",
            object="longer response times",
            attribution=Attribution(agent="Chen et al.", act="report"),
            relation_sign="neutral",
        )

        self.assertEqual(_provider_frame_mismatches(proposition), [])


if __name__ == "__main__":
    unittest.main()
