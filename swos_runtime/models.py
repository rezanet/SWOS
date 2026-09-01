"""Typed contracts for the Autonomous SWOS reference runtime."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class VersionDispatchError(ValueError):
    """Raised when a versioned SWOS document cannot be routed safely."""

    code = "unknown_version"


class ErrorCode(str, Enum):
    """Stable machine-readable errors shared by v2 boundaries."""

    INVALID_INPUT = "invalid_input"
    UNKNOWN_VERSION = "unknown_version"
    SCOPE_REQUIRED = "scope_required"
    SCOPE_DENIED = "scope_denied"
    EVIDENCE_UNRESOLVED = "evidence_unresolved"
    APPROVAL_MISMATCH = "approval_mismatch"
    POLICY_DENIED = "policy_denied"
    STALE_ASSESSMENT = "stale_assessment"
    CLASSIFICATION_DENIED = "classification_denied"
    RIGHTS_DENIED = "rights_denied"
    CONTRADICTION_REQUIRES_REVIEW = "contradiction_requires_review"
    INTEGRITY_FAILURE = "integrity_failure"
    COLLISION = "collision"
    UNSUPPORTED = "unsupported"
    RESOURCE_LIMIT = "resource_limit"
    NOT_RUN = "not_run"
    INTERNAL_ERROR = "internal_error"


class SWOSRuntimeError(RuntimeError):
    """A typed, serializable failure at a governed v2 boundary."""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code.value if isinstance(code, ErrorCode) else str(code)
        self.details = dict(details or {})
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": self.details}


class ResourceLimitError(SWOSRuntimeError):
    """Raised when an input exceeds an explicit bounded resource budget."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.RESOURCE_LIMIT, message, details=details)


@dataclass(frozen=True)
class ResourceLimits:
    """Conservative limits used before parsing or expanding untrusted input."""

    max_bytes: int = 10 * 1024 * 1024
    max_items: int = 10_000
    max_depth: int = 32
    max_string_length: int = 1_000_000
    max_duration_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.max_bytes <= 0 or self.max_items <= 0 or self.max_depth <= 0:
            raise ValueError("resource limits must be positive")
        if self.max_string_length <= 0 or self.max_duration_seconds <= 0:
            raise ValueError("resource limits must be positive")

    def check_bytes(self, value: bytes | bytearray | memoryview | int) -> None:
        size = value if isinstance(value, int) else len(value)
        if size > self.max_bytes:
            raise ResourceLimitError(
                "input exceeds byte limit",
                details={"actual": size, "limit": self.max_bytes, "resource": "bytes"},
            )

    def check_items(self, value: Any) -> None:
        count = value if isinstance(value, int) else len(value)
        if count > self.max_items:
            raise ResourceLimitError(
                "input exceeds item limit",
                details={"actual": count, "limit": self.max_items, "resource": "items"},
            )

    def check_depth(self, depth: int) -> None:
        if depth > self.max_depth:
            raise ResourceLimitError(
                "input exceeds nesting limit",
                details={"actual": depth, "limit": self.max_depth, "resource": "depth"},
            )

    def check_string(self, value: str) -> None:
        if len(value) > self.max_string_length:
            raise ResourceLimitError(
                "input exceeds string limit",
                details={
                    "actual": len(value),
                    "limit": self.max_string_length,
                    "resource": "string",
                },
            )


