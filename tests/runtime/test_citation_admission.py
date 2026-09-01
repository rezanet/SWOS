"""Core-owned citation admission boundary tests."""

from __future__ import annotations

import unittest

from swos_runtime.citation_classifier import (
    LABELS,
    CitationPair,
    CitationSupportDecision,
    DeterministicCitationChecks,
    admission_eligibility,
)


class CitationAdmissionTests(unittest.TestCase):
    def _decision(
        self, label: str = "directly_supports", status: str = "classified"
    ) -> CitationSupportDecision:
        probabilities = {item: 0.0 for item in LABELS}
        probabilities[label] = 0.95
        return CitationSupportDecision(
            pair_id="p",
            status=status,
            support_level=label if status == "classified" else None,
            probabilities=probabilities,
            confidence=0.95,
            selected_threshold=0.9,
        )

    def test_only_direct_nonabstained_after_all_prechecks_is_eligible(self) -> None:
        pair = CitationPair(pair_id="p", claim="claim", passage="passage")
        checks = DeterministicCitationChecks(
            source_exists=True,
            metadata_verified=True,
            rights_allowed=True,
            quote_contained=True,
            provenance_valid=True,
        )
        self.assertTrue(admission_eligibility(pair, checks, self._decision()).eligible)
        for label in ("partially_supports", "context_only", "contradicts", "not_supported"):
            self.assertFalse(admission_eligibility(pair, checks, self._decision(label)).eligible)
        self.assertFalse(
            admission_eligibility(pair, checks, self._decision(status="abstained")).eligible
        )


if __name__ == "__main__":
    unittest.main()
