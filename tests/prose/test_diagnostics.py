from __future__ import annotations

import unittest

from swos_prose.diagnostics import diagnose_polish
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.providers.rewrite_mock import StaticRewriteProvider
from swos_prose.rewrite import polish_text

STRONG_SOURCE = "The revised workflow reduced implementation errors and simplified later review."


class PolishDiagnosticsTests(unittest.TestCase):
    def test_reviewed_exemplar_abstains_before_any_provider_call(self):
        source = STRONG_SOURCE
        rewriter = StaticRewriteProvider("This provider must not be called.")
        verifier = StaticSemanticVerifierProvider(
            {
                "equivalent": True,
                "independent_of_rewriter": True,
                "deltas": [],
                "notes": [],
            }
        )

        result = polish_text(
            source=source,
            rewrite_provider=rewriter,
            verifier_provider=verifier,
            assurance="strict",
        )

        self.assertTrue(result.generation_skipped_by_diagnostics)
        self.assertTrue(result.safe_for_automatic_use)
        self.assertEqual(result.final_text, source)
        self.assertEqual(result.candidate, source)
        self.assertFalse(result.used_source_fallback)
        self.assertIsNone(result.verification)
        self.assertIsNone(result.rewrite_token_usage)
        self.assertEqual(rewriter.calls, 0)
        self.assertEqual(verifier.calls, 0)
        self.assertEqual(
            result.diagnostics_before.recommendation,
            "NO_CHANGE_RECOMMENDED",
        )
        self.assertEqual(
            result.diagnostics_before.positive_evidence,
            ("reviewed_whole_sentence_exemplar",),
        )
        self.assertEqual(result.diagnostics_before.signals, ())

    def test_exemplar_case_change_is_not_an_exact_match(self):
        diagnostics = diagnose_polish(STRONG_SOURCE.upper())

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertEqual(diagnostics.positive_evidence, ())
        self.assertIn("no_reviewed_abstention_exemplar", diagnostics.signals)

    def test_exemplar_whitespace_change_is_not_an_exact_match(self):
        diagnostics = diagnose_polish(f" {STRONG_SOURCE}")

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertEqual(diagnostics.positive_evidence, ())
        self.assertIn("no_reviewed_abstention_exemplar", diagnostics.signals)

    def test_absence_of_known_defect_is_not_positive_evidence(self):
        diagnostics = diagnose_polish(
            "The report contain several error that make it difficult to read."
        )

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertFalse(diagnostics.high_confidence)
        self.assertEqual(diagnostics.positive_evidence, ())
        self.assertIn("no_reviewed_abstention_exemplar", diagnostics.signals)

    def test_malformed_and_tail_cannot_hide_behind_valid_predicate(self):
        diagnostics = diagnose_polish(
            "The revised report reduced several errors and contain obvious mistakes."
        )

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertEqual(diagnostics.positive_evidence, ())
        self.assertIn("no_reviewed_abstention_exemplar", diagnostics.signals)

    def test_malformed_but_tail_cannot_be_consumed_as_object_text(self):
        diagnostics = diagnose_polish(
            "The revised report reduced several errors but contain obvious mistakes."
        )

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertEqual(diagnostics.positive_evidence, ())
        self.assertIn("no_reviewed_abstention_exemplar", diagnostics.signals)

    def test_unreviewed_well_formed_sentence_still_proceeds(self):
        diagnostics = diagnose_polish(
            "The revised workflow reduced processing time and improved later review."
        )

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertEqual(diagnostics.positive_evidence, ())
        self.assertIn("no_reviewed_abstention_exemplar", diagnostics.signals)

    def test_quantifier_number_risk_prevents_abstention(self):
        diagnostics = diagnose_polish(
            "The revised report reduced several error during the final review."
        )

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertIn(
            "possible_quantifier_number_agreement_problem",
            diagnostics.signals,
        )

    def test_reviewed_wordiness_signal_proceeds_to_rewriter(self):
        source = (
            "It is important to note that the team changed the implementation in "
            "order to reduce unnecessary repetition."
        )
        diagnostics = diagnose_polish(source)

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertFalse(diagnostics.high_confidence)
        self.assertIn("avoidable_expansion:important_to_note", diagnostics.signals)
        self.assertIn("avoidable_expansion:in_order_to", diagnostics.signals)

    def test_force_bearing_language_does_not_trigger_deterministic_abstention(self):
        diagnostics = diagnose_polish(
            "The available evidence may remain somewhat uncertain after this analysis."
        )

        self.assertEqual(diagnostics.recommendation, "PROCEED_TO_REWRITE")
        self.assertIn(
            "force_bearing_language_requires_richer_editorial_path",
            diagnostics.signals,
        )

    def test_neighboring_context_prevents_early_abstention(self):
        source = STRONG_SOURCE
        rewriter = StaticRewriteProvider(source)

        result = polish_text(
            source=source,
            rewrite_provider=rewriter,
            verifier_provider=None,
            context_before="The previous sentence makes the same point.",
        )

        self.assertEqual(rewriter.calls, 1)
        self.assertFalse(result.generation_skipped_by_diagnostics)
        self.assertEqual(
            result.diagnostics_before.recommendation,
            "PROCEED_TO_REWRITE",
        )
        self.assertIn(
            "neighboring_context_requires_context_aware_diagnostics",
            result.diagnostics_before.signals,
        )

    def test_diagnostics_can_be_explicitly_disabled_for_calibration(self):
        source = STRONG_SOURCE
        rewriter = StaticRewriteProvider(source)

        result = polish_text(
            source=source,
            rewrite_provider=rewriter,
            verifier_provider=None,
            run_diagnostics=False,
        )

        self.assertEqual(rewriter.calls, 1)
        self.assertIsNone(result.diagnostics_before)
        self.assertFalse(result.generation_skipped_by_diagnostics)
        self.assertEqual(result.final_text, source)


if __name__ == "__main__":
    unittest.main()
