"""Validate bidirectional proposition reports and convert them into core deltas."""
from __future__ import annotations

from collections import Counter
import re

from ..models import DeltaType, SemanticDelta, Severity
from ..providers.base import Proposition, PropositionReport


RELATION_RE = re.compile(
    r"^\s*(?P<subject>.+?)\s+"
    r"(?:is|are|was|were)\s+"
    r"(?P<relation>associated\s+with|correlated\s+with|linked\s+to|related\s+to)\s+"
    r"(?P<object>.+?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)


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
    )


def _malformed(
    explanation: str,
    *,
    severity: Severity = Severity.WARNING,
    source_span: str | None = None,
    candidate_span: str | None = None,
) -> SemanticDelta:
    return _delta(
        DeltaType.MALFORMED_PROVIDER_RESPONSE,
        explanation,
        source_span=source_span,
        candidate_span=candidate_span,
        severity=severity,
    )


def _normalise_role(text: str) -> str:
    value = " ".join(text.casefold().split()).strip(" .,:;!?")
    for article in ("the ", "a ", "an "):
        if value.startswith(article):
            return value[len(article):]
    return value


def _relation_parts(proposition: Proposition) -> tuple[str, str, str] | None:
    # Parse raw proposition text in the core. Provider-supplied directional fields
    # are metadata and cannot override this narrow deterministic check.
    match = RELATION_RE.match(proposition.text)
    if not match:
        return None
    return (
        _normalise_role(match.group("subject")),
        " ".join(match.group("relation").casefold().split()),
        _normalise_role(match.group("object")),
    )


def _provider_role_mismatch(proposition: Proposition) -> bool:
    parsed = _relation_parts(proposition)
    if parsed is None:
        return False
    if proposition.subject is not None and _normalise_role(proposition.subject) != parsed[0]:
        return True
    if proposition.relation is not None and " ".join(proposition.relation.casefold().split()) != parsed[1]:
        return True
    if proposition.object is not None and _normalise_role(proposition.object) != parsed[2]:
        return True
    return False


def _direction_delta(source: Proposition, candidate: Proposition) -> SemanticDelta | None:
    left = _relation_parts(source)
    right = _relation_parts(candidate)
    if left is None or right is None:
        return None
    if left[1] != right[1]:
        return None
    if left[0] == right[2] and left[2] == right[0] and left[0] != left[2]:
        return _delta(
            DeltaType.DIRECTION_REVERSAL,
            "Core relation parsing detected a subject/object reversal despite provider equivalence.",
            source_span=source.text,
            candidate_span=candidate.text,
        )
    return None


