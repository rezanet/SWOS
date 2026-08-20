"""Narrow causal-scope helpers for deterministic semantic-risk checks.

These helpers do not decide semantic equivalence. They distinguish causal words
used as affirmative claims from causal words embedded inside a reviewed denied
claim/evidence scope, so the deterministic layer does not mistake a preserved
phrase such as ``do not claim ... caused`` for an affirmative causal assertion.
Ambiguous or changed denied content remains verifier work.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from ..anchors import CAUSAL_RE


# Evidence-led nominal association paraphrase observed in live dogfood. Keep this
# narrow rather than treating arbitrary uses of the noun "association" as a
# relational assertion.
_REVIEWED_ASSOCIATION_RE = re.compile(r"\bassociation\s+between\b", re.I)

# Reviewed outer predicates whose explicit do/does/did-not form denies assertion
# or evidential support for the embedded causal proposition. This does not make
# the embedded proposition semantically irrelevant; it only means its causal
# token is not an affirmative causal claim by the writer.
_DENIED_CAUSAL_HEAD_RE = re.compile(
    r"\b(?:do|does|did)\s+not\s+"
    r"(?:claim|assert|conclude|demonstrate|show|establish|prove)\b",
    re.I,
)

# Keep scope local to the clause. A contrasting/coordinating clause after a comma
# is not silently absorbed into the denial.
_DENIED_SCOPE_END_RE = re.compile(
    r"[.;!?]|,\s+(?:but|and|while|although|yet)\b",
    re.I,
)

# A narrow unpunctuated coordinate-clause boundary. Requiring an explicit subject
# token before the causal predicate avoids cutting ``does not claim X caused Y
# and produced Z`` at the predicate coordination. This boundary is used only
# when the denied predicate is not followed by an explicit ``that`` complement;
# with ``that``, coordination may legitimately remain inside the embedded claim.
_CAUSAL_PREDICATE_PATTERN = (
    r"(?:causes?|caused|leads?\s+to|led\s+to|results?\s+in|resulted\s+in|"
    r"produces?|produced|drives?|drove|determines?|determined)"
)
_UNPUNCTUATED_COORDINATE_CAUSAL_RE = re.compile(
    r"\b(?:and|but|yet)\s+"
    r"(?:[A-Za-z][A-Za-z0-9'’.-]*\s+){1,4}"
    rf"(?={_CAUSAL_PREDICATE_PATTERN}\b)",
    re.I,
)
_THAT_COMPLEMENT_RE = re.compile(r"\s+that\b", re.I)


@dataclass(frozen=True)
class CausalPolaritySignals:
    affirmative: tuple[str, ...]
    denied: tuple[str, ...]


def reviewed_association_markers(text: str) -> tuple[str, ...]:
    return tuple(
        " ".join(match.group(0).split()).casefold()
        for match in _REVIEWED_ASSOCIATION_RE.finditer(text)
    )


def _scope_end(text: str, scope_start: int) -> int:
    candidates: list[int] = []

    punctuated = _DENIED_SCOPE_END_RE.search(text, scope_start)
    if punctuated is not None:
        candidates.append(punctuated.start())

    # Without an explicit ``that`` complement, a new unpunctuated coordinate
    # clause with its own subject + causal predicate is outside the denial.
    if _THAT_COMPLEMENT_RE.match(text[scope_start:]) is None:
        coordinate = _UNPUNCTUATED_COORDINATE_CAUSAL_RE.search(text, scope_start)
        if coordinate is not None:
            candidates.append(coordinate.start())

    return min(candidates) if candidates else len(text)


def _denied_causal_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for head in _DENIED_CAUSAL_HEAD_RE.finditer(text):
        scope_start = head.end()
        spans.append((scope_start, _scope_end(text, scope_start)))
    return spans


def causal_polarity_signals(text: str) -> CausalPolaritySignals:
    """Partition causal markers into affirmative vs reviewed denied scope."""
    denied_spans = _denied_causal_spans(text)
    affirmative: list[str] = []
    denied: list[str] = []

    for match in CAUSAL_RE.finditer(text):
        normalized = " ".join(match.group(0).split()).casefold()
        in_denied_scope = any(
            start <= match.start() < end
            for start, end in denied_spans
        )
        if in_denied_scope:
            denied.append(normalized)
        else:
            affirmative.append(normalized)

    return CausalPolaritySignals(
        affirmative=tuple(affirmative),
        denied=tuple(denied),
    )
