from __future__ import annotations

import unittest

from swos_prose.diagnostics import diagnose_polish
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.providers.rewrite_mock import StaticRewriteProvider
from swos_prose.rewrite import polish_text


class PolishDiagnosticsTests(unittest.TestCase):
    def test_compact_strong_prose_abstains_before_any_provider_call(self):
        source = (
            "Clear requirements reduce implementation errors and make later review "
            "easier for everyone involved."
        )
        rewriter = StaticRewriteProvider("This provider must not be called.")
        verifier = StaticSemanticVerifierProvider({
            "equivalent": True,
            "independent_of_rewriter": True,
            "deltas": [],
            "notes": [],
        })

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

    def test_diagnostics_can_be_explicitly_disabled_for_calibration(self):
        source = (
            "Clear requirements reduce implementation errors and make later review "
            "easier for everyone involved."
        )
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
