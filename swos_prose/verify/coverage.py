"""Coverage and granularity checks for semantic-verifier proposition reports.

This module deliberately treats provider classifications as evidence, not as an
unquestioned verdict. It checks whether mapped propositions preserve their
claim category and epistemic status, while remaining compatible with older
provider fixtures that do not yet populate Slice 4 fields.
"""
from __future__ import annotations

from ..models import DeltaType, SemanticDelta, Severity
from ..providers.base import Proposition, PropositionReport


UNKNOWN = {None, "", "unknown"}


def _normalise(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.casefold().split()).strip()


def _known(value: str | None) -> bool:
    return _normalise(value) not in UNKNOWN


def _delta(
    delta_type: DeltaType,
    explanation: str,
    *,
    source_span: str | None = None,
    candidate_span: str | None = None,
    severity: Severity = Severity.BLOCKER,
) -> SemanticDelta:
    return SemanticDelta(
        delta_type=delta_type,
        source_span=source_span,
        candidate_span=candidate_span,
        severity=severity,
        explanation=explanation,
        repairable=False,
        confidence=1.0,
    )


def _review(
    explanation: str,
    *,
    source_span: str | None = None,
    candidate_span: str | None = None,
) -> SemanticDelta:
    return _delta(
        DeltaType.UNRESOLVED_EQUIVALENCE,
        explanation,
        source_span=source_span,
        candidate_span=candidate_span,
        severity=Severity.WARNING,
    )


def _classification_pair_deltas(
    source: Proposition,
    candidate: Proposition,
) -> list[SemanticDelta]:
    deltas: list[SemanticDelta] = []

    source_claim = _normalise(source.claim_type)
    candidate_claim = _normalise(candidate.claim_type)
    if source_claim is not None or candidate_claim is not None:
        if not _known(source_claim) or not _known(candidate_claim):
            if source_claim != candidate_claim:
                deltas.append(_review(
                    "Mapped propositions do not both have a resolved claim_type classification.",
                    source_span=source.text,
                    candidate_span=candidate.text,
                ))
        elif source_claim != candidate_claim:
            deltas.append(_review(
                f"Claim type changed from {source_claim!r} to {candidate_claim!r}; semantic review is required.",
                source_span=source.text,
                candidate_span=candidate.text,
            ))

    source_epi = _normalise(source.epistemic_type)
    candidate_epi = _normalise(candidate.epistemic_type)
    if source_epi is not None or candidate_epi is not None:
        if not _known(source_epi) or not _known(candidate_epi):
            if source_epi != candidate_epi:
                deltas.append(_review(
                    "Mapped propositions do not both have a resolved epistemic_type classification.",
                    source_span=source.text,
                    candidate_span=candidate.text,
                ))
        elif source_epi != candidate_epi:
            deltas.append(_delta(
                DeltaType.EPISTEMIC_TYPE_CHANGED,
                f"Epistemic type changed from {source_epi!r} to {candidate_epi!r}.",
                source_span=source.text,
                candidate_span=candidate.text,
            ))

    return deltas


def coverage_deltas(
    report: PropositionReport,
    *,
    assurance: str = "standard",
) -> list[SemanticDelta]:
    """Check claim/epistemic classifications across the report's mapping graph.

    The mapping contract is many-to-many. A source proposition split into
    several candidate propositions is safe only when each mapped fragment keeps
    compatible classification. If heterogeneous source classifications are
    merged into a single scalar-classified candidate, strict assurance routes
    the case to REVIEW rather than pretending the scalar label captures the
    composite semantics.
    """
    deltas: list[SemanticDelta] = []
    seen: set[tuple[str, str, str]] = set()
    strict = assurance in {"strict", "review"}

    source_props = {item.proposition_id: item for item in report.source_propositions}
    candidate_props = {item.proposition_id: item for item in report.candidate_propositions}

    for mapping in report.source_to_candidate:
        source = source_props.get(mapping.source_id)
        if source is None:
            continue
        for candidate_id in mapping.candidate_ids:
            candidate = candidate_props.get(candidate_id)
            if candidate is None:
                continue
            for delta in _classification_pair_deltas(source, candidate):
                key = (delta.delta_type.value, source.proposition_id, candidate.proposition_id)
                if key not in seen:
                    seen.add(key)
                    deltas.append(delta)

    if strict:
        for mapping in report.candidate_to_source:
            candidate = candidate_props.get(mapping.candidate_id)
            if candidate is None or len(mapping.source_ids) < 2:
                continue
            sources = [source_props[item] for item in mapping.source_ids if item in source_props]
            claim_types = {
                _normalise(item.claim_type)
                for item in sources
                if _known(item.claim_type)
            }
            epistemic_types = {
                _normalise(item.epistemic_type)
                for item in sources
                if _known(item.epistemic_type)
            }
            if len(claim_types) > 1:
                deltas.append(_review(
                    "A candidate proposition merges source propositions with heterogeneous claim types; scalar classification is insufficient to prove preservation.",
                    source_span=" | ".join(item.text for item in sources),
                    candidate_span=candidate.text,
                ))
            if len(epistemic_types) > 1:
                deltas.append(_review(
                    "A candidate proposition merges source propositions with heterogeneous epistemic types; scalar classification is insufficient to prove preservation.",
                    source_span=" | ".join(item.text for item in sources),
                    candidate_span=candidate.text,
                ))

    return deltas
