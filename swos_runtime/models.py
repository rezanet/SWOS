"""Typed contracts for the Autonomous SWOS reference runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


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
