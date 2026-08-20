"""Convert bidirectional proposition reports into core semantic deltas."""
from __future__ import annotations

from collections import Counter

from ..models import DeltaType, SemanticDelta, Severity
from ..providers.base import Proposition, PropositionReport


def _delta(
    delta_type: DeltaType,
    explanation: str,
    *,
    source_span: str | None = None,
    candidate_span: str | None = None,
    severity: Severity = Severity.BLOCKER,
    confidence: float = 1.0,
) -> SemanticDelta:
    return SemanticDelta(
        delta_type=delta_type,
        source_span=source_span,
        candidate_span=candidate_span,
        severity=severity,
        explanation=explanation,
        repairable=False,
        confidence=confidence,
    )


def _unresolved(
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
        confidence=1.0,
    )


def deltas_from_proposition_report(report: PropositionReport) -> list[SemanticDelta]:
    """Translate provider proposition mappings into SWOS-owned semantic deltas.

    Providers describe proposition preservation/licensing. They do not decide the
    final verification status. Missing mappings and unresolved judgements fail
    conservatively to REVIEW; explicit preservation/licensing failures are
    blockers.
    """
    deltas: list[SemanticDelta] = []

    source_props = {item.proposition_id: item for item in report.source_propositions}
    candidate_props = {item.proposition_id: item for item in report.candidate_propositions}

    source_mapping_counts = Counter(item.source_id for item in report.source_to_candidate)
    candidate_mapping_counts = Counter(item.candidate_id for item in report.candidate_to_source)

    for source_id, count in source_mapping_counts.items():
        if count > 1:
            deltas.append(_unresolved(
                f"Semantic verifier returned {count} mappings for source proposition {source_id}.",
                source_span=source_props.get(source_id).text if source_id in source_props else source_id,
            ))

    for candidate_id, count in candidate_mapping_counts.items():
        if count > 1:
            deltas.append(_unresolved(
                f"Semantic verifier returned {count} mappings for candidate proposition {candidate_id}.",
                candidate_span=candidate_props.get(candidate_id).text if candidate_id in candidate_props else candidate_id,
            ))

    source_mappings = {item.source_id: item for item in report.source_to_candidate}
    candidate_mappings = {item.candidate_id: item for item in report.candidate_to_source}

    if not source_props or not candidate_props:
        deltas.append(_unresolved(
            "Bidirectional proposition report is empty or one-sided; equivalence cannot be established."
        ))

    for source_id, proposition in source_props.items():
        mapping = source_mappings.get(source_id)
        if mapping is None:
            deltas.append(_unresolved(
                f"No candidate mapping was returned for source proposition {source_id}.",
                source_span=proposition.text,
            ))
            continue

        if mapping.preserved is False:
            deltas.append(_delta(
                DeltaType.CLAIM_REMOVED,
                f"Source proposition {source_id} is not preserved in the candidate.",
                source_span=proposition.text,
                candidate_span=_candidate_text(mapping.candidate_ids, candidate_props),
            ))
        elif mapping.preserved is None:
            deltas.append(_unresolved(
                f"Preservation of source proposition {source_id} is unresolved.",
                source_span=proposition.text,
                candidate_span=_candidate_text(mapping.candidate_ids, candidate_props),
            ))

        if mapping.modality_preserved is False:
            deltas.append(_delta(
                DeltaType.EPISTEMIC_TYPE_CHANGED,
                f"Modality is not preserved for source proposition {source_id}.",
                source_span=proposition.text,
                candidate_span=_candidate_text(mapping.candidate_ids, candidate_props),
            ))

        if mapping.scope_preserved is False:
            deltas.append(_delta(
                DeltaType.UNRESOLVED_EQUIVALENCE,
                f"Scope is not preserved for source proposition {source_id}.",
                source_span=proposition.text,
                candidate_span=_candidate_text(mapping.candidate_ids, candidate_props),
            ))

        if mapping.attribution_preserved is False:
            deltas.append(_delta(
                DeltaType.ATTRIBUTION_CHANGED,
                f"Attribution is not preserved for source proposition {source_id}.",
                source_span=proposition.text,
                candidate_span=_candidate_text(mapping.candidate_ids, candidate_props),
            ))

        if mapping.causal_force_preserved is False:
            deltas.append(_delta(
                DeltaType.CAUSAL_STRENGTH_CHANGED,
                f"Causal/relational force is not preserved for source proposition {source_id}.",
                source_span=proposition.text,
                candidate_span=_candidate_text(mapping.candidate_ids, candidate_props),
            ))

    for candidate_id, proposition in candidate_props.items():
        mapping = candidate_mappings.get(candidate_id)
        if mapping is None:
            deltas.append(_unresolved(
                f"No source licensing mapping was returned for candidate proposition {candidate_id}.",
                candidate_span=proposition.text,
            ))
            continue

        if mapping.licensed is False or mapping.new_claim is True:
            deltas.append(_delta(
                DeltaType.CLAIM_ADDED,
                f"Candidate proposition {candidate_id} is not licensed by the source.",
                source_span=_source_text(mapping.source_ids, source_props),
                candidate_span=proposition.text,
            ))
        elif mapping.licensed is None or mapping.new_claim is None:
            deltas.append(_unresolved(
                f"Licensing of candidate proposition {candidate_id} is unresolved.",
                source_span=_source_text(mapping.source_ids, source_props),
                candidate_span=proposition.text,
            ))

    for item in report.unresolved:
        deltas.append(_unresolved(f"Semantic verifier unresolved item: {item}"))

    return deltas


def _candidate_text(candidate_ids: tuple[str, ...], propositions: dict[str, Proposition]) -> str | None:
    texts = [
        propositions[item].text
        for item in candidate_ids
        if item in propositions
    ]
    return " | ".join(texts) or None


def _source_text(source_ids: tuple[str, ...], propositions: dict[str, Proposition]) -> str | None:
    texts = [
        propositions[item].text
        for item in source_ids
        if item in propositions
    ]
    return " | ".join(texts) or None
