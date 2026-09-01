"""Scoped, evidence-bound Research Programme Memory v2 contracts.

The service in this module is intentionally provider-neutral.  It stores
metadata and references, not model prompts or raw restricted payloads, and it
delegates durable atomicity to :class:`ProgrammeStore`.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4

from .models import (
    ErrorCode,
    SWOSRuntimeError,
    canonical_digest,
    utc_timestamp,
)

RPM_VERSION = "2.0.0"


def _timestamp(value: datetime | str | None = None) -> str:
    if value is None:
        return utc_timestamp()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("timestamps must include a UTC offset")
        return (
            value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        )
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return result.astimezone(timezone.utc)


def _required(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    if len(value) > 256:
        raise ValueError(f"{field_name} is too long")
    return value.strip()


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"

    @property
    def rank(self) -> int:
        return list(DataClassification).index(self)


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    CONTRADICTED = "contradicted"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    DELETED = "deleted"


@dataclass(frozen=True)
class ResearchScope:
    repository_namespace_id: str
    programme_id: str
    project_id: str
    schema_version: str = RPM_VERSION

    def __post_init__(self) -> None:
        for name in ("repository_namespace_id", "programme_id", "project_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.schema_version != RPM_VERSION:
            raise ValueError(f"ResearchScope requires schema version {RPM_VERSION}")

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.repository_namespace_id, self.programme_id, self.project_id)

    def to_dict(self) -> dict[str, str]:
        return {
            "repository_namespace_id": self.repository_namespace_id,
            "programme_id": self.programme_id,
            "project_id": self.project_id,
        }


@dataclass(frozen=True)
class MemoryReadPolicy:
    max_classification: DataClassification
    include_inactive: bool = False
    review_mode: str = "normal"
    schema_version: str = RPM_VERSION

    def __post_init__(self) -> None:
        classification = self.max_classification
        if not isinstance(classification, DataClassification):
            object.__setattr__(self, "max_classification", DataClassification(classification))
        if self.review_mode not in {"normal", "governance", "adversarial"}:
            raise ValueError("unsupported memory read mode")
        if self.schema_version != RPM_VERSION:
            raise ValueError(f"MemoryReadPolicy requires schema version {RPM_VERSION}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_classification": self.max_classification.value,
            "include_inactive": self.include_inactive,
            "review_mode": self.review_mode,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ProgrammeProjectBinding:
    binding_id: str
    scope: ResearchScope
    label: str
    manifest_digest: str
    visibility_permissions: dict[str, bool] = field(
        default_factory=lambda: {"programme": True, "project": True}
    )
    created_at: str = field(default_factory=utc_timestamp)
    retired_at: str | None = None
    approval_id: str | None = None
    epg_reference: str | None = None
    sdl_reference: str | None = None
    status: str = "active"
    schema_version: str = RPM_VERSION

    @classmethod
    def create(
        cls, scope: ResearchScope, *, label: str, manifest_digest: str
    ) -> "ProgrammeProjectBinding":
        return cls(
            binding_id=f"binding-{uuid4()}",
            scope=scope,
            label=_required(label, "label"),
            manifest_digest=_required(manifest_digest, "manifest_digest"),
        )

    def __post_init__(self) -> None:
        _required(self.binding_id, "binding_id")
        _required(self.label, "label")
        _required(self.manifest_digest, "manifest_digest")
        if self.status not in {"active", "retired"}:
            raise ValueError("binding status is invalid")
        if self.schema_version != RPM_VERSION:
            raise ValueError(f"binding requires schema version {RPM_VERSION}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.to_dict()
        return data


@dataclass(frozen=True)
class MemoryCandidate:
    item_id: str
    category: str
    statement: str
    confidence: float
    data_classification: DataClassification
    owner: str
    expiry: datetime | str
    source_grounded: bool
    epg_node_ids: tuple[str, ...]
    sdl_decision_id: str | None
    parent_digest: str | None = None
    origin: str = ""
    visibility: str = "project"
    rights: tuple[str, ...] = ()
    correction_of: str | None = None
    supersedes: str | None = None
    contradiction_candidates: tuple[str, ...] = ()
    schema_version: str = RPM_VERSION

    def __post_init__(self) -> None:
        _required(self.item_id, "item_id")
        _required(self.category, "category")
        _required(self.statement, "statement")
        _required(self.owner, "owner")
        _required(self.sdl_decision_id, "sdl_decision_id")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between zero and one")
        classification = self.data_classification
        if not isinstance(classification, DataClassification):
            object.__setattr__(self, "data_classification", DataClassification(classification))
        object.__setattr__(self, "expiry", _timestamp(self.expiry))
        object.__setattr__(self, "epg_node_ids", tuple(self.epg_node_ids))
        if self.visibility not in {"programme", "project"}:
            raise ValueError("visibility must be programme or project")
        if self.schema_version != RPM_VERSION:
            raise ValueError(f"candidate requires schema version {RPM_VERSION}")

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["data_classification"] = self.data_classification.value
        data["epg_node_ids"] = list(self.epg_node_ids)
        data["rights"] = list(self.rights)
        data["contradiction_candidates"] = list(self.contradiction_candidates)
        return data


@dataclass(frozen=True)
class RPMOperation:
    operation_id: str
    operation_type: str
    scope: ResearchScope
    payload: dict[str, Any] = field(default_factory=dict)
    target_item_id: str | None = None
    expected_head: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    requested_at: str = field(default_factory=utc_timestamp)
    schema_version: str = RPM_VERSION

    def __post_init__(self) -> None:
        _required(self.operation_id, "operation_id")
        _required(self.operation_type, "operation_type")
        if self.schema_version != RPM_VERSION:
            raise ValueError(f"operation requires schema version {RPM_VERSION}")

    @classmethod
    def _new(
        cls,
        scope: ResearchScope,
        operation_type: str,
        payload: dict[str, Any] | None = None,
        *,
        target_item_id: str | None = None,
        expected_head: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> "RPMOperation":
        return cls(
            operation_id=f"operation-{uuid4()}",
            operation_type=operation_type,
            scope=scope,
            payload=payload or {},
            target_item_id=target_item_id,
            expected_head=expected_head,
            evidence=evidence or {},
        )

    @classmethod
    def register_project(
        cls, scope: ResearchScope, *, label: str, manifest_digest: str
    ) -> "RPMOperation":
        return cls._new(
            scope,
            "register_project",
            {"label": label, "manifest_digest": manifest_digest},
        )

    @classmethod
    def retire_project(cls, scope: ResearchScope) -> "RPMOperation":
        return cls._new(scope, "retire_project")

    @classmethod
    def unbind_project(cls, scope: ResearchScope) -> "RPMOperation":
        return cls._new(scope, "unbind_project")

    @classmethod
    def close_programme(cls, scope: ResearchScope) -> "RPMOperation":
        return cls._new(scope, "close_programme")

    @classmethod
    def write(cls, scope: ResearchScope, candidate: MemoryCandidate) -> "RPMOperation":
        evidence = {
            "epg_node_ids": list(candidate.epg_node_ids),
            "epg_digest": canonical_digest(list(candidate.epg_node_ids)),
            "sdl_decision_id": candidate.sdl_decision_id,
            "sdl_digest": canonical_digest(candidate.sdl_decision_id),
        }
        return cls._new(scope, "write", {"candidate": candidate.to_dict()}, evidence=evidence)

    @classmethod
    def confirm(cls, scope: ResearchScope, item_id: str) -> "RPMOperation":
        return cls._new(scope, "confirm", target_item_id=item_id)

    @classmethod
    def correct(
        cls, scope: ResearchScope, item_id: str, successor: MemoryCandidate
    ) -> "RPMOperation":
        return cls._new(
            scope,
            "correct",
            {"candidate": successor.to_dict()},
            target_item_id=item_id,
            evidence={
                "epg_node_ids": list(successor.epg_node_ids),
                "epg_digest": canonical_digest(list(successor.epg_node_ids)),
                "sdl_decision_id": successor.sdl_decision_id,
                "sdl_digest": canonical_digest(successor.sdl_decision_id),
            },
        )

    @classmethod
    def supersede(
        cls, scope: ResearchScope, item_id: str, successor: MemoryCandidate
    ) -> "RPMOperation":
        operation = cls.correct(scope, item_id, successor)
        return cls(
            operation_id=operation.operation_id,
            operation_type="supersede",
            scope=scope,
            payload=operation.payload,
            target_item_id=item_id,
            evidence=operation.evidence,
        )

    @classmethod
    def contradiction_open(
        cls, scope: ResearchScope, item_id: str, *, reason: str
    ) -> "RPMOperation":
        return cls._new(scope, "contradiction_opened", {"reason": reason}, target_item_id=item_id)

    @classmethod
    def contradiction_resolve(
        cls, scope: ResearchScope, item_id: str, *, resolution: str
    ) -> "RPMOperation":
        return cls._new(
            scope, "contradiction_resolved", {"resolution": resolution}, target_item_id=item_id
        )

    @classmethod
    def expire(cls, scope: ResearchScope, item_id: str) -> "RPMOperation":
        return cls._new(scope, "expire", target_item_id=item_id)

    @classmethod
    def delete(cls, scope: ResearchScope, item_id: str) -> "RPMOperation":
        return cls._new(scope, "delete", target_item_id=item_id)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.to_dict()
        return data

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class HumanApproval:
    approval_id: str
    approver: str
    role: str
    approved_at: str
    assessment_digest: str
    candidate_digest: str | None
    sdl_decision_id: str
    disposition: str
    rationale: str
    epg_digest: str | None = None
    schema_version: str = RPM_VERSION

    def __post_init__(self) -> None:
        for name in ("approval_id", "approver", "role", "assessment_digest", "rationale"):
            _required(getattr(self, name), name)
        if self.sdl_decision_id is not None:
            _required(self.sdl_decision_id, "sdl_decision_id")
        if self.candidate_digest is not None:
            _required(self.candidate_digest, "candidate_digest")
        object.__setattr__(self, "approved_at", _timestamp(self.approved_at))
        if self.disposition not in {"approved", "denied", "escalated"}:
            raise ValueError("approval disposition is invalid")
        if self.schema_version != RPM_VERSION:
            raise ValueError(f"approval requires schema version {RPM_VERSION}")

    @classmethod
    def for_assessment(
        cls, assessment: "MemoryAssessment", *, approver: str, role: str
    ) -> "HumanApproval":
        return cls(
            approval_id=f"approval-{uuid4()}",
            approver=approver,
            role=role,
            approved_at=utc_timestamp(),
            assessment_digest=assessment.digest,
            candidate_digest=assessment.candidate_digest,
            sdl_decision_id=assessment.sdl_decision_id,
            disposition="approved",
            rationale="approved for governed operation",
            epg_digest=assessment.epg_digest,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryAssessment:
    assessment_id: str
    status: str
    scope: ResearchScope
    operation_digest: str
    candidate_digest: str | None
    epg_digest: str | None
    epg_node_ids: tuple[str, ...]
    sdl_digest: str | None
    sdl_decision_id: str | None
    policy_id: str
    policy_version: str
    policy_digest: str
    target_head: str
    assessed_at: str
    expires_at: str
    denial_reasons: tuple[str, ...] = ()
    rights_result: str = "unknown"
    classification_result: str = "unknown"
    contradiction_result: str = "not_checked"
    operation: dict[str, Any] = field(default_factory=dict)
    consumed: bool = False
    schema_version: str = RPM_VERSION

    def __post_init__(self) -> None:
        if self.status not in {"allow", "deny", "review"}:
            raise ValueError("assessment status is invalid")
        object.__setattr__(self, "assessed_at", _timestamp(self.assessed_at))
        object.__setattr__(self, "expires_at", _timestamp(self.expires_at))
        if self.schema_version != RPM_VERSION:
            raise ValueError(f"assessment requires schema version {RPM_VERSION}")

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.to_dict()
        data["epg_node_ids"] = list(self.epg_node_ids)
        data["denial_reasons"] = list(self.denial_reasons)
        return data


@dataclass(frozen=True)
class MemoryQuery:
    category: str | None = None
    item_id: str | None = None
    statuses: tuple[str, ...] = ("active",)
    include_expired: bool = False
    schema_version: str = RPM_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RPM_VERSION:
            raise ValueError(f"query requires schema version {RPM_VERSION}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "item_id": self.item_id,
            "statuses": list(self.statuses),
            "include_expired": self.include_expired,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class MemoryProjection:
    item_id: str
    scope: ResearchScope
    category: str
    statement: str
    status: str
    confidence: float
    data_classification: DataClassification
    owner: str
    expiry: str
    version_id: str
    predecessor_id: str | None
    successor_id: str | None
    contradiction_ids: tuple[str, ...]
    last_event_hash: str
    candidate_digest: str
    epg_node_ids: tuple[str, ...]
    sdl_decision_id: str
    visibility: str
    origin: str
    schema_version: str = RPM_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.to_dict()
        data["data_classification"] = self.data_classification.value
        data["contradiction_ids"] = list(self.contradiction_ids)
        data["epg_node_ids"] = list(self.epg_node_ids)
        return data


@dataclass(frozen=True)
class MemoryReadReceipt:
    receipt_id: str
    scope: ResearchScope
    query_digest: str
    policy: MemoryReadPolicy
    as_of: str
    returned_item_ids: tuple[str, ...]
    exclusion_counts: dict[str, int]
    exceptional: bool
    influence_flag: bool
    epg_node_ids: tuple[str, ...]
    run_id: str | None = None
    work_id: str | None = None
    schema_version: str = RPM_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "scope": self.scope.to_dict(),
            "query_digest": self.query_digest,
            "policy": self.policy.to_dict(),
            "as_of": self.as_of,
            "returned_item_ids": list(self.returned_item_ids),
            "exclusion_counts": dict(self.exclusion_counts),
            "exceptional": self.exceptional,
            "influence_flag": self.influence_flag,
            "epg_node_ids": list(self.epg_node_ids),
            "run_id": self.run_id,
            "work_id": self.work_id,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class MemoryQueryResult:
    items: list[dict[str, Any]]
    receipt: MemoryReadReceipt
    schema_version: str = RPM_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "receipt": self.receipt.to_dict(),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ExpiryReport:
    scope: ResearchScope
    as_of: str
    candidates: list[dict[str, Any]]
    read_only: bool = True
    schema_version: str = RPM_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope.to_dict(),
            "as_of": self.as_of,
            "candidates": self.candidates,
            "read_only": self.read_only,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class RPMResult:
    status: str
    scope: ResearchScope
    operation_id: str
    event_id: str | None
    event_digest: str | None
    projection: dict[str, Any] | None
    receipt: dict[str, Any] | None = None
    schema_version: str = RPM_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.to_dict()
        return data


def _candidate_from_payload(payload: Mapping[str, Any]) -> MemoryCandidate:
    return MemoryCandidate(
        item_id=str(payload["item_id"]),
        category=str(payload["category"]),
        statement=str(payload["statement"]),
        confidence=float(payload["confidence"]),
        data_classification=DataClassification(payload["data_classification"]),
        owner=str(payload["owner"]),
        expiry=str(payload["expiry"]),
        source_grounded=bool(payload["source_grounded"]),
        epg_node_ids=tuple(str(value) for value in payload.get("epg_node_ids", [])),
        sdl_decision_id=str(payload["sdl_decision_id"]),
        parent_digest=payload.get("parent_digest"),
        origin=str(payload.get("origin", "")),
        visibility=str(payload.get("visibility", "project")),
        rights=tuple(str(value) for value in payload.get("rights", [])),
        correction_of=payload.get("correction_of"),
        supersedes=payload.get("supersedes"),
        contradiction_candidates=tuple(
            str(value) for value in payload.get("contradiction_candidates", [])
        ),
    )


class ResearchMemoryService:
    """Single assessed-operation path for all durable RPM transitions."""

    def __init__(self, store: Any, *, policy_digest: str | None = None) -> None:
        self.store = store
        self.policy_id = "swos.research-programme-memory"
        self.policy_version = RPM_VERSION
        self.policy_digest = (
            policy_digest
            or hashlib.sha256(b"swos.research-programme-memory.v2.fail-closed").hexdigest()
        )
        self.assessment_ttl = timedelta(minutes=5)
        self.store.initialize()

    def normal_read_policy(self) -> MemoryReadPolicy:
        return MemoryReadPolicy(DataClassification.INTERNAL)

    def governance_read_policy(self) -> MemoryReadPolicy:
        return MemoryReadPolicy(
            DataClassification.SECRET, include_inactive=True, review_mode="governance"
        )

    def _ensure_scope(self, scope: ResearchScope) -> None:
        if not isinstance(scope, ResearchScope):
            raise SWOSRuntimeError(ErrorCode.SCOPE_REQUIRED, "explicit ResearchScope is required")

    def _binding(
        self,
        scope: ResearchScope,
        *,
        allow_registration: bool = False,
        allow_retired: bool = False,
        allow_closed: bool = False,
    ) -> Any:
        if self.store.programme_status(scope) == "closed" and not allow_closed:
            raise SWOSRuntimeError(ErrorCode.POLICY_DENIED, "programme is closed")
        binding = self.store.get_binding(scope)
        if binding is None and not allow_registration:
            raise SWOSRuntimeError(ErrorCode.SCOPE_DENIED, "scope is not registered")
        if binding is not None and binding.get("status") != "active" and not allow_retired:
            raise SWOSRuntimeError(ErrorCode.SCOPE_DENIED, "scope is retired or unbound")
        return binding

    def _operation_from_dict(
        self, value: RPMOperation | Mapping[str, Any], scope: ResearchScope
    ) -> RPMOperation:
        if isinstance(value, RPMOperation):
            if value.scope != scope:
                raise SWOSRuntimeError(
                    ErrorCode.SCOPE_DENIED, "operation scope does not match request"
                )
            return value
        try:
            operation_scope = ResearchScope(**value["scope"])
            operation = RPMOperation(
                operation_id=str(value["operation_id"]),
                operation_type=str(value["operation_type"]),
                scope=operation_scope,
                payload=dict(value.get("payload", {})),
                target_item_id=value.get("target_item_id"),
                expected_head=value.get("expected_head"),
                evidence=dict(value.get("evidence", {})),
                requested_at=str(value.get("requested_at", utc_timestamp())),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SWOSRuntimeError(ErrorCode.INVALID_INPUT, "malformed RPM operation") from exc
        if operation.scope != scope:
            raise SWOSRuntimeError(ErrorCode.SCOPE_DENIED, "operation scope does not match request")
        return operation

    def assess_operation(
        self,
        scope: ResearchScope,
        operation: RPMOperation | Mapping[str, Any],
        *,
        as_of: datetime | str | None = None,
    ) -> MemoryAssessment:
        self._ensure_scope(scope)
        operation_obj = self._operation_from_dict(operation, scope)
        operation_as_of = _timestamp(as_of)
        allow_registration = operation_obj.operation_type == "register_project"
        self._binding(
            scope,
            allow_registration=allow_registration,
            allow_retired=operation_obj.operation_type == "close_programme",
            allow_closed=operation_obj.operation_type == "close_programme",
        )
        denial_reasons: list[str] = []
        candidate_digest: str | None = None
        epg_digest = operation_obj.evidence.get("epg_digest")
        sdl_digest = operation_obj.evidence.get("sdl_digest")
        epg_node_ids = tuple(str(value) for value in operation_obj.evidence.get("epg_node_ids", []))
        sdl_decision_id = operation_obj.evidence.get("sdl_decision_id")
        rights_result = "not_applicable"
        classification_result = "not_applicable"
        if operation_obj.operation_type in {"write", "correct", "supersede"}:
            try:
                candidate = _candidate_from_payload(operation_obj.payload["candidate"])
            except (KeyError, TypeError, ValueError):
                denial_reasons.append("candidate is malformed")
            else:
                candidate_digest = candidate.digest
                if (
                    not candidate.source_grounded
                    or not candidate.epg_node_ids
                    or not candidate.sdl_decision_id
                ):
                    denial_reasons.append("source grounding, EPG and SDL evidence are required")
                if _dt(candidate.expiry) <= _dt(operation_as_of):
                    denial_reasons.append("candidate expiry is not in the future")
                if candidate.data_classification in {
                    DataClassification.RESTRICTED,
                    DataClassification.SECRET,
                }:
                    classification_result = "denied"
                    denial_reasons.append("restricted or secret candidate is denied")
                else:
                    classification_result = candidate.data_classification.value
                rights_result = "allowed" if not candidate.rights else "review"
                if candidate.rights and "write" not in candidate.rights:
                    denial_reasons.append("candidate rights do not permit memory write")
                if not operation_obj.evidence.get("epg_digest") or not operation_obj.evidence.get(
                    "sdl_digest"
                ):
                    denial_reasons.append("operation EPG and SDL digests are required")
        if operation_obj.operation_type not in {
            "register_project",
            "retire_project",
            "unbind_project",
            "close_programme",
            "write",
            "confirm",
            "correct",
            "supersede",
            "contradiction_opened",
            "contradiction_resolved",
            "expire",
            "delete",
            "exceptional_read",
        }:
            denial_reasons.append("unsupported RPM operation")
        target_head = self.store.chain_head(scope)
        if operation_obj.expected_head is not None and operation_obj.expected_head != target_head:
            denial_reasons.append("operation target head is stale")
        if operation_obj.target_item_id and operation_obj.operation_type not in {
            "register_project",
            "close_programme",
        }:
            if self.store.get_projection(scope, operation_obj.target_item_id) is None:
                denial_reasons.append("lifecycle target is not present in this scope")
        status = "deny" if denial_reasons else "allow"
        assessment = MemoryAssessment(
            assessment_id=f"assessment-{uuid4()}",
            status=status,
            scope=scope,
            operation_digest=operation_obj.digest,
            candidate_digest=candidate_digest,
            epg_digest=str(epg_digest) if epg_digest else None,
            epg_node_ids=epg_node_ids,
            sdl_digest=str(sdl_digest) if sdl_digest else None,
            sdl_decision_id=str(sdl_decision_id) if sdl_decision_id else None,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            policy_digest=self.policy_digest,
            target_head=target_head,
            assessed_at=operation_as_of,
            expires_at=_timestamp(_dt(operation_as_of) + self.assessment_ttl),
            denial_reasons=tuple(denial_reasons),
            rights_result=rights_result,
            classification_result=classification_result,
            contradiction_result="review_required"
            if operation_obj.operation_type == "write"
            and self.store.get_projection(
                scope, operation_obj.payload.get("candidate", {}).get("item_id", "")
            )
            else "not_checked",
            operation=operation_obj.to_dict(),
        )
        self.store.save_assessment(assessment.to_dict())
        return assessment

    def _validate_approval(self, assessment: MemoryAssessment, approval: HumanApproval) -> None:
        if approval.disposition != "approved":
            raise SWOSRuntimeError(
                ErrorCode.APPROVAL_MISMATCH, "approval disposition is not approved"
            )
        if approval.assessment_digest != assessment.digest:
            raise SWOSRuntimeError(
                ErrorCode.APPROVAL_MISMATCH, "approval is not bound to assessment digest"
            )
        if assessment.candidate_digest and approval.candidate_digest != assessment.candidate_digest:
            raise SWOSRuntimeError(
                ErrorCode.APPROVAL_MISMATCH, "approval is not bound to candidate digest"
            )
        if assessment.sdl_decision_id and approval.sdl_decision_id != assessment.sdl_decision_id:
            raise SWOSRuntimeError(
                ErrorCode.APPROVAL_MISMATCH, "approval SDL decision does not match assessment"
            )

    def commit_operation(
        self,
        scope: ResearchScope,
        *,
        assessment_id: str,
        approval: HumanApproval,
        as_of: datetime | str | None = None,
    ) -> RPMResult:
        self._ensure_scope(scope)
        stored = self.store.get_assessment(assessment_id)
        if stored is None:
            raise SWOSRuntimeError(ErrorCode.STALE_ASSESSMENT, "assessment is unknown")
        assessment = self._assessment_from_dict(stored)
        if assessment.scope != scope:
            raise SWOSRuntimeError(
                ErrorCode.SCOPE_DENIED, "assessment scope does not match request"
            )
        now = _dt(as_of or utc_timestamp())
        if assessment.consumed or now > _dt(assessment.expires_at):
            raise SWOSRuntimeError(
                ErrorCode.STALE_ASSESSMENT, "assessment is expired or already consumed"
            )
        if assessment.policy_digest != self.policy_digest:
            raise SWOSRuntimeError(ErrorCode.STALE_ASSESSMENT, "assessment policy digest is stale")
        if assessment.status != "allow":
            raise SWOSRuntimeError(ErrorCode.POLICY_DENIED, "; ".join(assessment.denial_reasons))
        self._validate_approval(assessment, approval)
        operation = self._operation_from_dict(assessment.operation, scope)
        current_head = self.store.chain_head(scope)
        if current_head != assessment.target_head:
            raise SWOSRuntimeError(ErrorCode.STALE_ASSESSMENT, "commit target head changed")
        self._binding(
            scope,
            allow_registration=operation.operation_type == "register_project",
            allow_retired=operation.operation_type == "close_programme",
            allow_closed=operation.operation_type == "close_programme",
        )
        if operation.operation_type in {"write", "correct", "supersede"}:
            candidate = _candidate_from_payload(operation.payload["candidate"])
            if _dt(candidate.expiry) <= now:
                raise SWOSRuntimeError(ErrorCode.POLICY_DENIED, "candidate expired before commit")
        if operation.operation_type == "register_project":
            binding = ProgrammeProjectBinding.create(
                scope,
                label=str(operation.payload["label"]),
                manifest_digest=str(operation.payload["manifest_digest"]),
            )
            event = self.store.register_binding(
                binding.to_dict(), operation_id=operation.operation_id
            )
            projection = None
        elif operation.operation_type in {"retire_project", "unbind_project"}:
            event = self.store.transition_binding(
                scope,
                "retired",
                operation_id=operation.operation_id,
                reason=operation.operation_type,
            )
            projection = None
        elif operation.operation_type == "close_programme":
            event = self.store.close_programme(scope, operation_id=operation.operation_id)
            projection = None
        else:
            event_payload = self._event_payload(operation, assessment, approval)
            event = self.store.append_event(
                scope,
                operation.operation_type,
                operation.target_item_id or event_payload.get("item_id"),
                event_payload,
                operation_id=operation.operation_id,
            )
            projection = self.store.get_projection(
                scope, event_payload.get("item_id", operation.target_item_id)
            )
        self.store.consume_assessment(assessment_id, approval.to_dict())
        return RPMResult(
            status="committed",
            scope=scope,
            operation_id=operation.operation_id,
            event_id=event.get("event_id"),
            event_digest=event.get("event_hash"),
            projection=projection,
        )

    def _event_payload(
        self, operation: RPMOperation, assessment: MemoryAssessment, approval: HumanApproval
    ) -> dict[str, Any]:
        payload = dict(operation.payload)
        item_id = operation.target_item_id or payload.get("candidate", {}).get("item_id")
        payload.update(
            {
                "item_id": item_id,
                "status": self._status_for_operation(operation),
                "assessment_id": assessment.assessment_id,
                "assessment_digest": assessment.digest,
                "approval_id": approval.approval_id,
                "candidate_digest": assessment.candidate_digest,
                "epg_digest": assessment.epg_digest,
                "sdl_digest": assessment.sdl_digest,
                "epg_node_ids": list(assessment.epg_node_ids),
            }
        )
        if operation.operation_type in {"correct", "supersede"}:
            payload["successor_id"] = payload.get("candidate", {}).get("item_id")
        return payload

    @staticmethod
    def _status_for_operation(operation: RPMOperation) -> str:
        return {
            "write": "active",
            "confirm": "active",
            "correct": "corrected",
            "supersede": "superseded",
            "contradiction_opened": "contradicted",
            "contradiction_resolved": operation.payload.get("resolution", "active"),
            "expire": "expired",
            "delete": "deleted",
        }.get(operation.operation_type, "active")

    @staticmethod
    def _assessment_from_dict(data: Mapping[str, Any]) -> MemoryAssessment:
        scope = data["scope"]
        return MemoryAssessment(
            assessment_id=str(data["assessment_id"]),
            status=str(data["status"]),
            scope=ResearchScope(**scope),
            operation_digest=str(data["operation_digest"]),
            candidate_digest=data.get("candidate_digest"),
            epg_digest=data.get("epg_digest"),
            epg_node_ids=tuple(data.get("epg_node_ids", [])),
            sdl_digest=data.get("sdl_digest"),
            sdl_decision_id=data.get("sdl_decision_id"),
            policy_id=str(data["policy_id"]),
            policy_version=str(data["policy_version"]),
            policy_digest=str(data["policy_digest"]),
            target_head=str(data.get("target_head", "")),
            assessed_at=str(data["assessed_at"]),
            expires_at=str(data["expires_at"]),
            denial_reasons=tuple(data.get("denial_reasons", [])),
            rights_result=str(data.get("rights_result", "unknown")),
            classification_result=str(data.get("classification_result", "unknown")),
            contradiction_result=str(data.get("contradiction_result", "not_checked")),
            operation=dict(data.get("operation", {})),
            consumed=bool(data.get("consumed", False)),
        )

    def query(
        self,
        scope: ResearchScope,
        query: MemoryQuery,
        policy: MemoryReadPolicy,
        *,
        as_of: datetime | str | None = None,
    ) -> MemoryQueryResult:
        self._ensure_scope(scope)
        self._binding(scope)
        when = _timestamp(as_of)
        rows = self.store.list_projections(scope)
        items: list[dict[str, Any]] = []
        exclusions: dict[str, int] = {}
        for row in rows:
            status = str(row.get("status"))
            if not policy.include_inactive and status != MemoryStatus.ACTIVE.value:
                exclusions[status] = exclusions.get(status, 0) + 1
                continue
            if query.statuses and status not in query.statuses and not policy.include_inactive:
                exclusions[status] = exclusions.get(status, 0) + 1
                continue
            if query.item_id and row.get("item_id") != query.item_id:
                continue
            if query.category and row.get("category") != query.category:
                continue
            if (
                _dt(str(row["expiry"])) <= _dt(when)
                and not query.include_expired
                and policy.review_mode == "normal"
            ):
                exclusions["expired"] = exclusions.get("expired", 0) + 1
                continue
            classification = DataClassification(row["data_classification"])
            if classification.rank > policy.max_classification.rank:
                exclusions["classification"] = exclusions.get("classification", 0) + 1
                continue
            items.append(row)
        receipt = MemoryReadReceipt(
            receipt_id=f"read-{uuid4()}",
            scope=scope,
            query_digest=canonical_digest(query.to_dict()),
            policy=policy,
            as_of=when,
            returned_item_ids=tuple(str(item["item_id"]) for item in items),
            exclusion_counts=exclusions,
            exceptional=policy.review_mode != "normal",
            influence_flag=bool(items),
            epg_node_ids=tuple(node for item in items for node in item.get("epg_node_ids", [])),
        )
        self.store.save_receipt(receipt.to_dict())
        return MemoryQueryResult(items=items, receipt=receipt)

    def propose_expiry(
        self, scope: ResearchScope, *, as_of: datetime | str | None = None
    ) -> ExpiryReport:
        self._ensure_scope(scope)
        self._binding(scope)
        when = _timestamp(as_of)
        candidates = [
            row
            for row in self.store.list_projections(scope)
            if row.get("status") == MemoryStatus.ACTIVE.value and _dt(row["expiry"]) <= _dt(when)
        ]
        return ExpiryReport(scope=scope, as_of=when, candidates=candidates)

    def register_project(
        self,
        scope: ResearchScope,
        *,
        label: str,
        manifest_digest: str,
        approval: HumanApproval | None = None,
    ) -> RPMResult:
        operation = RPMOperation.register_project(
            scope, label=label, manifest_digest=manifest_digest
        )
        assessment = self.assess_operation(scope, operation)
        approval = approval or HumanApproval.for_assessment(
            assessment, approver="operator", role="memory_owner"
        )
        return self.commit_operation(
            scope, assessment_id=assessment.assessment_id, approval=approval
        )
