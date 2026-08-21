"""Core data models for the SWOS Prose semantic-delta engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class VerificationStatus(str, Enum):
    PASS = "PASS"
    REPAIR = "REPAIR"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class DeltaType(str, Enum):
    CLAIM_ADDED = "claim_added"
    CLAIM_REMOVED = "claim_removed"
    CLAIM_CONTRADICTED = "claim_contradicted"
    NUMBER_CHANGED = "number_changed"
    DATE_CHANGED = "date_changed"
    UNIT_CHANGED = "unit_changed"
    ENTITY_CHANGED = "entity_changed"
    QUOTATION_CHANGED = "quotation_changed"
    CITATION_REMOVED = "citation_removed"
    CITATION_RELOCATED = "citation_relocated"
    NEGATION_CHANGED = "negation_changed"
    MODALITY_STRENGTHENED = "modality_strengthened"
    MODALITY_WEAKENED = "modality_weakened"
    CAUSAL_STRENGTH_CHANGED = "causal_strength_changed"
    DIRECTION_REVERSAL = "direction_reversal"
    RELATION_SIGN_CHANGED = "relation_sign_changed"
    SCOPE_BROADENED = "scope_broadened"
    SCOPE_NARROWED = "scope_narrowed"
    ATTRIBUTION_CHANGED = "attribution_changed"
    QUANTIFIER_CHANGED = "quantifier_changed"
    CHRONOLOGY_CHANGED = "chronology_changed"
    CONDITION_CHANGED = "condition_changed"
    EXCEPTION_REMOVED = "exception_removed"
    EPISTEMIC_TYPE_CHANGED = "epistemic_type_changed"
    MALFORMED_PROVIDER_RESPONSE = "malformed_provider_response"
    UNRESOLVED_EQUIVALENCE = "unresolved_equivalence"


@dataclass(frozen=True)
class SemanticAnchor:
    anchor_id: str
    kind: str
    text: str
    start: int
    end: int
    normalized: str
    protected: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticDelta:
    delta_type: DeltaType
    source_span: str | None
    candidate_span: str | None
    severity: Severity
    explanation: str
    source_start: int | None = None
    source_end: int | None = None
    candidate_start: int | None = None
    candidate_end: int | None = None
    repairable: bool = False
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["type"] = payload.pop("delta_type").value
        payload["severity"] = self.severity.value
        return payload


@dataclass
class RepairAttempt:
    attempt_number: int
    offending_span: str
    repaired_span: str
    candidate_before: str
    candidate_after: str
    deltas_before: list[SemanticDelta]
    deltas_after: list[SemanticDelta]
    success: bool
    failure_reason: str | None
    timestamp: str
    token_usage: dict[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_number": self.attempt_number,
            "offending_span": self.offending_span,
            "repaired_span": self.repaired_span,
            "candidate_before": self.candidate_before,
            "candidate_after": self.candidate_after,
            "deltas_before": [delta.to_dict() for delta in self.deltas_before],
            "deltas_after": [delta.to_dict() for delta in self.deltas_after],
            "success": self.success,
            "failure_reason": self.failure_reason,
            "timestamp": self.timestamp,
            "token_usage": self.token_usage,
        }


@dataclass
class VerificationResult:
    status: VerificationStatus
    source: str
    candidate: str
    semantic_deltas: list[SemanticDelta] = field(default_factory=list)
    source_anchors: list[SemanticAnchor] = field(default_factory=list)
    candidate_anchors: list[SemanticAnchor] = field(default_factory=list)
    verifier_used: bool = False
    verifier_independent: bool | None = None
    verifier_skip_reason: str | None = None
    verifier_notes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    token_usage: dict[str, int] | None = None
    cost_estimate: float | None = None

    @property
    def safe_for_automatic_use(self) -> bool:
        return self.status is VerificationStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "source": self.source,
            "candidate": self.candidate,
            "safe_for_automatic_use": self.safe_for_automatic_use,
            "semantic_deltas": [delta.to_dict() for delta in self.semantic_deltas],
            "source_anchors": [anchor.to_dict() for anchor in self.source_anchors],
            "candidate_anchors": [anchor.to_dict() for anchor in self.candidate_anchors],
            "verifier_used": self.verifier_used,
            "verifier_independent": self.verifier_independent,
            "verifier_skip_reason": self.verifier_skip_reason,
            "verifier_notes": self.verifier_notes,
            "notes": self.notes,
            "token_usage": self.token_usage,
            "cost_estimate": self.cost_estimate,
        }
