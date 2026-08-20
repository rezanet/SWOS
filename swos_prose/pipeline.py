"""Verification pipeline for the SWOS Prose semantic-delta engine."""
from __future__ import annotations

from .models import DeltaType, SemanticDelta, Severity, VerificationResult, VerificationStatus
from .providers.base import ProviderAssessment, SemanticVerifierProvider
from .verify.classify import classify_deltas
from .verify.coverage import coverage_deltas
from .verify.deterministic import deterministic_deltas
from .verify.propositions import deltas_from_proposition_report


ASSURANCE_LEVELS = {"standard", "strict", "review"}


def _boundary_result(
    *,
    source: str,
    candidate: str,
    delta_type: DeltaType | None,
    note: str,
) -> VerificationResult:
    deltas: list[SemanticDelta] = []
    if delta_type is not None:
        deltas.append(SemanticDelta(
            delta_type=delta_type,
            source_span=source or None,
            candidate_span=candidate or None,
            severity=Severity.BLOCKER,
            explanation=note,
            repairable=False,
            confidence=1.0,
        ))
    return VerificationResult(
        status=classify_deltas(deltas),
        source=source,
        candidate=candidate,
        semantic_deltas=deltas,
        notes=[note],
        verifier_skip_reason=(
            f"boundary:{delta_type.value}"
            if delta_type is not None
            else "boundary:no_claims"
        ),
    )


