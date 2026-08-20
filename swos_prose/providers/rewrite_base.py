"""Provider contract for SWOS Prose rewrite generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class RewriteCandidate:
    """One provider-generated prose candidate plus execution metadata."""

    candidate_text: str
    notes: list[str] = field(default_factory=list)
    token_usage: dict[str, int] | None = None
    cost_estimate: float | None = None


class RewriteProvider(Protocol):
    """Host/model adapter contract for prose generation.

    Rewrite providers propose wording. They never decide whether their own
    candidate is semantically safe; the independent SWOS Prose verification
    pipeline owns that decision.
    """

    def rewrite(
        self,
        *,
        source: str,
        mode: str,
        protected_anchors: list[dict[str, Any]],
        rewrite_plan: dict[str, Any],
        context_before: str | None = None,
        context_after: str | None = None,
    ) -> RewriteCandidate:
        ...
