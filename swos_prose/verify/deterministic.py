"""Deterministic and heuristic semantic-delta checks."""
from __future__ import annotations

from collections import Counter
import re

from ..anchors import (
    anchor_multiset,
    canonical_number_multisets,
    extract_anchors,
    extract_risk_signals,
)
from ..models import DeltaType, SemanticDelta, Severity
from .negation_equivalence import REVIEWED_LEXICAL_NEGATION_TERMS


_ANAPHORIC_ALL_RE = re.compile(
    r"\ball\s+of\s+(?:which|whom|them|these|those)\b", re.I
)
_REVIEWED_LEXICAL_NEGATION_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(item) for item in REVIEWED_LEXICAL_NEGATION_TERMS) + r")\b",
    re.I,
)


def _delta(
    delta_type: DeltaType,
    explanation: str,
    *,
    source_span: str | None = None,
    candidate_span: str | None = None,
    severity: Severity = Severity.BLOCKER,
    repairable: bool = False,
    confidence: float = 1.0,
) -> SemanticDelta:
    return SemanticDelta(
        delta_type=delta_type,
        source_span=source_span,
        candidate_span=candidate_span,
        severity=severity,
        explanation=explanation,
        repairable=repairable,
        confidence=confidence,
    )


def _counter_text(counter: Counter[str]) -> str:
    return ", ".join(f"{item} x{count}" if count > 1 else item for item, count in sorted(counter.items()))


def _reviewed_lexical_negations(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).casefold() for match in _REVIEWED_LEXICAL_NEGATION_RE.finditer(text))


def _compare_hard_anchors(source: str, candidate: str) -> tuple[list, list, list[SemanticDelta]]:
    source_anchors = extract_anchors(source)
    candidate_anchors = extract_anchors(candidate)
    deltas: list[SemanticDelta] = []

    number_left, number_right = canonical_number_multisets(
        source,
        candidate,
        source_anchors,
        candidate_anchors,
    )
    if number_left != number_right:
        deltas.append(_delta(
            DeltaType.NUMBER_CHANGED,
            "Protected number anchors differ between source and candidate after conservative numeric canonicalization.",
            source_span=_counter_text(number_left) or None,
            candidate_span=_counter_text(number_right) or None,
            severity=Severity.BLOCKER,
            repairable=False,
        ))

    mapping = {
        "citation": DeltaType.CITATION_REMOVED,
        "quotation": DeltaType.QUOTATION_CHANGED,
    }
    for kind, delta_type in mapping.items():
        left = anchor_multiset(source_anchors, kind)
        right = anchor_multiset(candidate_anchors, kind)
        if left != right:
            deltas.append(_delta(
                delta_type,
                f"Protected {kind} anchors differ between source and candidate.",
                source_span=_counter_text(left) or None,
                candidate_span=_counter_text(right) or None,
                severity=Severity.BLOCKER,
                repairable=False,
            ))

    return source_anchors, candidate_anchors, deltas


