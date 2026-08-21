from __future__ import annotations

import unittest

from swos_prose.models import DeltaType
from swos_prose.providers.base import Proposition
from swos_prose.verify.propositions import _frame_consistency_deltas


class ReviewedContextSentenceForceTests(unittest.TestCase):
    def _proposition(self, proposition_id: str, text: str) -> Proposition:
        return Proposition(
            proposition_id=proposition_id,
            text=text,
            subject="A",
            relation="associated with",
            object="B in the observed tests",
            relation_sign="neutral",
        )

    def test_question_or_exclamation_cannot_normalize_to_assertion(self):
        source = self._proposition(
            "s1",
            "A was associated with B in the observed tests.",
        )

        for terminal in ("?", "!"):
            with self.subTest(terminal=terminal):
                candidate = self._proposition(
                    "c1",
                    f"A was associated with B in the observed tests{terminal}",
                )
                deltas = _frame_consistency_deltas(source, candidate)
                self.assertIn(
                    DeltaType.UNRESOLVED_EQUIVALENCE,
                    [delta.delta_type for delta in deltas],
                )

    def test_single_full_stop_and_no_terminal_punctuation_are_equivalent_surface(self):
        source = self._proposition(
            "s2",
            "A was associated with B in the observed tests.",
        )
        candidate = self._proposition(
            "c2",
            "A was associated with B in the observed tests",
        )

        deltas = _frame_consistency_deltas(source, candidate)
        self.assertNotIn(
            DeltaType.UNRESOLVED_EQUIVALENCE,
            [delta.delta_type for delta in deltas],
        )


if __name__ == "__main__":
    unittest.main()
