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
from .causal_scope import causal_polarity_signals, reviewed_association_markers
from .negation_equivalence import (
    REVIEWED_LEXICAL_NEGATION_TERMS,
    REVIEWED_NEGATION_EQUIVALENCES,
)


_ANAPHORIC_ALL_RE = re.compile(
    r"\ball\s+of\s+(?:which|whom|them|these|those)\b", re.I
)
_REVIEWED_LEXICAL_NEGATION_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(item) for item in REVIEWED_LEXICAL_NEGATION_TERMS) + r")\b",
    re.I,
)
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’.-][A-Za-z0-9]+)*")


def _phrase_re(phrase: str) -> re.Pattern[str]:
    return re.compile(
        r"\b" + r"\s+".join(re.escape(part) for part in phrase.split()) + r"\b",
        re.I,
    )


_REVIEWED_NEGATION_PATTERNS = tuple(
    (explicit, lexical, _phrase_re(explicit), _phrase_re(lexical))
    for explicit, lexical in REVIEWED_NEGATION_EQUIVALENCES
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


def _local_contexts(text: str, pattern: re.Pattern[str]) -> Counter[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Return narrow two-token context keys around reviewed negation forms."""
    contexts: Counter[tuple[tuple[str, ...], tuple[str, ...]]] = Counter()
    for match in pattern.finditer(text):
        before = tuple(item.casefold() for item in _WORD_RE.findall(text[:match.start()])[-2:])
        after = tuple(item.casefold() for item in _WORD_RE.findall(text[match.end():])[:2])
        contexts[(before, after)] += 1
    return contexts


def _reviewed_negation_context_signature(text: str) -> tuple:
    """Canonicalize reviewed explicit/lexical forms only within local context.

    The same reviewed pair is trusted as a polarity-preserving substitution only
    when it occupies the same narrow lexical neighbourhood. This prevents a
    reviewed negative from being moved to another clause or wrapped in another
    negation and then treated as equivalent merely because both sides contain a
    negative-looking token.
    """
    signature = []
    for explicit, lexical, explicit_re, lexical_re in _REVIEWED_NEGATION_PATTERNS:
        contexts = _local_contexts(text, explicit_re)
        contexts.update(_local_contexts(text, lexical_re))
        signature.append((explicit, lexical, tuple(sorted(contexts.items()))))
    return tuple(signature)


def _reviewed_negation_occurrences(text: str) -> int:
    return sum(
        sum(_local_contexts(text, explicit_re).values())
        + sum(_local_contexts(text, lexical_re).values())
        for _, _, explicit_re, lexical_re in _REVIEWED_NEGATION_PATTERNS
    )


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

    left_reviewed = _reviewed_lexical_negations(source)
    right_reviewed = _reviewed_lexical_negations(candidate)
    reviewed_forms_present = bool(
        _reviewed_negation_occurrences(source) or _reviewed_negation_occurrences(candidate)
    )
    base_negation_mismatch = bool(left.negations) != bool(right.negations)

    if reviewed_forms_present:
        # A reviewed lexical form contributes one polarity signal. Exact
        # explicit<->lexical substitution may explain the base Boolean mismatch,
        # but only if negation count/parity remains balanced and the reviewed form
        # stays in the same narrow lexical context.
        left_adjusted_count = len(left.negations) + len(left_reviewed)
        right_adjusted_count = len(right.negations) + len(right_reviewed)
        reviewed_contexts_match = (
            _reviewed_negation_context_signature(source)
            == _reviewed_negation_context_signature(candidate)
        )
        if base_negation_mismatch:
            negation_mismatch = not (
                left_adjusted_count == right_adjusted_count
                and reviewed_contexts_match
            )
        else:
            negation_mismatch = left_adjusted_count != right_adjusted_count
    else:
        negation_mismatch = base_negation_mismatch

    if negation_mismatch:
        left_spans = (*left.negations, *left_reviewed)
        right_spans = (*right.negations, *right_reviewed)
        deltas.append(_delta(
            DeltaType.NEGATION_CHANGED,
            "Negation polarity, count, or reviewed lexical-negation context differs between source and candidate.",
            source_span=", ".join(left_spans) or None,
            candidate_span=", ".join(right_spans) or None,
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

    # Causal words inside a reviewed denied claim/evidence scope are not treated
    # as affirmative causal assertions. The denied proposition still matters: if
    # its causal wording changes, retain a REVIEW-level signal for the semantic
    # verifier rather than declaring the content irrelevant.
    left_causal = causal_polarity_signals(source)
    right_causal = causal_polarity_signals(candidate)
    left_associations = (*left.association_markers, *reviewed_association_markers(source))
    right_associations = (*right.association_markers, *reviewed_association_markers(candidate))

    # Compare occurrence counts rather than asking whether the source contains
    # *any* affirmative causal marker. Otherwise an unrelated source-side causal
    # claim can mask association -> causation strengthening in another clause.
    lost_association = len(right_associations) < len(left_associations)
    introduced_affirmative_causality = (
        len(right_causal.affirmative) > len(left_causal.affirmative)
    )

    if left_associations and lost_association and introduced_affirmative_causality:
        deltas.append(_delta(
            DeltaType.CAUSAL_STRENGTH_CHANGED,
            "Candidate replaces at least one associative relation with additional affirmative causal language.",
            source_span=", ".join(left_associations),
            candidate_span=", ".join(right_causal.affirmative),
        ))
    elif not left_causal.affirmative and right_causal.affirmative:
        deltas.append(_delta(
            DeltaType.CAUSAL_STRENGTH_CHANGED,
            "Candidate introduces affirmative causal language absent from the source.",
            source_span=None,
            candidate_span=", ".join(right_causal.affirmative),
            severity=Severity.WARNING,
            confidence=0.9,
        ))

    if Counter(left_causal.denied) != Counter(right_causal.denied):
        deltas.append(_delta(
            DeltaType.CAUSAL_STRENGTH_CHANGED,
            "Causal wording inside a denied claim/evidence scope differs and requires semantic review.",
            source_span=", ".join(left_causal.denied) or None,
            candidate_span=", ".join(right_causal.denied) or None,
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
