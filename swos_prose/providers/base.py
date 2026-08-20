"""Provider contracts for model-assisted semantic verification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..models import DeltaType, SemanticAnchor, SemanticDelta, Severity


@dataclass(frozen=True)
class Proposition:
    proposition_id: str
    text: str


@dataclass(frozen=True)
class SourceToCandidateMapping:
    source_id: str
    candidate_ids: tuple[str, ...] = ()
    preserved: bool | None = None
    modality_preserved: bool | None = None
    scope_preserved: bool | None = None
    attribution_preserved: bool | None = None
    causal_force_preserved: bool | None = None
    confidence: float | None = None
    reason: str | None = None


@dataclass(frozen=True)
class CandidateToSourceMapping:
    candidate_id: str
    source_ids: tuple[str, ...] = ()
    licensed: bool | None = None
    new_claim: bool | None = None
    confidence: float | None = None
    reason: str | None = None


@dataclass(frozen=True)
class PropositionReport:
    """Bidirectional proposition map returned by a semantic verifier."""

    source_propositions: tuple[Proposition, ...] = ()
    candidate_propositions: tuple[Proposition, ...] = ()
    source_to_candidate: tuple[SourceToCandidateMapping, ...] = ()
    candidate_to_source: tuple[CandidateToSourceMapping, ...] = ()
    unresolved: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PropositionReport":
        def prop(item: dict[str, Any]) -> Proposition:
            return Proposition(
                proposition_id=str(item["id"]),
                text=str(item["text"]),
            )

        def s2c(item: dict[str, Any]) -> SourceToCandidateMapping:
            return SourceToCandidateMapping(
                source_id=str(item["source_id"]),
                candidate_ids=tuple(str(value) for value in item.get("candidate_ids", [])),
                preserved=_optional_bool(item.get("preserved")),
                modality_preserved=_optional_bool(item.get("modality_preserved")),
                scope_preserved=_optional_bool(item.get("scope_preserved")),
                attribution_preserved=_optional_bool(item.get("attribution_preserved")),
                causal_force_preserved=_optional_bool(item.get("causal_force_preserved")),
                confidence=_optional_float(item.get("confidence")),
                reason=_optional_str(item.get("reason")),
            )

        def c2s(item: dict[str, Any]) -> CandidateToSourceMapping:
            return CandidateToSourceMapping(
                candidate_id=str(item["candidate_id"]),
                source_ids=tuple(str(value) for value in item.get("source_ids", [])),
                licensed=_optional_bool(item.get("licensed")),
                new_claim=_optional_bool(item.get("new_claim")),
                confidence=_optional_float(item.get("confidence")),
                reason=_optional_str(item.get("reason")),
            )

        return cls(
            source_propositions=tuple(prop(item) for item in payload.get("source_propositions", [])),
            candidate_propositions=tuple(prop(item) for item in payload.get("candidate_propositions", [])),
            source_to_candidate=tuple(s2c(item) for item in payload.get("source_to_candidate", [])),
            candidate_to_source=tuple(c2s(item) for item in payload.get("candidate_to_source", [])),
            unresolved=tuple(str(item) for item in payload.get("unresolved", [])),
        )


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"Expected boolean or null, got {value!r}")
    return value


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Expected number or null, got {value!r}")
    return float(value)


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


@dataclass
class ProviderAssessment:
    equivalent: bool | None
    deltas: list[SemanticDelta] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    independent_of_rewriter: bool | None = None
    token_usage: dict[str, int] | None = None
    cost_estimate: float | None = None
    proposition_report: PropositionReport | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProviderAssessment":
        equivalent = _optional_bool(payload.get("equivalent"))
        raw_deltas = payload.get("deltas", [])
        deltas = [
            SemanticDelta(
                delta_type=DeltaType(item.get("type", item.get("delta_type"))),
                source_span=item.get("source_span"),
                candidate_span=item.get("candidate_span"),
                severity=Severity(item.get("severity", Severity.WARNING.value)),
                explanation=str(item.get("explanation", "Provider-reported semantic delta.")),
                repairable=bool(item.get("repairable", False)),
                confidence=float(item.get("confidence", 1.0)),
            )
            for item in raw_deltas
        ]

        report_payload = payload.get("proposition_report")
        if report_payload is None and any(
            key in payload
            for key in (
                "source_propositions",
                "candidate_propositions",
                "source_to_candidate",
                "candidate_to_source",
                "unresolved",
            )
        ):
            report_payload = {
                "source_propositions": payload.get("source_propositions", []),
                "candidate_propositions": payload.get("candidate_propositions", []),
                "source_to_candidate": payload.get("source_to_candidate", []),
                "candidate_to_source": payload.get("candidate_to_source", []),
                "unresolved": payload.get("unresolved", []),
            }

        report = PropositionReport.from_dict(report_payload) if report_payload is not None else None

        token_usage = payload.get("token_usage")
        if token_usage is not None:
            token_usage = {str(key): int(value) for key, value in token_usage.items()}

        return cls(
            equivalent=equivalent,
            deltas=deltas,
            notes=[str(note) for note in payload.get("notes", [])],
            independent_of_rewriter=_optional_bool(payload.get("independent_of_rewriter")),
            token_usage=token_usage,
            cost_estimate=_optional_float(payload.get("cost_estimate")),
            proposition_report=report,
        )


class SemanticVerifierProvider(Protocol):
    """Host/model adapter contract.

    Providers analyse semantic equivalence; the SWOS Prose core still owns the
    final PASS/REPAIR/REVIEW/REJECT decision.
    """

    def verify(
        self,
        *,
        source: str,
        candidate: str,
        source_anchors: list[SemanticAnchor],
        candidate_anchors: list[SemanticAnchor],
        assurance: str,
        native_swos_context: dict | None,
    ) -> ProviderAssessment:
        ...
