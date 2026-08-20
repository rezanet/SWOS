"""Verification pipeline for the SWOS Prose semantic-delta engine."""
from __future__ import annotations

from .models import DeltaType, SemanticDelta, Severity, VerificationResult
from .providers.base import SemanticVerifierProvider
from .verify.classify import classify_deltas
from .verify.deterministic import deterministic_deltas
from .verify.propositions import deltas_from_proposition_report


ASSURANCE_LEVELS = {"standard", "strict", "review"}


def verify_rewrite(
    *,
    source: str,
    candidate: str,
    assurance: str = "standard",
    verifier_provider: SemanticVerifierProvider | None = None,
    native_swos_context: dict | None = None,
) -> VerificationResult:
    """Verify source/candidate semantic safety.

    The deterministic layer always runs first. Deterministic blockers short-circuit
    provider execution. Changed text without a bound semantic verifier cannot
    receive automatic PASS.

    In strict/review assurance, a provider must return a bidirectional proposition
    report; a bare ``equivalent=True`` is not sufficient.
    """
    if assurance not in ASSURANCE_LEVELS:
        raise ValueError(f"Unknown assurance level: {assurance}")

    if not isinstance(source, str) or not isinstance(candidate, str):
        raise TypeError("source and candidate must both be strings")

    source_anchors, candidate_anchors, deltas = deterministic_deltas(source, candidate)
    notes: list[str] = []
    verifier_used = False
    verifier_independent: bool | None = None
    token_usage = None
    cost_estimate = None

    if source == candidate:
        status = classify_deltas(deltas)
        return VerificationResult(
            status=status,
            source=source,
            candidate=candidate,
            semantic_deltas=deltas,
            source_anchors=source_anchors,
            candidate_anchors=candidate_anchors,
            notes=["Source and candidate are identical."],
        )

    deterministic_status = classify_deltas(deltas)
    if deterministic_status.value == "REJECT":
        return VerificationResult(
            status=deterministic_status,
            source=source,
            candidate=candidate,
            semantic_deltas=deltas,
            source_anchors=source_anchors,
            candidate_anchors=candidate_anchors,
            notes=["Deterministic/high-risk checks found a blocking semantic delta."],
        )

    if verifier_provider is None:
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
        assessment = verifier_provider.verify(
            source=source,
            candidate=candidate,
            source_anchors=source_anchors,
            candidate_anchors=candidate_anchors,
            assurance=assurance,
            native_swos_context=native_swos_context,
        )
        verifier_used = True
        verifier_independent = assessment.independent_of_rewriter
        token_usage = assessment.token_usage
        cost_estimate = assessment.cost_estimate

        provider_deltas = list(assessment.deltas)
        if assessment.proposition_report is not None:
            provider_deltas.extend(
                deltas_from_proposition_report(assessment.proposition_report)
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
        notes=notes,
        token_usage=token_usage,
        cost_estimate=cost_estimate,
    )
