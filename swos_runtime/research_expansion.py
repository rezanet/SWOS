"""Bounded, pre-retrieval expansion plans derived from diversity gaps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .models import canonical_digest, utc_timestamp


@dataclass(frozen=True)
class ExpansionPlan:
    topic: str
    queries: tuple[str, ...]
    required_dimensions: tuple[str, ...]
    required_strata: Mapping[str, tuple[str, ...]]
    requires_review: bool
    limitations: tuple[str, ...] = ()
    plan_digest: str = ""
    created_at: str = field(default_factory=utc_timestamp)

    def __post_init__(self) -> None:
        if not self.plan_digest:
            object.__setattr__(
                self,
                "plan_digest",
                canonical_digest(
                    {
                        "topic": self.topic,
                        "queries": self.queries,
                        "dimensions": self.required_dimensions,
                    }
                ),
            )


def expansion_plan(report: Mapping[str, Any], *, topic: str, max_queries: int = 8) -> ExpansionPlan:
    dimensions = report.get("dimensions", {}) if isinstance(report, Mapping) else {}
    queries: list[str] = []
    required: dict[str, tuple[str, ...]] = {}
    for dimension, raw in dimensions.items():
        if not isinstance(raw, Mapping):
            continue
        missing = tuple(
            str(item) for item in raw.get("missing_strata", raw.get("required_strata_missing", []))
        )
        if missing:
            required[str(dimension)] = missing
            queries.append(f"{topic} {dimension} {' '.join(missing)} independent evidence")
        elif raw.get("status") == "fail":
            queries.append(f"{topic} independent sources across {dimension}")
    counter = report.get("counter_position", {}) if isinstance(report, Mapping) else {}
    if isinstance(counter, Mapping) and counter.get("status") in {"missing", "fail"}:
        queries.append(f"{topic} counter-position contradictory evidence limitations")
    if not queries:
        queries.append(f"{topic} limitations exceptions counter-evidence")
    bounded = tuple(dict.fromkeys(query for query in queries if query.strip()))[
        : max(1, int(max_queries))
    ]
    return ExpansionPlan(
        topic=topic,
        queries=bounded,
        required_dimensions=tuple(sorted(required)),
        required_strata=required,
        requires_review=str(report.get("status") in {"fail", "review_required"}) or bool(required),
        limitations=("Expansion is bounded and must be re-measured after retrieval.",),
    )