def deterministic_deltas(source: str, candidate: str) -> tuple[list, list, list[SemanticDelta]]:
    """Return deterministic/high-risk deltas without claiming full equivalence.

    Hard anchors (numbers, citations, quotations) are literal blockers after
    conservative canonicalization. Linguistic risk checks are conservative
    signals. Clear semantic strengthening is a blocker; potentially safe
    paraphrases that require interpretation become REVIEW-level warnings.
    """
    source_anchors, candidate_anchors, deltas = _compare_hard_anchors(source, candidate)
    left = extract_risk_signals(source)
    right = extract_risk_signals(candidate)

    # Reviewed lexical negatives count as polarity signals, but do not establish
    # sentence-level equivalence. This prevents a known explicit-to-lexical
    # paraphrase from being hard-rejected while still requiring semantic
    # verification for changed prose.
    left_negations = (*left.negations, *_reviewed_lexical_negations(source))
    right_negations = (*right.negations, *_reviewed_lexical_negations(candidate))
    if bool(left_negations) != bool(right_negations):
        deltas.append(_delta(
            DeltaType.NEGATION_CHANGED,
            "Negation is present on only one side of the rewrite.",
            source_span=", ".join(left_negations) or None,
            candidate_span=", ".join(right_negations) or None,
        ))

    if left.weak_modals and not right.weak_modals:
        deltas.append(_delta(
            DeltaType.MODALITY_STRENGTHENED,
            "Source contains an explicit weak modal that the candidate removes.",
            source_span=", ".join(left.weak_modals),
            candidate_span=", ".join(right.weak_modals) or None,
        ))

    if left.suggestive_markers and right.strong_epistemic_markers:
        deltas.append(_delta(
            DeltaType.MODALITY_STRENGTHENED,
            "Candidate replaces suggestive evidence language with a stronger epistemic verb.",
            source_span=", ".join(left.suggestive_markers),
            candidate_span=", ".join(right.strong_epistemic_markers),
        ))

    if left.association_markers and right.causal_markers:
        deltas.append(_delta(
            DeltaType.CAUSAL_STRENGTH_CHANGED,
            "Candidate changes associative language into causal language.",
            source_span=", ".join(left.association_markers),
            candidate_span=", ".join(right.causal_markers),
        ))
    elif not left.causal_markers and right.causal_markers:
        deltas.append(_delta(
            DeltaType.CAUSAL_STRENGTH_CHANGED,
            "Candidate introduces explicit causal language absent from the source.",
            source_span=None,
            candidate_span=", ".join(right.causal_markers),
            severity=Severity.WARNING,
            confidence=0.9,
        ))

    if Counter(left.quantifiers) != Counter(right.quantifiers):
        strong = {"most", "all", "always"}
        introduced_strong = (
            strong.intersection(right.quantifiers)
            - strong.intersection(left.quantifiers)
        )

        # A newly introduced strong quantifier is normally blocking. One narrow
        # exception is anaphoric "all of which/whom/them/these/those": its scope
        # can be licensed by an already-defined referent rather than strengthening
        # the proposition. Deterministic parsing cannot prove that equivalence,
        # so route it to semantic verification instead of rejecting it.
        anaphoric_all_requires_verification = (
            introduced_strong == {"all"}
            and "all" not in left.quantifiers
            and bool(_ANAPHORIC_ALL_RE.search(candidate))
        )

        if introduced_strong and not anaphoric_all_requires_verification:
            severity = Severity.BLOCKER
            explanation = (
                "Candidate introduces stronger quantifier language and "
                "deterministic scope comparison indicates semantic strengthening."
            )
        else:
            severity = Severity.WARNING
            explanation = (
                "Quantifier language differs and requires proposition-level "
                "verification of scope and binding."
            )

        deltas.append(_delta(
            DeltaType.QUANTIFIER_CHANGED,
            explanation,
            source_span=", ".join(left.quantifiers) or None,
            candidate_span=", ".join(right.quantifiers) or None,
            severity=severity,
            confidence=0.9,
        ))

    if left.scope_markers and Counter(left.scope_markers) != Counter(right.scope_markers):
        deltas.append(_delta(
            DeltaType.SCOPE_BROADENED,
            "A source scope/condition marker is not preserved literally; semantic review is required.",
            source_span=", ".join(left.scope_markers),
            candidate_span=", ".join(right.scope_markers) or None,
            severity=Severity.WARNING,
            confidence=0.8,
        ))

    if left.attributions and Counter(left.attributions) != Counter(right.attributions):
        deltas.append(_delta(
            DeltaType.ATTRIBUTION_CHANGED,
            "Attribution language differs between source and candidate.",
            source_span=", ".join(left.attributions),
            candidate_span=", ".join(right.attributions) or None,
            severity=Severity.BLOCKER if not right.attributions else Severity.WARNING,
            confidence=0.9,
        ))

    return source_anchors, candidate_anchors, deltas
