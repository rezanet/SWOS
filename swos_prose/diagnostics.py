"""Conservative pre-generation diagnostics for SWOS Prose polish mode.

Diagnostics answer one narrow question: is there enough *positive* deterministic
evidence to justify returning an already-good source unchanged without spending a
rewrite-provider call? They do not score style, prove grammatical correctness, or
establish semantic equivalence.

The fail-closed rule is asymmetric:
- only a fully reviewed whole-sentence exemplar plus no defect/uncertainty signal
  may produce ``NO_CHANGE_RECOMMENDED``;
- absence of a known defect is never sufficient by itself;
- anything outside the reviewed exemplar set proceeds to the normal rewriter and
  verifier pipeline.

The exemplar set is intentionally tiny. Expanding zero-cost abstention coverage is
a benchmark task, not a parser task: new exemplars must be reviewed and added from
empirical evidence rather than inferred through increasingly permissive regexes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
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
    ("was_performed_using", re.compile(r"\bwas\s+performed\s+using\b", re.IGNORECASE)),
    ("rather_unnecessarily", re.compile(r"\brather\s+unnecessarily\b", re.IGNORECASE)),
)

# Force-bearing language is not an editorial defect. It is simply a reason not
# to let this first deterministic diagnostics slice make a high-confidence
# abstention decision. The rewriter/verifier path has richer safeguards for it.
_FORCE_BEARING_RE = re.compile(
    r"\b(?:may|might|can|could|should|would|must|somewhat|slightly|marginally|"
    r"moderately|considerably|substantially|significantly|highly|strongly|partly|"
    r"partially|largely|mostly|nearly|almost|barely|hardly)\b",
    re.IGNORECASE,
)

# These are deliberately complete, reviewed source sentences. No slot, wildcard,
# case normalization, whitespace normalization, or unrestricted object span is
# accepted. The set exists to prove the abstention plumbing and zero-provider-cost
# contract without pretending that deterministic regexes can certify arbitrary
# English prose. Benchmark evidence may justify adding more literal exemplars.
_REVIEWED_ABSTENTION_EXEMPLARS = frozenset(
    {
        "The revised workflow reduced implementation errors and simplified later review.",
        "The revised process reduced review effort and improved consistency.",
        "The revised implementation reduced unnecessary repetition and improved readability.",
    }
)

# A few high-confidence agreement risks are cheap reasons to avoid abstention.
# False positives are safe: they merely spend the normal rewrite/verifier path.
_QUANTIFIER_AGREEMENT_RISK_RE = re.compile(
    r"\b(?:several|many|few|multiple|numerous)\s+([A-Za-z][A-Za-z'-]*)\b",
    re.IGNORECASE,
)
_IRREGULAR_PLURALS = {"children", "people", "men", "women", "data", "criteria", "phenomena"}

# High-confidence abstention envelope. Falling outside it does not mean the prose
# is defective; it means deterministic diagnostics are not confident enough to
# skip generation.
_MIN_ABSTAIN_WORDS = 8
_MAX_ABSTAIN_WORDS = 32
_MAX_SENTENCE_WORDS = 32


@dataclass(frozen=True)
class PolishDiagnostics:
    recommendation: str
    high_confidence: bool
    signals: tuple[str, ...]
    positive_evidence: tuple[str, ...]
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
            "positive_evidence": list(self.positive_evidence),
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "max_sentence_words": self.max_sentence_words,
        }


def _sentence_word_counts(text: str) -> list[int]:
    """Return conservative sentence-sized word counts without full parsing."""
    chunks: list[str] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(text):
        chunks.append(text[start : match.end()])
        start = match.end()
    if text[start:].strip():
        chunks.append(text[start:])
    if not chunks:
        chunks = [text]
    counts = [len(_WORD_RE.findall(chunk)) for chunk in chunks if chunk.strip()]
    return counts or [0]


def _quantifier_agreement_risk(source: str) -> bool:
    for match in _QUANTIFIER_AGREEMENT_RISK_RE.finditer(source):
        noun = match.group(1).casefold()
        if not noun.endswith("s") and noun not in _IRREGULAR_PLURALS:
            return True
    return False


def _positive_structure_evidence(
    source: str,
    *,
    word_count: int,
    sentence_count: int,
) -> tuple[str, ...]:
    """Recognise only an explicitly reviewed literal source exemplar."""
    if not (_MIN_ABSTAIN_WORDS <= word_count <= _MAX_ABSTAIN_WORDS):
        return ()
    if sentence_count != 1:
        return ()
    if source not in _REVIEWED_ABSTENTION_EXEMPLARS:
        return ()
    return ("reviewed_whole_sentence_exemplar",)


def diagnose_polish(
    source: str,
    *,
    context_before: str | None = None,
    context_after: str | None = None,
) -> PolishDiagnostics:
    """Return a conservative pre-generation recommendation for polish mode.

    ``NO_CHANGE_RECOMMENDED`` requires an exact literal reviewed whole-sentence
    exemplar *and* the absence of reviewed material-defect/uncertainty signals.
    Anything else is ``PROCEED_TO_REWRITE``. This function never labels prose as
    bad.

    Until diagnostics are context-aware, supplying neighbouring context disables
    early abstention so local-flow problems cannot be hidden by an isolated
    sentence that looks acceptable on its own.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if context_before is not None and not isinstance(context_before, str):
        raise TypeError("context_before must be a string or None")
    if context_after is not None and not isinstance(context_after, str):
        raise TypeError("context_after must be a string or None")

    words = _WORD_RE.findall(source)
    sentence_word_counts = _sentence_word_counts(source)
    word_count = len(words)
    sentence_count = len(sentence_word_counts)
    max_sentence_words = max(sentence_word_counts, default=0)
    signals: list[str] = []

    if word_count < _MIN_ABSTAIN_WORDS:
        signals.append("insufficient_length_for_high_confidence_abstention")
    if word_count > _MAX_ABSTAIN_WORDS:
        signals.append("paragraph_length_requires_richer_editorial_path")
    if sentence_count != 1:
        signals.append("multi_sentence_structure_requires_richer_editorial_path")
    if max_sentence_words > _MAX_SENTENCE_WORDS:
        signals.append("long_sentence_may_benefit_from_restructuring")
    if re.search(r"[,;:]", source):
        signals.append("punctuated_clause_structure_requires_richer_editorial_path")
    if _REPEATED_WORD_RE.search(source):
        signals.append("immediate_word_repetition")
    if _FORCE_BEARING_RE.search(source):
        signals.append("force_bearing_language_requires_richer_editorial_path")
    if _quantifier_agreement_risk(source):
        signals.append("possible_quantifier_number_agreement_problem")
    if (context_before and context_before.strip()) or (context_after and context_after.strip()):
        signals.append("neighboring_context_requires_context_aware_diagnostics")

    for name, pattern in _WORDINESS_PATTERNS:
        if pattern.search(source):
            signals.append(f"avoidable_expansion:{name}")

    positive_evidence = _positive_structure_evidence(
        source,
        word_count=word_count,
        sentence_count=sentence_count,
    )
    if not positive_evidence:
        signals.append("no_reviewed_abstention_exemplar")

    if signals:
        return PolishDiagnostics(
            recommendation="PROCEED_TO_REWRITE",
            high_confidence=False,
            signals=tuple(dict.fromkeys(signals)),
            positive_evidence=positive_evidence,
            word_count=word_count,
            sentence_count=sentence_count,
            max_sentence_words=max_sentence_words,
        )

    return PolishDiagnostics(
        recommendation="NO_CHANGE_RECOMMENDED",
        high_confidence=True,
        signals=(),
        positive_evidence=positive_evidence,
        word_count=word_count,
        sentence_count=sentence_count,
        max_sentence_words=max_sentence_words,
    )
