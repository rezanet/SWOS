from __future__ import annotations

import unittest

from swos_prose.models import DeltaType, SemanticDelta, Severity, VerificationResult, VerificationStatus
from swos_prose.providers.rewrite_base import RewriteCandidate
from swos_prose.providers.rewrite_mock import StaticRewriteProvider
from swos_prose.repair import MAX_REPAIR_ATTEMPTS, annotate_local_repairability, locate_span, render_repair_prompt, repair_loop
from swos_prose.rewrite import polish_text


class ScriptedRepairProvider:
    def __init__(self, *responses: str):
        self.responses = list(responses)
        self.calls = 0
        self.requests: list[dict] = []

    def repair(self, **kwargs) -> RewriteCandidate:
        self.requests.append(kwargs)
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return RewriteCandidate(candidate_text=self.responses[index], token_usage={"input_tokens": 20, "output_tokens": 5, "total_tokens": 25})


class BoundedRepairIntegrationTests(unittest.TestCase):
    CASES = (
        ("modality", "The findings may indicate a relationship between the variables.", "The findings indicate a relationship between the variables."),
        ("quantifier", "Some participants reported fatigue after the session.", "Participants reported fatigue after the session."),
        ("attribution", "Ahmed argues that the evidence is limited.", "Ahmed states that the evidence is limited."),
        ("negation", "The intervention did not change the measured outcome.", "The intervention changed the measured outcome."),
        ("causal_force", "Exposure was associated with the observed outcome.", "Exposure caused the observed outcome."),
    )

    def test_five_reviewed_local_drift_families_repair_and_reverify(self):
        for name, source, defective in self.CASES:
            with self.subTest(name=name):
                repairer = ScriptedRepairProvider(source)
                result = polish_text(
                    source=source, rewrite_provider=StaticRewriteProvider(defective), verifier_provider=None,
                    assurance="strict", run_diagnostics=False, repair_provider=repairer,
                )
                self.assertEqual(result.verification_status, VerificationStatus.PASS.value)
                self.assertEqual(result.final_text, source)
                self.assertEqual(result.candidate, source)
                self.assertFalse(result.used_source_fallback)
                self.assertTrue(result.safe_for_automatic_use)
                self.assertTrue(result.repair_success)
                self.assertIsNone(result.repair_failure_reason)
                self.assertEqual(len(result.repair_attempts), 1)
                self.assertTrue(result.repair_attempts[0].success)
                self.assertEqual(repairer.calls, 1)

    def test_number_change_is_never_sent_to_repair(self):
        source = "The response rate was 18.7%."
        repairer = ScriptedRepairProvider(source)
        result = polish_text(
            source=source, rewrite_provider=StaticRewriteProvider("The response rate was 19%."),
            verifier_provider=None, assurance="strict", run_diagnostics=False, repair_provider=repairer,
        )
        self.assertEqual(result.verification_status, VerificationStatus.REJECT.value)
        self.assertEqual(result.final_text, source)
        self.assertTrue(result.used_source_fallback)
        self.assertFalse(result.repair_success)
        self.assertEqual(result.repair_attempts, [])
        self.assertEqual(repairer.calls, 0)

    def test_runtime_rejects_repair_that_changes_text_outside_authorised_span(self):
        source = "The findings may indicate a relationship."
        repairer = ScriptedRepairProvider("Clearly, the findings may indicate a relationship.")
        result = polish_text(
            source=source, rewrite_provider=StaticRewriteProvider("The findings indicate a relationship."),
            verifier_provider=None, run_diagnostics=False, repair_provider=repairer,
        )
        self.assertEqual(result.final_text, source)
        self.assertTrue(result.used_source_fallback)
        self.assertFalse(result.repair_success)
        self.assertEqual(len(result.repair_attempts), 1)
        self.assertIn("outside the authorised local span", result.repair_failure_reason)

    def test_out_of_scope_provider_delta_cannot_self_declare_repairable(self):
        source = "The analysis was performed using a t-test."
        candidate = "The analysis used a t-test."
        delta = SemanticDelta(
            delta_type=DeltaType.CONDITION_CHANGED, source_span=source, candidate_span=candidate,
            severity=Severity.BLOCKER, explanation="Synthetic structural condition delta.", repairable=True,
        )
        annotated = annotate_local_repairability(source, candidate, [delta])
        self.assertEqual(len(annotated), 1)
        self.assertFalse(annotated[0].repairable)
        self.assertEqual(annotated[0].severity, Severity.BLOCKER)


