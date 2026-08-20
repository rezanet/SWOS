from __future__ import annotations

import unittest

from swos_prose.models import VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.verify.causal_scope import causal_polarity_signals


class _MustNotRunVerifier:
    def __init__(self) -> None:
        self.calls = 0

    def verify(self, **kwargs):
        self.calls += 1
        raise AssertionError("deterministic causal blocker should have short-circuited")


class CausalScopeAttackTests(unittest.TestCase):
    def test_unrelated_source_causal_claim_does_not_mask_strengthening(self):
        source = "A was associated with B. C caused D."
        candidate = "A caused B. C caused D."
        verifier = _MustNotRunVerifier()

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

    def test_unpunctuated_coordinate_causal_clause_ends_denial_scope(self):
        candidate = "Evidence does not show benefit and exposure caused harm."

        signals = causal_polarity_signals(candidate)

        self.assertEqual(signals.denied, ())
        self.assertEqual(signals.affirmative, ("caused",))

    def test_unpunctuated_coordinate_strengthening_remains_hard_blocked(self):
        source = (
            "Evidence does not show benefit and exposure was associated with fatigue."
        )
        candidate = (
            "Evidence does not show benefit and exposure caused fatigue."
        )
        verifier = _MustNotRunVerifier()

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