def deltas_from_proposition_report(
    report: PropositionReport,
    *,
    assurance: str = "standard",
) -> list[SemanticDelta]:
    """Validate provider coverage/IDs before translating semantic judgements.

    Provider booleans are evidence, not authority. The core validates proposition
    coverage, cross-references and a narrow class of relation reversals first.
    """
    deltas: list[SemanticDelta] = []
    strict = assurance in {"strict", "review"}

    source_ids = [item.proposition_id for item in report.source_propositions]
    candidate_ids = [item.proposition_id for item in report.candidate_propositions]
    source_props = {item.proposition_id: item for item in report.source_propositions}
    candidate_props = {item.proposition_id: item for item in report.candidate_propositions}

    duplicate_source_ids = [item for item, count in Counter(source_ids).items() if count > 1]
    duplicate_candidate_ids = [item for item, count in Counter(candidate_ids).items() if count > 1]
    if duplicate_source_ids:
        deltas.append(_malformed(
            f"Duplicate source proposition IDs: {', '.join(sorted(duplicate_source_ids))}."
        ))
    if duplicate_candidate_ids:
        deltas.append(_malformed(
            f"Duplicate candidate proposition IDs: {', '.join(sorted(duplicate_candidate_ids))}."
        ))

    for proposition in (*report.source_propositions, *report.candidate_propositions):
        if _provider_role_mismatch(proposition):
            deltas.append(_malformed(
                f"Provider directional fields disagree with the core parse for proposition {proposition.proposition_id}.",
                source_span=proposition.text if proposition.proposition_id in source_props else None,
                candidate_span=proposition.text if proposition.proposition_id in candidate_props else None,
            ))

    source_mapping_counts = Counter(item.source_id for item in report.source_to_candidate)
    candidate_mapping_counts = Counter(item.candidate_id for item in report.candidate_to_source)

    for source_id, count in source_mapping_counts.items():
        if count > 1:
            deltas.append(_malformed(
                f"Semantic verifier returned {count} mappings for source proposition {source_id}."
            ))
    for candidate_id, count in candidate_mapping_counts.items():
        if count > 1:
            deltas.append(_malformed(
                f"Semantic verifier returned {count} mappings for candidate proposition {candidate_id}."
            ))

    # Validate all mapping references before dereferencing them.
    for mapping in report.source_to_candidate:
        if mapping.source_id not in source_props:
            deltas.append(_malformed(
                f"source_to_candidate references unknown source proposition {mapping.source_id}."
            ))
        unknown_candidates = [item for item in mapping.candidate_ids if item not in candidate_props]
        if unknown_candidates:
            deltas.append(_malformed(
                "source_to_candidate references unknown candidate proposition(s): "
                + ", ".join(sorted(set(unknown_candidates))) + "."
            ))

    for mapping in report.candidate_to_source:
        if mapping.candidate_id not in candidate_props:
            deltas.append(_malformed(
                f"candidate_to_source references unknown candidate proposition {mapping.candidate_id}."
            ))
        unknown_sources = [item for item in mapping.source_ids if item not in source_props]
        if unknown_sources:
            deltas.append(_malformed(
                "candidate_to_source references unknown source proposition(s): "
                + ", ".join(sorted(set(unknown_sources))) + "."
            ))

    source_mappings = {
        item.source_id: item
        for item in report.source_to_candidate
        if item.source_id in source_props
    }
    candidate_mappings = {
        item.candidate_id: item
        for item in report.candidate_to_source
        if item.candidate_id in candidate_props
    }

    if not source_props and not candidate_props:
        deltas.append(_unresolved(
            "Bidirectional proposition report contains no verifiable propositions."
        ))
    elif not source_props or not candidate_props:
        deltas.append(_malformed(
            "Bidirectional proposition report is one-sided.",
            severity=Severity.BLOCKER if strict else Severity.WARNING,
        ))

    # Completeness: source propositions may not be silently omitted.
    for source_id, proposition in source_props.items():
        mapping = source_mappings.get(source_id)
        if mapping is None:
            deltas.append(_malformed(
                f"No candidate mapping was returned for source proposition {source_id}.",
                source_span=proposition.text,
                severity=Severity.BLOCKER if strict else Severity.WARNING,
            ))
            continue

        if mapping.preserved is True and not mapping.candidate_ids:
            deltas.append(_malformed(
                f"Source proposition {source_id} is marked preserved but has no candidate IDs.",
                source_span=proposition.text,
                severity=Severity.BLOCKER if strict else Severity.WARNING,
            ))

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
        if mapping.relational_direction_preserved is False:
            deltas.append(_delta(
                DeltaType.DIRECTION_REVERSAL,
                f"Relational direction is not preserved for source proposition {source_id}.",
                source_span=proposition.text,
                candidate_span=_candidate_text(mapping.candidate_ids, candidate_props),
            ))

        if len(mapping.candidate_ids) == 1 and mapping.candidate_ids[0] in candidate_props:
            direction_delta = _direction_delta(
                proposition,
                candidate_props[mapping.candidate_ids[0]],
            )
            if direction_delta is not None:
                deltas.append(direction_delta)

    # Licensing completeness: orphan candidates are unlicensed added claims.
    for candidate_id, proposition in candidate_props.items():
        mapping = candidate_mappings.get(candidate_id)
        if mapping is None:
            deltas.append(_delta(
                DeltaType.CLAIM_ADDED,
                f"Candidate proposition {candidate_id} has no source licensing mapping.",
                candidate_span=proposition.text,
            ))
            continue

        if mapping.licensed is True and mapping.new_claim is False and not mapping.source_ids:
            deltas.append(_malformed(
                f"Candidate proposition {candidate_id} is marked licensed but has no source IDs.",
                candidate_span=proposition.text,
                severity=Severity.BLOCKER if strict else Severity.WARNING,
            ))

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
    texts = [propositions[item].text for item in candidate_ids if item in propositions]
    return " | ".join(texts) or None


def _source_text(source_ids: tuple[str, ...], propositions: dict[str, Proposition]) -> str | None:
    texts = [propositions[item].text for item in source_ids if item in propositions]
    return " | ".join(texts) or None
