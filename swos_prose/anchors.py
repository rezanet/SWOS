"""Deterministic semantic-anchor extraction for SWOS Prose.

This module intentionally favours conservative, inspectable signals over opaque
semantic scoring. Model-assisted proposition extraction is plugged in separately.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .models import SemanticAnchor


NUMBER_RE = re.compile(r"(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![\w.])")
CITATION_RES = (
    re.compile(r"\[(?:\d+(?:\s*[-,]\s*\d+)*)\]"),
    re.compile(r"\([A-Z][A-Za-z'’.-]+(?:\s+et al\.)?,?\s+(?:19|20)\d{2}[a-z]?\)"),
)
QUOTE_RES = (
    re.compile(r'“([^”]+)”'),
    re.compile(r'"([^"\n]+)"'),
)
NEGATION_RE = re.compile(r"\b(?:no|not|never|neither|nor|without)\b|\bfailed\s+to\b", re.I)
WEAK_MODAL_RE = re.compile(r"\b(?:may|might|could|possibly|perhaps)\b", re.I)
SUGGESTIVE_RE = re.compile(r"\b(?:suggests?|suggested|indicates?|indicated|appears?|seems?)\b", re.I)
STRONG_EPISTEMIC_RE = re.compile(r"\b(?:demonstrates?|demonstrated|proves?|proved|establishes?|established|confirms?|confirmed)\b", re.I)
ASSOCIATION_RE = re.compile(r"\b(?:associated\s+with|correlated\s+with|linked\s+to|related\s+to)\b", re.I)
CAUSAL_RE = re.compile(r"\b(?:causes?|caused|leads?\s+to|led\s+to|results?\s+in|resulted\s+in|produces?|produced|drives?|drove|determines?|determined)\b", re.I)
QUANTIFIER_RE = re.compile(r"\b(?:none|few|some|many|most|all|sometimes|often|always)\b", re.I)
SCOPE_RES = (
    re.compile(r"\bin\s+(?:this|the)\s+(?:sample|cohort|study|dataset|population)\b", re.I),
    re.compile(r"\bamong\s+[^,.;:]+", re.I),
    re.compile(r"\bonly\b", re.I),
    re.compile(r"\bexcept\b", re.I),
    re.compile(r"\bafter\s+adjust(?:ment|ing)\s+for\s+[^,.;:]+", re.I),
)
ATTRIBUTION_RE = re.compile(
    r"\b([A-Z][A-Za-z'’.-]+(?:\s+et\s+al\.)?)\s+"
    r"(argues?|claims?|reports?|states?|suggests?|finds?|found|observes?|proposes?)\b"
)

_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
)
_TENS = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety"}
_SCALES = ((1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand"))
_NUMBER_WORDS = set(_ONES) | set(_TENS.values()) | {"hundred", "thousand", "million", "billion", "and", "minus"}


@dataclass(frozen=True)
class RiskSignals:
    negations: tuple[str, ...]
    weak_modals: tuple[str, ...]
    suggestive_markers: tuple[str, ...]
    strong_epistemic_markers: tuple[str, ...]
    association_markers: tuple[str, ...]
    causal_markers: tuple[str, ...]
    quantifiers: tuple[str, ...]
    scope_markers: tuple[str, ...]
    attributions: tuple[str, ...]


def _overlaps(span: tuple[int, int], excluded: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in excluded)


def canonical_numeric_token(text: str) -> str:
    """Canonicalize literal numeric anchors without changing their value."""
    value = text.strip().replace(",", "")
    percent = value.endswith("%")
    if percent:
        value = value[:-1]
    try:
        number = Decimal(value)
    except InvalidOperation:
        return " ".join(text.split()).casefold()
    normalized = format(number.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized in {"-0", ""}:
        normalized = "0"
    return normalized + ("%" if percent else "")


def _anchor(kind: str, text: str, start: int, end: int, index: int) -> SemanticAnchor:
    normalized = canonical_numeric_token(text) if kind == "number" else " ".join(text.split()).casefold()
    return SemanticAnchor(
        anchor_id=f"{kind}-{index:03d}",
        kind=kind,
        text=text,
        start=start,
        end=end,
        normalized=normalized,
    )


def extract_anchors(text: str) -> list[SemanticAnchor]:
    anchors: list[SemanticAnchor] = []
    protected_spans: list[tuple[int, int]] = []

    for regex in QUOTE_RES:
        for match in regex.finditer(text):
            anchors.append(_anchor("quotation", match.group(0), match.start(), match.end(), len(anchors) + 1))
            protected_spans.append((match.start(), match.end()))

    for regex in CITATION_RES:
        for match in regex.finditer(text):
            if not _overlaps((match.start(), match.end()), protected_spans):
                anchors.append(_anchor("citation", match.group(0), match.start(), match.end(), len(anchors) + 1))
                protected_spans.append((match.start(), match.end()))

    for match in NUMBER_RE.finditer(text):
        if not _overlaps((match.start(), match.end()), protected_spans):
            anchors.append(_anchor("number", match.group(0), match.start(), match.end(), len(anchors) + 1))

    return sorted(anchors, key=lambda item: (item.start, item.end, item.kind))


def anchor_multiset(anchors: list[SemanticAnchor], kind: str) -> Counter[str]:
    return Counter(anchor.normalized for anchor in anchors if anchor.kind == kind)


def _integer_to_words(value: int, *, british_and: bool = False) -> str:
    if value < 0:
        return "minus " + _integer_to_words(-value, british_and=british_and)
    if value < 20:
        return _ONES[value]
    if value < 100:
        tens = (value // 10) * 10
        remainder = value % 10
        return _TENS[tens] if remainder == 0 else f"{_TENS[tens]} {_ONES[remainder]}"
    if value < 1000:
        hundreds = value // 100
        remainder = value % 100
        if remainder == 0:
            return f"{_ONES[hundreds]} hundred"
        joiner = " and " if british_and else " "
        return f"{_ONES[hundreds]} hundred{joiner}{_integer_to_words(remainder, british_and=british_and)}"
    for scale, label in _SCALES:
        if value >= scale:
            leading = value // scale
            remainder = value % scale
            head = f"{_integer_to_words(leading, british_and=british_and)} {label}"
            if remainder == 0:
                return head
            joiner = " and " if british_and and remainder < 100 else " "
            return f"{head}{joiner}{_integer_to_words(remainder, british_and=british_and)}"
    raise ValueError("Integer outside supported range.")


def _word_number_occurrences(text: str, value: str) -> int:
    """Count complete conservative English word forms for a peer literal integer.

    Matching is deliberately enabled only for integer values >= 100. A generated
    form must occupy a complete number-word phrase, so ``two hundred`` does not
    match inside ``two hundred and one`` or ``one thousand two hundred``.
    """
    if value.endswith("%") or not re.fullmatch(r"-?\d+", value):
        return 0
    integer = int(value)
    if abs(integer) < 100 or abs(integer) > 999_999_999_999:
        return 0

    tokens = re.findall(r"[a-z]+", text.casefold().replace("-", " "))
    forms = {
        tuple(_integer_to_words(integer, british_and=False).split()),
        tuple(_integer_to_words(integer, british_and=True).split()),
    }
    best = 0
    for form_tokens in forms:
        width = len(form_tokens)
        count = 0
        for index in range(0, len(tokens) - width + 1):
            if tuple(tokens[index:index + width]) != form_tokens:
                continue
            before = tokens[index - 1] if index > 0 else None
            after_index = index + width
            after = tokens[after_index] if after_index < len(tokens) else None
            if before in _NUMBER_WORDS or after in _NUMBER_WORDS:
                continue
            count += 1
        best = max(best, count)
    return best


def canonical_number_multisets(
    source_text: str,
    candidate_text: str,
    source_anchors: list[SemanticAnchor],
    candidate_anchors: list[SemanticAnchor],
) -> tuple[Counter[str], Counter[str]]:
    """Compare literal numeric anchors plus conservative word-form equivalents."""
    left = anchor_multiset(source_anchors, "number")
    right = anchor_multiset(candidate_anchors, "number")

    for value, count in list(left.items()):
        missing = count - right[value]
        if missing > 0:
            right[value] += min(missing, _word_number_occurrences(candidate_text, value))

    for value, count in list(right.items()):
        missing = count - left[value]
        if missing > 0:
            left[value] += min(missing, _word_number_occurrences(source_text, value))

    return left, right


def _matches(regex: re.Pattern[str], text: str) -> tuple[str, ...]:
    return tuple(" ".join(match.group(0).split()).casefold() for match in regex.finditer(text))


def extract_risk_signals(text: str) -> RiskSignals:
    scope: list[str] = []
    for regex in SCOPE_RES:
        scope.extend(_matches(regex, text))

    attributions = tuple(
        f"{match.group(1).casefold()}::{match.group(2).casefold()}"
        for match in ATTRIBUTION_RE.finditer(text)
    )

    return RiskSignals(
        negations=_matches(NEGATION_RE, text),
        weak_modals=_matches(WEAK_MODAL_RE, text),
        suggestive_markers=_matches(SUGGESTIVE_RE, text),
        strong_epistemic_markers=_matches(STRONG_EPISTEMIC_RE, text),
        association_markers=_matches(ASSOCIATION_RE, text),
        causal_markers=_matches(CAUSAL_RE, text),
        quantifiers=_matches(QUANTIFIER_RE, text),
        scope_markers=tuple(scope),
        attributions=attributions,
    )
