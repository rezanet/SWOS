"""Conservative pre-generation diagnostics for SWOS Prose polish mode.

Diagnostics answer one narrow question: is there enough evidence of an editorial
problem to justify spending a rewrite-provider call? They do not score style,
prove quality, or establish semantic equivalence. The only automatic action is a
high-confidence abstention when a compact passage exposes none of the reviewed
material-defect signals below. Everything else proceeds to the normal rewriter
and verifier pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


_WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
_REPEATED_WORD_RE = re.compile(r"\b([A-Za-z][A-Za-z'’-]*)\s+\1\b", re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r"[.!?](?:\s+|$)")

# Reviewed examples of avoidable filler/expansion. These are evidence that a
# rewrite may be useful, not forbidden phrases or style targets.
_WORDINESS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("in_order_to", re.compile(r"\bin\s+order\s+to\b", re.IGNORECASE)),
    ("due_to_the_fact_that", re.compile(r"\bdue\s+to\s+the\s+fact\s+that\b", re.IGNORECASE)),
    ("important_to_note", re.compile(r"\bit\s+is\s+important\s+to\s+note\s+that\b", re.IGNORECASE)),
    ("should_be_noted", re.compile(r"\bit\s+should\s+be\s+noted\s+that\b", re.IGNORECASE)),
    ("at_this_point_in_time", re.compile(r"\bat\s+this\s+point\s+in\s+time\b", re.IGNORECASE)),
    ("in_the_event_that", re.compile(r"\bin\s+the\s+event\s+that\b", re.IGNORECASE)),
    ("for_the_purpose_of", re.compile(r"\bfor\s+the\s+purpose\s+of\b", re.IGNORECASE)),
    ("with_regard_to", re.compile(r"\bwith\s+regard\s+to\b", re.IGNORECASE)),
    ("has_the_ability_to", re.compile(r"\bhas\s+the\s+ability\s+to\b", re.IGNORECASE)),
)

# High-confidence abstention envelope. Falling outside it does not mean the prose
# is defective; it means the deterministic diagnostics are not confident enough
# to skip generation.
_MIN_ABSTAIN_WORDS = 8
_MAX_ABSTAIN_WORDS = 48
_MAX_SENTENCE_WORDS = 34
_MAX_SENTENCE_COUNT = 3
_MAX_HEAVY_PUNCTUATION = 5  # commas + semicolons + colons


@dataclass(frozen=True)
class PolishDiagnostics:
    recommendation: str
    high_confidence: bool
    signals: tuple[str, ...]
    word_count: int
    sentence_count: int
    max_sentence_words: int

    @property
    def no_change_recommended(self) -> bool:
        return self.recommendation == "NO_CHANGE_RECOMMENDED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation": self.recommendation,
            "high_confidence": self.high_confidence,
            "signals": list(self.signals),
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "max_sentence_words": self.max_sentence_words,
        }


def _sentence_word_counts(text: str) -> list[int]:
    """Return conservative sentence-sized word counts without full parsing."""
    chunks: list[str] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(text):
        chunks.append(text[start:match.end()])
        start = match.end()
    if text[start:].strip():
        chunks.append(text[start:])
    if not chunks:
        chunks = [text]
    counts = [len(_WORD_RE.findall(chunk)) for chunk in chunks if chunk.strip()]
    return counts or [0]


def diagnose_polish(source: str) -> PolishDiagnostics:
    """Return a conservative pre-generation recommendation for polish mode.

    ``NO_CHANGE_RECOMMENDED`` is issued only inside a narrow compact-prose
    envelope and only when no reviewed material-defect signal is present.
    ``PROCEED_TO_REWRITE`` is intentionally broader: it includes both detected
    defects and cases where deterministic diagnostics are simply uncertain.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")

    words = _WORD_RE.findall(source)
    sentence_word_counts = _sentence_word_counts(source)
    word_count = len(words)
    sentence_count = len(sentence_word_counts)
    max_sentence_words = max(sentence_word_counts, default=0)
    signals: list[str] = []

    if word_count < _MIN_ABSTAIN_WORDS:
        signals.append("insufficient_length_for_high_confidence_abstention")
    if word_count > _MAX_ABSTAIN_WORDS:
        signals.append("paragraph_length_may_benefit_from_editing")
    if sentence_count > _MAX_SENTENCE_COUNT:
        signals.append("multi_sentence_structure_requires_editorial_review")
    if max_sentence_words > _MAX_SENTENCE_WORDS:
        signals.append("long_sentence_may_benefit_from_restructuring")
    if len(re.findall(r"[,;:]", source)) > _MAX_HEAVY_PUNCTUATION:
        signals.append("dense_punctuation_may_indicate_overloaded_construction")
    if _REPEATED_WORD_RE.search(source):
        signals.append("immediate_word_repetition")

    for name, pattern in _WORDINESS_PATTERNS:
        if pattern.search(source):
            signals.append(f"avoidable_expansion:{name}")

    if signals:
        return PolishDiagnostics(
            recommendation="PROCEED_TO_REWRITE",
            high_confidence=False,
            signals=tuple(signals),
            word_count=word_count,
            sentence_count=sentence_count,
            max_sentence_words=max_sentence_words,
        )

    return PolishDiagnostics(
        recommendation="NO_CHANGE_RECOMMENDED",
        high_confidence=True,
        signals=("compact_prose_without_reviewed_material_defect_signal",),
        word_count=word_count,
        sentence_count=sentence_count,
        max_sentence_words=max_sentence_words,
    )
