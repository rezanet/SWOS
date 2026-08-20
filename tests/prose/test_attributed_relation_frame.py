from __future__ import annotations

import unittest

from swos_prose.models import DeltaType, VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.base import Attribution, Proposition
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.verify.propositions import (
    _frame_consistency_deltas,
    _is_symmetric_swap,
    _provider_frame_mismatches,
)


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

    def test_provider_only_observed_test_scope_is_rejected(self):
        proposition = Proposition(
            proposition_id="p2",
            text="Mortality was associated with exposure.",
            subject="Mortality",
            relation="associated with",
            object="exposure in the observed tests",
            relation_sign="neutral",
        )

        self.assertIn("object", _provider_frame_mismatches(proposition))

    def test_comma_led_observed_test_context_keeps_inner_subject(self):
        proposition = Proposition(
            proposition_id="p3",
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

    def test_outer_reporting_frame_requires_complete_embedded_claim(self):
        text = "Chen et al. report that mortality was associated with exposure."
        attribution = Attribution(agent="Chen et al.", act="report")
        for bad_object in (
            "mortality",
            "mortality was associated with exposure and caused harm",
        ):
            with self.subTest(object=bad_object):
                proposition = Proposition(
                    proposition_id="p4",
                    text=text,
                    subject="Chen et al.",
                    relation="report",
                    object=bad_object,
                    attribution=attribution,
                    relation_sign="neutral",
                )
                self.assertIn("object", _provider_frame_mismatches(proposition))

    def test_outer_reporting_frames_can_prove_symmetric_relation_swap(self):
        attribution = Attribution(agent="Chen et al.", act="report")
        source = Proposition(
            proposition_id="s1",
            text="Chen et al. report that A was associated with B.",
            subject="Chen et al.",
            relation="report",
            object="A was associated with B",
            attribution=attribution,
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c1",
            text="Chen et al. report that B was associated with A.",
            subject="Chen et al.",
            relation="report",
            object="B was associated with A",
            attribution=attribution,
            relation_sign="neutral",
        )

        self.assertTrue(_is_symmetric_swap(source, candidate))

    def test_reviewed_relation_variants_share_one_canonical_frame(self):
        for relation in (
            "associated with",
            "was associated with",
            "associated",
            "association",
            "association with",
        ):
            with self.subTest(relation=relation):
                proposition = Proposition(
                    proposition_id="p5",
                    text="Processor load was associated with longer response times.",
                    subject="processor load",
                    relation=relation,
                    object="longer response times",
                    relation_sign="neutral",
                )
                self.assertEqual(_provider_frame_mismatches(proposition), [])

    def test_unreviewed_relation_label_remains_malformed(self):
        proposition = Proposition(
            proposition_id="p6",
            text="Processor load was associated with longer response times.",
            subject="processor load",
            relation="caused",
            object="longer response times",
            relation_sign="neutral",
        )

        self.assertIn("relation", _provider_frame_mismatches(proposition))

    def test_mapped_observed_test_scope_removal_requires_review(self):
        source = Proposition(
            proposition_id="s2",
            text="A was associated with B in the observed tests.",
            subject="A",
            relation="associated with",
            object="B",
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c2",
            text="A was associated with B.",
            subject="A",
            relation="associated with",
            object="B",
            relation_sign="neutral",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_mapped_observed_test_scope_broadening_requires_review(self):
        source = Proposition(
            proposition_id="s3",
            text="A was associated with B in the observed tests.",
            subject="A",
            relation="associated with",
            object="B in the observed tests",
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c3",
            text=(
                "A was associated with B in the observed tests and in field "
                "deployments."
            ),
            subject="A",
            relation="associated with",
            object="B in the observed tests and in field deployments",
            relation_sign="neutral",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_comma_coordinated_observed_scope_broadening_requires_review(self):
        source = Proposition(
            proposition_id="s4",
            text="A was associated with B in the observed tests.",
            subject="A",
            relation="associated with",
            object="B in the observed tests",
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c4",
            text=(
                "A was associated with B in the observed tests, as well as in "
                "field deployments."
            ),
            subject="A",
            relation="associated with",
            object=(
                "B in the observed tests, as well as in field deployments"
            ),
            relation_sign="neutral",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_but_also_observed_scope_broadening_requires_review(self):
        source = Proposition(
            proposition_id="s5",
            text="A was associated with B in the observed tests.",
            subject="A",
            relation="associated with",
            object="B in the observed tests",
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c5",
            text=(
                "A was associated with B in the observed tests, but also in field "
                "deployments."
            ),
            subject="A",
            relation="associated with",
            object="B in the observed tests, but also in field deployments",
            relation_sign="neutral",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_auxiliary_led_observed_scope_broadening_requires_review(self):
        source = Proposition(
            proposition_id="s6",
            text="A was associated with B in the observed tests.",
            subject="A",
            relation="associated with",
            object="B in the observed tests",
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c6",
            text=(
                "A was associated with B in the observed tests, and was also "
                "associated with B in field deployments."
            ),
            subject="A",
            relation="associated with",
            object=(
                "B in the observed tests, and was also associated with B in field deployments"
            ),
            relation_sign="neutral",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_semicolon_observed_scope_broadening_requires_review(self):
        source = Proposition(
            proposition_id="s7",
            text="A was associated with B in the observed tests.",
            subject="A",
            relation="associated with",
            object="B in the observed tests",
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c7",
            text="A was associated with B in the observed tests; also in field deployments.",
            subject="A",
            relation="associated with",
            object="B in the observed tests; also in field deployments",
            relation_sign="neutral",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_dependent_while_scope_broadening_requires_review(self):
        source = Proposition(
            proposition_id="s8",
            text="A was associated with B in the observed tests.",
            subject="A",
            relation="associated with",
            object="B in the observed tests",
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c8",
            text=(
                "A was associated with B in the observed tests, while being "
                "associated with B in field deployments."
            ),
            subject="A",
            relation="associated with",
            object=(
                "B in the observed tests, while being associated with B in field deployments"
            ),
            relation_sign="neutral",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_independent_extra_association_scope_broadening_requires_review(self):
        source = Proposition(
            proposition_id="s9",
            text="A was associated with B in the observed tests.",
            subject="A",
            relation="associated with",
            object="B in the observed tests",
            relation_sign="neutral",
        )
        candidate = Proposition(
            proposition_id="c9",
            text=(
                "A was associated with B in the observed tests, and it was also "
                "associated with B in field deployments."
            ),
            subject="A",
            relation="associated with",
            object=(
                "B in the observed tests, and it was also associated with B in field deployments"
            ),
            relation_sign="neutral",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_reviewed_scope_stops_at_explicit_reporting_clause_transition(self):
        source = Proposition(
            proposition_id="s10",
            text=(
                "A was associated with B in the observed tests, but they do not "
                "claim that A caused B."
            ),
        )
        candidate = Proposition(
            proposition_id="c10",
            text=(
                "A was associated with B in the observed tests, but they do not "
                "claim that it caused B."
            ),
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertNotIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )

    def test_outer_reporting_frame_validates_inner_relation_sign(self):
        attribution = Attribution(agent="Chen et al.", act="report")
        text = "Chen et al. report that A was positively associated with B."
        good = Proposition(
            proposition_id="p7",
            text=text,
            subject="Chen et al.",
            relation="report",
            object="A was positively associated with B",
            attribution=attribution,
            relation_sign="positive",
        )
        bad = Proposition(
            proposition_id="p8",
            text=text,
            subject="Chen et al.",
            relation="report",
            object="A was positively associated with B",
            attribution=attribution,
            relation_sign="negative",
        )

        self.assertEqual(_provider_frame_mismatches(good), [])
        self.assertIn("relation_sign", _provider_frame_mismatches(bad))


if __name__ == "__main__":
    unittest.main()
