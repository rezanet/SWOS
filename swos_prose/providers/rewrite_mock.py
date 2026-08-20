"""Static rewrite provider for SWOS Prose tests."""
from __future__ import annotations

from typing import Any

from .rewrite_base import RewriteCandidate


class StaticRewriteProvider:
    """Return one scripted rewrite candidate without calling a model."""

    def __init__(self, candidate_text: str):
        if not isinstance(candidate_text, str):
            raise TypeError("candidate_text must be a string")
        self.candidate_text = candidate_text
        self.calls = 0
        self.last_request: dict[str, Any] | None = None

    def rewrite(self, **kwargs: Any) -> RewriteCandidate:
        self.calls += 1
        self.last_request = dict(kwargs)
        return RewriteCandidate(candidate_text=self.candidate_text)
