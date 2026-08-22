"""Fail-closed handling for untrusted read-only prose context."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .models import DeltaType, SemanticDelta, Severity

MAX_CONTEXT_CHARS = 12_000
_INSTRUCTION_LIKE_RE = re.compile(
    r"\b(?:ignore|disregard|override|follow|obey|system|developer|prompt|instruction|jailbreak)\b",
    re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?(?=\s+|$)", re.DOTALL)
_WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)


@dataclass(frozen=True)
class ContextSafety:
    accepted: bool
    signals: tuple[str, ...]
    before_sha256: str | None
    after_sha256: str | None
    before_chars: int
    after_chars: int

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "signals": list(self.signals),
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "before_chars": self.before_chars,
            "after_chars": self.after_chars,
            "untrusted": True,
        }

    def to_provider_dict(self, *, before: str | None, after: str | None) -> dict[str, object]:
        payload = self.to_dict()
        payload.update({"before": before, "after": after})
        return payload


def _digest(value: str | None) -> str | None:
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None


def inspect_context(before: str | None = None, after: str | None = None) -> ContextSafety:
    """Validate bounds and record untrusted context metadata without judging prose."""

    signals: list[str] = []
    for label, value in (("before", before), ("after", after)):
        if value is not None and not isinstance(value, str):
            raise TypeError(f"context_{label} must be a string or None")
        if value is not None and len(value) > MAX_CONTEXT_CHARS:
            signals.append(f"context_{label}_exceeds_character_budget")
        if value is not None and "\x00" in value:
            signals.append(f"context_{label}_contains_nul")
        if value and _INSTRUCTION_LIKE_RE.search(value):
            signals.append(f"context_{label}_contains_instruction_like_text")
    if (before and before.strip()) or (after and after.strip()):
        signals.append("context_is_untrusted_read_only_input")
    hard_failures = {
        signal
        for signal in signals
        if signal.endswith("_exceeds_character_budget") or signal.endswith("_contains_nul")
    }
    return ContextSafety(
        accepted=not hard_failures,
        signals=tuple(dict.fromkeys(signals)),
        before_sha256=_digest(before),
        after_sha256=_digest(after),
        before_chars=len(before or ""),
        after_chars=len(after or ""),
    )


def _normalise_sentence(value: str) -> str:
    return " ".join(_WORD_RE.findall(value.casefold()))


def _sentences(value: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for match in _SENTENCE_RE.finditer(value):
        surface = match.group(0).strip()
        normalised = _normalise_sentence(surface)
        if len(_WORD_RE.findall(surface)) >= 3 and normalised:
            result.append((surface, normalised))
    return result


def context_only_deltas(
    source: str,
    candidate: str,
    *,
    context_before: str | None = None,
    context_after: str | None = None,
) -> list[SemanticDelta]:
    """Flag a complete context-only sentence copied into a changed candidate.

    This is deliberately an exact, conservative guard. It does not attempt to
    prove that all context use is unsafe; it only blocks a high-confidence
    context-only proposition from receiving an automatic PASS.
    """

    if not candidate or source == candidate:
        return []
    source_sentences = {normalised for _, normalised in _sentences(source)}
    deltas: list[SemanticDelta] = []
    for label, value in (("before", context_before), ("after", context_after)):
        if not value:
            continue
        for surface, normalised in _sentences(value):
            if normalised in source_sentences:
                continue
            if normalised in _normalise_sentence(candidate):
                deltas.append(
                    SemanticDelta(
                        delta_type=DeltaType.CONTEXT_ONLY_CLAIM,
                        source_span=None,
                        candidate_span=surface,
                        severity=Severity.WARNING,
                        explanation=(
                            f"Candidate contains a complete sentence copied from untrusted "
                            f"context_{label}; context-only propositions are not licensed by source text."
                        ),
                        repairable=False,
                        confidence=1.0,
                    )
                )
    return deltas