class RepairLocalisationTests(unittest.TestCase):
    def test_attribution_machine_signal_localises_only_speech_act(self):
        source = "Ahmed argues that the evidence is limited."
        candidate = "Ahmed states that the evidence is limited."
        delta = SemanticDelta(
            delta_type=DeltaType.ATTRIBUTION_CHANGED, source_span="ahmed::argues", candidate_span="ahmed::states",
            severity=Severity.WARNING, explanation="Attribution language differs.",
        )
        span = locate_span(source, candidate, delta)
        self.assertIsNotNone(span)
        self.assertEqual(source[span.source_start:span.source_end], "argues")
        self.assertEqual(candidate[span.candidate_start:span.candidate_end], "states")
        self.assertGreaterEqual(span.confidence, 0.95)

    def test_causal_relation_localises_bound_preposition_with_head(self):
        source = "Exposure was associated with the observed outcome."
        candidate = "Exposure caused the observed outcome."
        delta = SemanticDelta(
            delta_type=DeltaType.CAUSAL_STRENGTH_CHANGED, source_span="associated with", candidate_span="caused",
            severity=Severity.BLOCKER, explanation="Causal force strengthened.",
        )
        span = locate_span(source, candidate, delta)
        self.assertIsNotNone(span)
        self.assertEqual(source[span.source_start:span.source_end], "was associated with")
        self.assertEqual(candidate[span.candidate_start:span.candidate_end], "caused")

    def test_repeated_marker_is_ambiguous_and_not_guessed(self):
        source = "The first result may vary and the second may vary."
        candidate = "The first result varies and the second varies."
        delta = SemanticDelta(
            delta_type=DeltaType.MODALITY_STRENGTHENED, source_span="may", candidate_span=None,
            severity=Severity.BLOCKER, explanation="Weak modality removed.",
        )
        self.assertIsNone(locate_span(source, candidate, delta))

    def test_prompt_forbids_surrounding_rewrite_and_additions(self):
        delta = SemanticDelta(
            delta_type=DeltaType.MODALITY_STRENGTHENED, source_span="may indicate", candidate_span="indicate",
            severity=Severity.BLOCKER, explanation="Weak modality was removed.", repairable=True,
        )
        prompt = render_repair_prompt(
            source="The findings may indicate a relationship.", candidate="The findings indicate a relationship.",
            delta=delta, offending_span="indicate",
        ).casefold()
        self.assertIn("replace only the offending span", prompt)
        self.assertIn("do not change anything else", prompt)
        self.assertIn("do not add new claims", prompt)
        self.assertIn("return only the full corrected candidate text", prompt)


class RepairAttemptCapTests(unittest.TestCase):
    def _repair_result(self, candidate: str, marker: str | None) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.REPAIR, source="The findings may indicate a relationship.", candidate=candidate,
            semantic_deltas=[SemanticDelta(
                delta_type=DeltaType.MODALITY_STRENGTHENED, source_span="may", candidate_span=marker,
                severity=Severity.BLOCKER, explanation="Modal force remains different.", repairable=True, confidence=1.0,
            )],
        )

    def test_repair_loop_stops_after_exactly_two_failed_attempts(self):
        source = "The findings may indicate a relationship."
        candidate = "The findings indicate a relationship."
        repairer = ScriptedRepairProvider(
            "The findings might indicate a relationship.",
            "The findings could indicate a relationship.",
            source,
        )
        def verify(text: str) -> VerificationResult:
            if "might" in text:
                return self._repair_result(text, "might")
            if "could" in text:
                return self._repair_result(text, "could")
            raise AssertionError(f"Unexpected candidate: {text}")
        execution = repair_loop(
            source=source, candidate=candidate, initial_verification=self._repair_result(candidate, None),
            repair_provider=repairer, verify_candidate=verify,
        )
        self.assertFalse(execution.success)
        self.assertEqual(len(execution.attempts), MAX_REPAIR_ATTEMPTS)
        self.assertEqual(repairer.calls, MAX_REPAIR_ATTEMPTS)
        self.assertEqual(execution.failure_reason, "Maximum repair attempts exceeded.")

    def test_attempt_limit_cannot_be_raised_above_governed_cap(self):
        source = "The findings may indicate a relationship."
        candidate = "The findings indicate a relationship."
        with self.assertRaises(ValueError):
            repair_loop(
                source=source, candidate=candidate, initial_verification=self._repair_result(candidate, None),
                repair_provider=ScriptedRepairProvider(source), verify_candidate=lambda _: self._repair_result(candidate, None),
                max_attempts=MAX_REPAIR_ATTEMPTS + 1,
            )


if __name__ == "__main__":
    unittest.main()
