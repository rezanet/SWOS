"""Validate bidirectional proposition reports and convert them into core deltas."""
from __future__ import annotations

from collections import Counter
import re

from ..models import DeltaType, SemanticDelta, Severity
from ..providers.base import Attribution, Proposition, PropositionReport


SYMMETRIC_RELATIONS = {
    "associated with",
    "correlated with",
    "linked to",
    "related to",
}

RELATION_RE = re.compile(
    r"^\s*(?P<subject>.+?)\s+"
    r"(?:is|are|was|were)\s+"
    r"(?:(?P<sign>positively|negatively)\s+)?"
    r"(?P<relation>associated\s+with|correlated\s+with|linked\s+to|related\s+to)\s+"
    r"(?P<object>.+?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)

TEMPORAL_RE = re.compile(
    r"^\s*(?P<subject>.+?)\s+"
    r"(?P<relation>preceded|followed)\s+"
    r"(?P<object>.+?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)

ATTRIBUTION_RE = re.compile(
    r"^\s*(?P<agent>[A-Z][A-Za-z'’.-]+(?:\s+et\s+al\.)?)\s+"
    r"(?P<act>argues?|claims?|reports?|states?|suggests?|finds?|found|observes?|proposes?|speculates?)\s+that\b",
    re.IGNORECASE,
)

# Evidence/context adjuncts that the provider may represent separately from the
# relation object. Keep this reviewed and narrow: arbitrary ``in ...`` phrases
# can be part of an entity and must not be stripped mechanically.
_REVIEWED_RELATION_CONTEXT_SUFFIX_RE = re.compile(
    r"\s+in\s+(?:the|this)\s+(?:"
    r"observed\s+tests|sample|cohort|study|dataset|population"
    r")\s*$",
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


def _normalise_relation_object(text: str) -> str:
    value = " ".join(text.split()).strip(" .,:;!?")
    value = _REVIEWED_RELATION_CONTEXT_SUFFIX_RE.sub("", value).rstrip()
    return _normalise_role(value)


def _normalise_optional(text: str | None) -> str | None:
    if text is None:
        return None
    return " ".join(text.casefold().split()).strip()


def _normalise_attribution(attribution: Attribution | None) -> tuple[str, str] | None:
    if attribution is None:
        return None
    return (_normalise_role(attribution.agent), _normalise_role(attribution.act))


def _embedded_relation_text(proposition: Proposition) -> str:
    """Return relation surface with a reviewed attribution wrapper removed.

    The provider contract stores attribution separately from relational roles.
    When the proposition text still includes ``Smith reports that ...``, relation
    parsing must therefore compare subject/object against the embedded claim,
    while ``_raw_attribution`` independently validates the reporter and act.
    """
    match = ATTRIBUTION_RE.match(proposition.text)
    if match is None:
        return proposition.text
    return proposition.text[match.end():].lstrip()


def _relation_parts(proposition: Proposition) -> tuple[str, str, str, str] | None:
    match = RELATION_RE.match(_embedded_relation_text(proposition))
    if not match:
        return None
    sign_token = match.group("sign")
    sign = {
        "positively": "positive",
        "negatively": "negative",
    }.get(sign_token.casefold() if sign_token else "", "neutral")
    return (
        _normalise_role(match.group("subject")),
        " ".join(match.group("relation").casefold().split()),
        _normalise_relation_object(match.group("object")),
        sign,
    )


def _temporal_parts(proposition: Proposition) -> tuple[str, str] | None:
    """Return canonical (earlier, later) roles for simple preceded/followed forms."""
    match = TEMPORAL_RE.match(proposition.text)
    if not match:
        return None
    subject = _normalise_role(match.group("subject"))
    obj = _normalise_role(match.group("object"))
    relation = match.group("relation").casefold()
    if relation == "preceded":
        return subject, obj
    return obj, subject


def _raw_attribution(proposition: Proposition) -> tuple[str, str] | None:
    match = ATTRIBUTION_RE.match(proposition.text)
    if not match:
        return None
    return (_normalise_role(match.group("agent")), _normalise_role(match.group("act")))


def _provider_frame_mismatches(proposition: Proposition) -> list[str]:
    mismatches: list[str] = []
    parsed = _relation_parts(proposition)
    if parsed is not None:
        if proposition.subject is not None and _normalise_role(proposition.subject) != parsed[0]:
            mismatches.append("subject")
        if proposition.relation is not None and _normalise_optional(proposition.relation) != parsed[1]:
            mismatches.append("relation")
        if proposition.object is not None and _normalise_relation_object(proposition.object) != parsed[2]:
            mismatches.append("object")
        if parsed[3] in {"positive", "negative"} and _normalise_optional(proposition.relation_sign) != parsed[3]:
            mismatches.append("relation_sign")

    raw_attribution = _raw_attribution(proposition)
    if raw_attribution is not None and _normalise_attribution(proposition.attribution) != raw_attribution:
        mismatches.append("attribution")
    return mismatches


def _is_symmetric_swap(source: Proposition, candidate: Proposition) -> bool:
    """Return true only when raw text and structured frames prove a safe symmetric swap."""
    left = _relation_parts(source)
    right = _relation_parts(candidate)
    if left is None or right is None:
        return False
    if left[1] != right[1] or left[1] not in SYMMETRIC_RELATIONS:
        return False
    if left[3] != right[3]:
        return False
    if not (left[0] == right[2] and left[2] == right[0]):
        return False
    if source.relation is None or candidate.relation is None:
        return False
    return (
        _normalise_optional(source.relation) == left[1]
        and _normalise_optional(candidate.relation) == right[1]
        and not _provider_frame_mismatches(source)
        and not _provider_frame_mismatches(candidate)
    )


def _core_relation_delta(source: Proposition, candidate: Proposition) -> SemanticDelta | None:
    """Check relation semantics only where the core has a reliable rule."""
    left_time = _temporal_parts(source)
    right_time = _temporal_parts(candidate)
    if left_time is not None and right_time is not None:
        if left_time != right_time:
            return _delta(
                DeltaType.CHRONOLOGY_CHANGED,
                "Core temporal parsing detected a changed earlier/later relationship.",
                source_span=source.text,
                candidate_span=candidate.text,
            )
        return None

    left = _relation_parts(source)
    right = _relation_parts(candidate)
    if left is not None and right is not None and left[1] == right[1]:
        if left[3] != right[3]:
            return _delta(
                DeltaType.RELATION_SIGN_CHANGED,
                "Core relation parsing detected a positive/negative relation-sign change.",
                source_span=source.text,
                candidate_span=candidate.text,
            )
        swapped = left[0] == right[2] and left[2] == right[0] and left[0] != left[2]
        if swapped and not _is_symmetric_swap(source, candidate):
            return _delta(
                DeltaType.DIRECTION_REVERSAL,
                "Core relation parsing detected an argument reversal without proof that the relation is safely symmetric.",
                source_span=source.text,
                candidate_span=candidate.text,
            )
    return None


def _frame_consistency_deltas(source: Proposition, candidate: Proposition) -> list[SemanticDelta]:
    """Surface contradictions or missing high-risk structure in provider frames."""
    deltas: list[SemanticDelta] = []

    source_modality = _normalise_optional(source.modality)
    candidate_modality = _normalise_optional(candidate.modality)
    source_scope = _normalise_optional(source.modality_scope)
    candidate_scope = _normalise_optional(candidate.modality_scope)

    if source_modality is not None or candidate_modality is not None:
        if source_scope is None or candidate_scope is None:
            deltas.append(_unresolved(
                "A mapped modal proposition lacks an explicit modality scope.",
                source_span=source.text,
                candidate_span=candidate.text,
            ))
        elif source_scope != candidate_scope:
            deltas.append(_unresolved(
                "Provider-extracted modality scope differs across a mapped proposition.",
                source_span=source.text,
                candidate_span=candidate.text,
            ))
        if source_modality != candidate_modality:
            deltas.append(_unresolved(
                "Provider-extracted modal expression differs and requires semantic review.",
                source_span=source.text,
                candidate_span=candidate.text,
            ))

    source_force = _normalise_optional(source.causal_force)
    candidate_force = _normalise_optional(candidate.causal_force)
    if source_force is not None and candidate_force is not None and source_force != candidate_force:
        deltas.append(_delta(
            DeltaType.CAUSAL_STRENGTH_CHANGED,
            "Provider-extracted causal force differs across a mapped proposition.",
            source_span=source.text,
            candidate_span=candidate.text,
        ))

    source_time = _normalise_optional(source.temporal_relation)
    candidate_time = _normalise_optional(candidate.temporal_relation)
    if source_time is not None and candidate_time is not None and source_time != candidate_time:
        deltas.append(_delta(
            DeltaType.CHRONOLOGY_CHANGED,
            "Provider-extracted canonical chronology differs across a mapped proposition.",
            source_span=source.text,
            candidate_span=candidate.text,
        ))

    source_stance = _normalise_optional(source.normative_stance)
    candidate_stance = _normalise_optional(candidate.normative_stance)
    if source_stance is not None and candidate_stance is not None and source_stance != candidate_stance:
        deltas.append(_delta(
            DeltaType.EPISTEMIC_TYPE_CHANGED,
            "Provider-extracted normative stance differs across a mapped proposition.",
            source_span=source.text,
            candidate_span=candidate.text,
        ))

    source_attribution = _normalise_attribution(source.attribution)
    candidate_attribution = _normalise_attribution(candidate.attribution)
    if source_attribution != candidate_attribution:
        deltas.append(_delta(
            DeltaType.ATTRIBUTION_CHANGED,
            "Structured attribution agent or speech act differs across a mapped proposition.",
            source_span=source.text,
            candidate_span=candidate.text,
        ))

    source_sign = _normalise_optional(source.relation_sign)
    candidate_sign = _normalise_optional(candidate.relation_sign)
    if source_sign is not None and candidate_sign is not None and source_sign != candidate_sign:
        deltas.append(_delta(
            DeltaType.RELATION_SIGN_CHANGED,
            "Provider-extracted relation sign differs across a mapped proposition.",
            source_span=source.text,
            candidate_span=candidate.text,
        ))

    return deltas


def deltas_from_proposition_report(
    report: PropositionReport,
    *,
    assurance: str = "standard",
) -> list[SemanticDelta]:
    """Validate provider coverage/IDs before translating semantic judgements."""
    deltas: list[SemanticDelta] = []
    strict = assurance in {"strict", "review"}

    source_ids = [item.proposition_id for item in report.source_propositions]
    candidate_ids = [item.proposition_id for item in report.candidate_propositions]
    source_props = {item.proposition_id: item for item in report.source_propositions}
    candidate_props = {item.proposition_id: item for item in report.candidate_propositions}

    duplicate_source_ids = [item for item, count in Counter(source_ids).items() if count > 1]
    duplicate_candidate_ids = [item for item, count in Counter(candidate_ids).items() if count > 1]
    if duplicate_source_ids:
        deltas.append(_malformed(f"Duplicate source proposition IDs: {', '.join(sorted(duplicate_source_ids))}."))
    if duplicate_candidate_ids:
        deltas.append(_malformed(f"Duplicate candidate proposition IDs: {', '.join(sorted(duplicate_candidate_ids))}."))

    for proposition in (*report.source_propositions, *report.candidate_propositions):
        mismatches = _provider_frame_mismatches(proposition)
        if mismatches:
            deltas.append(_malformed(
                f"Provider frame disagrees with deterministic parse for proposition {proposition.proposition_id}: {', '.join(mismatches)}.",
                source_span=proposition.text if proposition.proposition_id in source_props else None,
                candidate_span=proposition.text if proposition.proposition_id in candidate_props else None,
            ))

    source_mapping_counts = Counter(item.source_id for item in report.source_to_candidate)
    candidate_mapping_counts = Counter(item.candidate_id for item in report.candidate_to_source)
    for source_id, count in source_mapping_counts.items():
        if count > 1:
            deltas.append(_malformed(f"Semantic verifier returned {count} mappings for source proposition {source_id}."))
    for candidate_id, count in candidate_mapping_counts.items():
        if count > 1:
            deltas.append(_malformed(f"Semantic verifier returned {count} mappings for candidate proposition {candidate_id}."))

    has_reference_errors = False
    for mapping in report.source_to_candidate:
        if mapping.source_id not in source_props:
            has_reference_errors = True
            deltas.append(_malformed(f"source_to_candidate references unknown source proposition {mapping.source_id}."))
        unknown_candidates = [item for item in mapping.candidate_ids if item not in candidate_props]
        if unknown_candidates:
            has_reference_errors = True
            deltas.append(_malformed(
                "source_to_candidate references unknown candidate proposition(s): "
                + ", ".join(sorted(set(unknown_candidates))) + "."
            ))

    for mapping in report.candidate_to_source:
        if mapping.candidate_id not in candidate_props:
            has_reference_errors = True
            deltas.append(_malformed(f"candidate_to_source references unknown candidate proposition {mapping.candidate_id}."))
        unknown_sources = [item for item in mapping.source_ids if item not in source_props]
        if unknown_sources:
            has_reference_errors = True
            deltas.append(_malformed(
                "candidate_to_source references unknown source proposition(s): "
                + ", ".join(sorted(set(unknown_sources))) + "."
            ))

    source_mappings = {item.source_id: item for item in report.source_to_candidate if item.source_id in source_props}
    candidate_mappings = {item.candidate_id: item for item in report.candidate_to_source if item.candidate_id in candidate_props}

    # Mapping arrays are many-to-many, but both directions must describe the same
    # graph when their references are otherwise well formed. Unknown IDs preserve
    # the PR #8 fail-safe policy (REVIEW) rather than cascading into a blocker.
    if not has_reference_errors:
        for source_id, mapping in source_mappings.items():
            for candidate_id in mapping.candidate_ids:
                reverse = candidate_mappings.get(candidate_id)
                if reverse is not None and source_id not in reverse.source_ids:
                    deltas.append(_malformed(
                        f"Mapping graph is not reciprocal: {source_id} -> {candidate_id} is missing from candidate_to_source.",
                        severity=Severity.BLOCKER if strict else Severity.WARNING,
                    ))
        for candidate_id, mapping in candidate_mappings.items():
            for source_id in mapping.source_ids:
                reverse = source_mappings.get(source_id)
                if reverse is not None and candidate_id not in reverse.candidate_ids:
                    deltas.append(_malformed(
                        f"Mapping graph is not reciprocal: {candidate_id} -> {source_id} is missing from source_to_candidate.",
                        severity=Severity.BLOCKER if strict else Severity.WARNING,
                    ))

    if not source_props and not candidate_props:
        deltas.append(_unresolved("Bidirectional proposition report contains no verifiable propositions."))
    elif not source_props or not candidate_props:
        deltas.append(_malformed(
            "Bidirectional proposition report is one-sided.",
            severity=Severity.BLOCKER if strict else Severity.WARNING,
        ))

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

        if len(mapping.candidate_ids) == 1 and mapping.candidate_ids[0] in candidate_props:
            candidate_prop = candidate_props[mapping.candidate_ids[0]]
            symmetric_swap = _is_symmetric_swap(proposition, candidate_prop)
            if mapping.relational_direction_preserved is False and not symmetric_swap:
                deltas.append(_delta(
                    DeltaType.DIRECTION_REVERSAL,
                    f"Relational direction is not preserved for source proposition {source_id}.",
                    source_span=proposition.text,
                    candidate_span=candidate_prop.text,
                ))
            relation_delta = _core_relation_delta(proposition, candidate_prop)
            if relation_delta is not None:
                deltas.append(relation_delta)
            deltas.extend(_frame_consistency_deltas(proposition, candidate_prop))
        elif mapping.relational_direction_preserved is False:
            deltas.append(_delta(
                DeltaType.DIRECTION_REVERSAL,
                f"Relational direction is not preserved for source proposition {source_id}.",
                source_span=proposition.text,
                candidate_span=_candidate_text(mapping.candidate_ids, candidate_props),
            ))

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