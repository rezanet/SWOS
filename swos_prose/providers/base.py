"""Provider contracts for model-assisted semantic verification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..models import DeltaType, SemanticAnchor, SemanticDelta, Severity


@dataclass(frozen=True)
class Attribution:
    """Structured attribution attached to a proposition."""

    agent: str
    act: str


@dataclass(frozen=True)
class Proposition:
    proposition_id: str
    text: str
    subject: str | None = None
    relation: str | None = None
    object: str | None = None
    modality: str | None = None
    modality_scope: str | None = None
    attribution: Attribution | None = None
    causal_force: str | None = None
    temporal_relation: str | None = None
    normative_stance: str | None = None
    relation_sign: str | None = None


@dataclass(frozen=True)
class SourceToCandidateMapping:
    source_id: str
    candidate_ids: tuple[str, ...] = ()
    preserved: bool | None = None
    modality_preserved: bool | None = None
    scope_preserved: bool | None = None
    attribution_preserved: bool | None = None
    causal_force_preserved: bool | None = None
    relational_direction_preserved: bool | None = None
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
        if not isinstance(payload, dict):
            raise ValueError("proposition_report must be an object")

        def prop(item: dict[str, Any]) -> Proposition:
            if not isinstance(item, dict) or "id" not in item or "text" not in item:
                raise ValueError("Each proposition requires id and text.")
            return Proposition(
                proposition_id=str(item["id"]),
                text=str(item["text"]),
                subject=_optional_str(item.get("subject")),
                relation=_optional_str(item.get("relation")),
                object=_optional_str(item.get("object")),
                modality=_optional_str(item.get("modality")),
                modality_scope=_optional_str(item.get("modality_scope")),
                attribution=_optional_attribution(item.get("attribution")),
                causal_force=_optional_str(item.get("causal_force")),
                temporal_relation=_optional_str(item.get("temporal_relation")),
                normative_stance=_optional_str(item.get("normative_stance")),
                relation_sign=_optional_str(item.get("relation_sign")),
            )

        def s2c(item: dict[str, Any]) -> SourceToCandidateMapping:
            if not isinstance(item, dict) or "source_id" not in item:
                raise ValueError("Each source_to_candidate mapping requires source_id.")
            return SourceToCandidateMapping(
                source_id=str(item["source_id"]),
                candidate_ids=tuple(str(value) for value in item.get("candidate_ids", [])),
                preserved=_optional_bool(item.get("preserved")),
                modality_preserved=_optional_bool(item.get("modality_preserved")),
                scope_preserved=_optional_bool(item.get("scope_preserved")),
                attribution_preserved=_optional_bool(item.get("attribution_preserved")),
                causal_force_preserved=_optional_bool(item.get("causal_force_preserved")),
                relational_direction_preserved=_optional_bool(
                    item.get("relational_direction_preserved")
                ),
                confidence=_optional_float(item.get("confidence")),
                reason=_optional_str(item.get("reason")),
            )

        def c2s(item: dict[str, Any]) -> CandidateToSourceMapping:
            if not isinstance(item, dict) or "candidate_id" not in item:
                raise ValueError("Each candidate_to_source mapping requires candidate_id.")
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


def _optional_attribution(value: Any) -> Attribution | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("attribution must be an object with agent and act, or null.")
    agent = value.get("agent")
    act = value.get("act")
    if not isinstance(agent, str) or not agent.strip():
        raise ValueError("attribution.agent must be a non-empty string.")
    if not isinstance(act, str) or not act.strip():
        raise ValueError("attribution.act must be a non-empty string.")
    return Attribution(agent=agent.strip(), act=act.strip())


def _provider_delta(item: Any) -> SemanticDelta:
    if not isinstance(item, dict):
        return SemanticDelta(
            delta_type=DeltaType.MALFORMED_PROVIDER_RESPONSE,
            source_span=None,
            candidate_span=None,
            severity=Severity.WARNING,
            explanation="Provider delta entry is not an object.",
            confidence=1.0,
        )
    try:
        delta_type = DeltaType(item.get("type", item.get("delta_type")))
        severity = Severity(item.get("severity", Severity.WARNING.value))
        confidence = float(item.get("confidence", 1.0))
    except (TypeError, ValueError):
        return SemanticDelta(
            delta_type=DeltaType.MALFORMED_PROVIDER_RESPONSE,
            source_span=None,
            candidate_span=None,
            severity=Severity.WARNING,
            explanation="Provider returned an invalid semantic-delta type, severity, or confidence.",
            confidence=1.0,
        )
    return SemanticDelta(
        delta_type=delta_type,
        source_span=item.get("source_span"),
        candidate_span=item.get("candidate_span"),
        severity=severity,
        explanation=str(item.get("explanation", "Provider-reported semantic delta.")),
        repairable=bool(item.get("repairable", False)),
        confidence=confidence,
    )


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
        if not isinstance(payload, dict):
            raise ValueError("Provider assessment must be an object.")

        equivalent = _optional_bool(payload.get("equivalent"))
        raw_deltas = payload.get("deltas", [])
        if not isinstance(raw_deltas, list):
            raise ValueError("Provider deltas must be an array.")
        deltas = [_provider_delta(item) for item in raw_deltas]

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
            if not isinstance(token_usage, dict):
                raise ValueError("token_usage must be an object or null.")
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