def verify_rewrite(
    *,
    source: str,
    candidate: str,
    assurance: str = "standard",
    verifier_provider: SemanticVerifierProvider | None = None,
    native_swos_context: dict | None = None,
) -> VerificationResult:
    """Verify source/candidate semantic safety.

    Deterministic blockers short-circuit provider execution. Changed text without
    a bound semantic verifier cannot receive automatic PASS. In strict/review
    assurance, a provider must return a complete bidirectional proposition report.
    """
    if assurance not in ASSURANCE_LEVELS:
        raise ValueError(f"Unknown assurance level: {assurance}")
    if not isinstance(source, str) or not isinstance(candidate, str):
        raise TypeError("source and candidate must both be strings")

    # Explicit empty-input boundaries. Whitespace-only no-change is a benign no-op;
    # adding text to an empty source or deleting all source text is not.
    if not source.strip() and not candidate.strip():
        return _boundary_result(
            source=source,
            candidate=candidate,
            delta_type=None,
            note="No verifiable claims found; no change recommended.",
        )
    if not source.strip() and candidate.strip():
        return _boundary_result(
            source=source,
            candidate=candidate,
            delta_type=DeltaType.CLAIM_ADDED,
            note="Candidate adds content to an empty source.",
        )
    if source.strip() and not candidate.strip():
        return _boundary_result(
            source=source,
            candidate=candidate,
            delta_type=DeltaType.CLAIM_REMOVED,
            note="Candidate removes all source content.",
        )

    source_anchors, candidate_anchors, deltas = deterministic_deltas(source, candidate)
    notes: list[str] = []
    verifier_used = False
    verifier_independent: bool | None = None
    verifier_skip_reason: str | None = None
    verifier_notes: list[str] = []
    token_usage = None
    cost_estimate = None

    if source == candidate:
        return VerificationResult(
            status=classify_deltas(deltas),
            source=source,
            candidate=candidate,
            semantic_deltas=deltas,
            source_anchors=source_anchors,
            candidate_anchors=candidate_anchors,
            notes=["Source and candidate are identical; no change recommended."],
            verifier_skip_reason="source_identical",
        )

    deterministic_status = classify_deltas(deltas)
    if deterministic_status is VerificationStatus.REJECT:
        return VerificationResult(
            status=deterministic_status,
            source=source,
            candidate=candidate,
            semantic_deltas=deltas,
            source_anchors=source_anchors,
            candidate_anchors=candidate_anchors,
            notes=["Deterministic/high-risk checks found a blocking semantic delta."],
            verifier_skip_reason=next(
                (
                    f"deterministic_blocker:{delta.delta_type.value}"
                    for delta in deltas
                    if delta.severity is Severity.BLOCKER and not delta.repairable
                ),
                "deterministic_blocker",
            ),
        )

    if verifier_provider is None:
        verifier_skip_reason = "no_verifier_bound"
        deltas.append(SemanticDelta(
            delta_type=DeltaType.UNRESOLVED_EQUIVALENCE,
            source_span=None,
            candidate_span=None,
            severity=Severity.WARNING,
            explanation=(
                "Candidate differs from source but no model-assisted semantic verifier is bound. "
                "Deterministic checks alone cannot establish proposition-level equivalence."
            ),
            repairable=False,
            confidence=1.0,
        ))
        notes.append("No semantic verifier provider bound; changed text cannot receive automatic PASS.")
    else:
        verifier_used = True
        try:
            assessment = verifier_provider.verify(
                source=source,
                candidate=candidate,
                source_anchors=source_anchors,
                candidate_anchors=candidate_anchors,
                assurance=assurance,
                native_swos_context=native_swos_context,
            )
            if not isinstance(assessment, ProviderAssessment):
                raise TypeError("Verifier provider must return ProviderAssessment.")
        except (TypeError, ValueError, KeyError) as exc:
            deltas.append(SemanticDelta(
                delta_type=DeltaType.MALFORMED_PROVIDER_RESPONSE,
                source_span=None,
                candidate_span=None,
                severity=Severity.WARNING,
                explanation=f"Semantic verifier returned a malformed response: {exc}",
                confidence=1.0,
            ))
            notes.append("Malformed semantic-verifier response; automatic approval blocked.")
            assessment = None

        if assessment is not None:
            verifier_independent = assessment.independent_of_rewriter
            token_usage = assessment.token_usage
            cost_estimate = assessment.cost_estimate

            provider_deltas = list(assessment.deltas)
            if assessment.proposition_report is not None:
                provider_deltas.extend(
                    deltas_from_proposition_report(
                        assessment.proposition_report,
                        assurance=assurance,
                    )
                )
                provider_deltas.extend(
                    coverage_deltas(
                        assessment.proposition_report,
                        assurance=assurance,
                    )
                )
            elif assurance in {"strict", "review"}:
                provider_deltas.append(SemanticDelta(
                    delta_type=DeltaType.UNRESOLVED_EQUIVALENCE,
                    source_span=None,
                    candidate_span=None,
                    severity=Severity.WARNING,
                    explanation=(
                        f"{assurance} assurance requires a bidirectional proposition report; "
                        "the provider returned only a top-level equivalence judgement."
                    ),
                    repairable=False,
                    confidence=1.0,
                ))

            deltas.extend(provider_deltas)
            verifier_notes.extend(assessment.notes)
            notes.extend(assessment.notes)

            if assessment.equivalent is None:
                deltas.append(SemanticDelta(
                    delta_type=DeltaType.UNRESOLVED_EQUIVALENCE,
                    source_span=None,
                    candidate_span=None,
                    severity=Severity.WARNING,
                    explanation="Semantic verifier returned an unresolved equivalence judgement.",
                    confidence=1.0,
                ))
            elif assessment.equivalent is False and not provider_deltas:
                deltas.append(SemanticDelta(
                    delta_type=DeltaType.UNRESOLVED_EQUIVALENCE,
                    source_span=None,
                    candidate_span=None,
                    severity=Severity.WARNING,
                    explanation="Verifier rejected equivalence without a structured semantic delta.",
                    confidence=1.0,
                ))

            # Deterministic linguistic warnings are signals, not semantic verdicts.
            # A warning may be removed only when an independent verifier supplies
            # a complete proposition report, reports equivalence, has no unresolved
            # items, and the core validators produce no semantic deltas.
            if (
                assessment.equivalent is True
                and assessment.independent_of_rewriter is True
                and assessment.proposition_report is not None
                and not assessment.proposition_report.unresolved
                and not provider_deltas
            ):
                before_resolution = len(deltas)
                deltas = [
                    delta
                    for delta in deltas
                    if not (
                        delta.severity is Severity.WARNING
                        and delta.delta_type is DeltaType.QUANTIFIER_CHANGED
                    )
                ]
                if len(deltas) < before_resolution:
                    notes.append(
                        "Independent proposition verification resolved heuristic "
                        "quantifier risk."
                    )

    status = classify_deltas(deltas)
    return VerificationResult(
        status=status,
        source=source,
        candidate=candidate,
        semantic_deltas=deltas,
        source_anchors=source_anchors,
        candidate_anchors=candidate_anchors,
        verifier_used=verifier_used,
        verifier_independent=verifier_independent,
        verifier_skip_reason=verifier_skip_reason,
        verifier_notes=verifier_notes,
        notes=notes,
        token_usage=token_usage,
        cost_estimate=cost_estimate,
    )
