"""Deterministic semantic-anchor extraction for SWOS Prose.

This module intentionally favours conservative, inspectable signals over opaque
semantic scoring. Model-assisted proposition extraction is plugged in separately.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

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


def _anchor(kind: str, text: str, start: int, end: int, index: int) -> SemanticAnchor:
    return SemanticAnchor(
        anchor_id=f"{kind}-{index:03d}",
        kind=kind,
        text=text,
        start=start,
        end=end,
        normalized=" ".join(text.split()).casefold(),
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
