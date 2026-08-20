"""Provider contracts for model-assisted semantic verification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..models import SemanticAnchor, SemanticDelta


@dataclass
class ProviderAssessment:
    equivalent: bool | None
    deltas: list[SemanticDelta] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    independent_of_rewriter: bool | None = None
    token_usage: dict[str, int] | None = None
    cost_estimate: float | None = None


class SemanticVerifierProvider(Protocol):
    """Host/model adapter contract.

    Providers analyse semantic equivalence; the SWOS Prose core still owns the
    final PASS/REPAIR/REVIEW/REJECT decision.
    """

    def verify(
        self,
        *,
        source: str,
        candidate: str,
        source_anchors: list[SemanticAnchor],
        candidate_anchors: list[SemanticAnchor],
        assurance: str,
        native_swos_context: dict | None,
    ) -> ProviderAssessment:
        ...