def canonical_json(value: Any) -> str:
    """Encode JSON using the SWOS byte-stable canonical profile."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_digest(value: Any) -> str:
    """Return a SHA-256 digest of canonical JSON or supplied bytes."""

    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


_IDENTIFIER_PREFIX = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")


def stable_identifier(prefix: str, value: Any) -> str:
    """Create a deterministic, namespaced identifier from canonical content."""

    if not prefix or not _IDENTIFIER_PREFIX.fullmatch(prefix):
        raise ValueError("identifier prefix must be a non-empty safe token")
    return f"{prefix}-{canonical_digest(value)[:32]}"


def artifact_identity(kind: str, digest: str) -> str:
    """Bind a human-readable artifact kind to a validated digest/token."""

    if not kind or not _IDENTIFIER_PREFIX.fullmatch(kind):
        raise ValueError("artifact kind must be a non-empty safe token")
    if not digest or not re.fullmatch(r"[A-Za-z0-9._:-]+", digest):
        raise ValueError("artifact digest must be a non-empty safe token")
    return f"{kind}-{digest}"


def utc_timestamp() -> str:
    """Return an RFC3339 UTC timestamp with microsecond precision."""

    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def require_version(document: dict[str, Any], expected: str) -> str:
    """Require a document to route to the explicitly requested version."""

    try:
        return dispatch_version(document, expected)
    except VersionDispatchError as exc:
        raise SWOSRuntimeError(ErrorCode.UNKNOWN_VERSION, str(exc)) from exc


def dispatch_version(document: dict[str, Any], expected: str | None = None) -> str:
    """Route a document only when it carries an explicit supported version.

    The v1 and v2 contracts are intentionally parallel.  No implicit upgrade or
    downgrade is permitted, including when a caller supplies an expected version.
    """

    if not isinstance(document, dict):
        raise VersionDispatchError("versioned document must be an object")
    candidates: list[str] = []
    for key in ("schema_version", "version"):
        value = document.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
    for key in ("$schema", "$id"):
        value = document.get(key)
        if isinstance(value, str):
            for version in ("1.0.0", "2.0.0"):
                if f"/{version}/" in value or value.endswith(f"/{version}"):
                    candidates.append(version)
    if not candidates or len(set(candidates)) != 1:
        raise VersionDispatchError("document requires one explicit supported version")
    version = candidates[0]
    if version not in {"1.0.0", "2.0.0"}:
        raise VersionDispatchError(f"unsupported SWOS version: {version}")
    if expected is not None and version != expected:
        raise VersionDispatchError(f"version mismatch: document is {version}, expected {expected}")
    return "v1" if version == "1.0.0" else "v2"


def swos_id(prefix: str) -> str:
    """Return a SWOS-prefixed UUID accepted by the frozen v1.0 schemas."""
    return f"{prefix}-{uuid4()}"


@dataclass(frozen=True)
class ResearchRequest:
    topic: str
    length: int = 2500
    audience: str = "intelligent general reader"
    style: str = "scholarly-natural"
    depth: str = "rigorous"
    jurisdiction: str | None = None
    citation_style: str = "authoritative-links"
    date_cutoff: str | None = None

    def __post_init__(self) -> None:
        if not self.topic.strip():
            raise ValueError("topic is required")
        if self.length < 500 or self.length > 10000:
            raise ValueError("length must be between 500 and 10000 words")
        if not self.audience.strip() or not self.style.strip() or not self.depth.strip():
            raise ValueError("audience, style and depth must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceRecord:
    source_id: str
    title: str
    url: str
    source_type: str
    provider: str
    text: str
    jurisdiction: str | None = None
    author: str | None = None
    published_date: str | None = None
    identifiers: dict[str, str] = field(default_factory=dict)
    metadata_verified: bool = False
    primary: bool = False
    retrieval_query: str = ""
    raw_rank: int | None = None
    rerank_score: float | None = None
    injection_detected: bool = False
    retraction_status: str = "not_checked"
    retraction_checked_at: str | None = None
    retraction_check_source: str | None = None
    licence: str = "unknown"
    access_status: str = "unknown"
    redistribution_allowed: bool = False
    excerpt_limit_chars: int = 0
    licence_cleared: bool = False
    licence_checked_at: str | None = None
    licence_check_source: str | None = None

    def excerpt(self, limit: int = 2400) -> str:
        text = " ".join(self.text.split())
        return text[:limit]

    def to_dict(self, *, include_text: bool = True) -> dict[str, Any]:
        data = asdict(self)
        if not include_text:
            data.pop("text", None)
        return data


@dataclass
class ProviderCall:
    stage: str
    model: str
    response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cost_estimate_usd: float | None
    elapsed_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunOutcome:
    run_id: str
    work_id: str
    status: str
    output_dir: str
    article_word_count: int
    human_interventions: int
    normal_user_questions_asked: int
    unresolved_questions: list[str]
    blocking_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
