"""Canonical source-family identity and pre-retrieval diversity controls."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import canonical_digest, utc_timestamp

DIMENSIONS = (
    "work_family",
    "publisher",
    "venue",
    "author_cluster",
    "geography",
    "language",
    "period",
    "methodology",
    "source_type",
    "access_mode",
    "stance",
)
KNOWN_METADATA_STATES = frozenset({"observed", "externally_verified", "inferred", "unknown"})


def _mapping(source: Any) -> dict[str, Any]:
    if isinstance(source, Mapping):
        return dict(source)
    if hasattr(source, "to_dict"):
        try:
            return dict(source.to_dict(include_text=False))
        except TypeError:
            return dict(source.to_dict())
    return dict(vars(source))


@dataclass(frozen=True)
class FamilyIdentityPolicy:
    identity_fields: tuple[str, ...] = ("canonical_work_id", "work_id", "doi", "isbn", "title")
    title_fallback: bool = True
    strip_url_tracking: bool = True
    provider_is_not_identity: bool = True


@dataclass(frozen=True)
class SourceFamily:
    family_id: str
    canonical_key: str
    source_ids: tuple[str, ...]
    provider_ids: tuple[str, ...]
    metadata: Mapping[str, Mapping[str, Any]]
    titles: tuple[str, ...] = ()
    identifiers: Mapping[str, str] = field(default_factory=dict)

    @property
    def canonical_id(self) -> str:
        return self.family_id

    def dimension(self, name: str) -> Mapping[str, Any]:
        value = self.metadata.get(name, {})
        return value if isinstance(value, Mapping) else {"value": value, "status": "unknown"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "canonical_id": self.canonical_id,
            "canonical_key": self.canonical_key,
            "source_ids": list(self.source_ids),
            "provider_count": len(self.provider_ids),
            "metadata": {key: dict(value) for key, value in sorted(self.metadata.items())},
            "titles": list(self.titles),
            "identifiers": dict(sorted(self.identifiers.items())),
        }


@dataclass(frozen=True)
class FamilySet:
    families: tuple[SourceFamily, ...]
    source_to_family: Mapping[str, str]
    policy_digest: str

    def __iter__(self):
        return iter(self.families)

    def __len__(self) -> int:
        return len(self.families)

    def to_dict(self) -> dict[str, Any]:
        return {
            "families": [family.to_dict() for family in self.families],
            "source_to_family": dict(sorted(self.source_to_family.items())),
            "policy_digest": self.policy_digest,
        }

    def by_id(self, family_id: str) -> SourceFamily:
        return next(family for family in self.families if family.family_id == family_id)


@dataclass(frozen=True)
class DiversityRequirement:
    requirement_id: str
    dimensions: tuple[str, ...] = DIMENSIONS
    required_strata: Mapping[str, Sequence[str]] = field(default_factory=dict)
    min_family_count: int = 5
    max_hhi: float = 0.40
    max_share: float = 0.60
    min_composite: float = 0.50
    max_unknown_rate: float = 0.10
    counter_position_required: bool = False
    research_question: str = ""
    ontology_digest: str = ""
    declared_before_retrieval: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimensions", tuple(self.dimensions))
        object.__setattr__(
            self,
            "required_strata",
            {str(key): tuple(value) for key, value in self.required_strata.items()},
        )
        if not self.requirement_id or not self.dimensions:
            raise ValueError("diversity requirement needs an id and at least one dimension")
        if not isinstance(self.min_family_count, int) or self.min_family_count <= 0:
            raise ValueError("minimum family count must be a positive integer")
        if (
            not 0 < self.min_composite <= 1
            or not 0 <= self.max_hhi <= 1
            or not 0 <= self.max_share <= 1
            or not 0 <= self.max_unknown_rate <= 1
        ):
            raise ValueError("diversity thresholds must be within [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "dimensions": list(self.dimensions),
            "required_strata": {
                key: list(value) for key, value in sorted(self.required_strata.items())
            },
            "min_family_count": self.min_family_count,
            "max_hhi": self.max_hhi,
            "max_share": self.max_share,
            "min_composite": self.min_composite,
            "max_unknown_rate": self.max_unknown_rate,
            "counter_position_required": self.counter_position_required,
            "research_question": self.research_question,
            "ontology_digest": self.ontology_digest,
            "declared_before_retrieval": self.declared_before_retrieval,
        }


@dataclass(frozen=True)
class DimensionReport:
    dimension: str
    applicable: bool
    sample_size: int
    known_count: int
    unknown_count: int
    metadata_completeness: float
    unknown_rate: float
    category_counts: Mapping[str, int]
    shares: Mapping[str, float]
    max_share: float
    hhi: float
    effective_categories: float
    normalized_balance: float
    required_strata: tuple[str, ...]
    covered_strata: tuple[str, ...]
    missing_strata: tuple[str, ...]
    required_strata_coverage: float
    source_count_hhi: float
    claim_exposure_hhi: float
    status: str
    corrective_query: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "applicable": self.applicable,
            "sample_size": self.sample_size,
            "known_count": self.known_count,
            "unknown_count": self.unknown_count,
            "metadata_completeness": self.metadata_completeness,
            "unknown_rate": self.unknown_rate,
            "category_counts": dict(sorted(self.category_counts.items())),
            "shares": dict(sorted(self.shares.items())),
            "max_share": self.max_share,
            "hhi": self.hhi,
            "effective_categories": self.effective_categories,
            "normalized_balance": self.normalized_balance,
            "required_strata": list(self.required_strata),
            "covered_strata": list(self.covered_strata),
            "missing_strata": list(self.missing_strata),
            "required_strata_coverage": self.required_strata_coverage,
            "source_count_hhi": self.source_count_hhi,
            "claim_exposure_hhi": self.claim_exposure_hhi,
            "status": self.status,
            "corrective_query": self.corrective_query,
        }


@dataclass(frozen=True)
class SourceDiversityReport:
    report_id: str
    requirement_id: str
    policy_version: str
    family_count: int
    provider_count: int
    dimensions: Mapping[str, DimensionReport]
    research_grade_composite: float
    raw_status: str
    status: str
    counter_position: Mapping[str, Any]
    exception: Mapping[str, Any]
    limitations: tuple[str, ...]
    corrective_queries: tuple[str, ...]
    family_digest: str
    requirement_digest: str
    created_at: str = field(default_factory=utc_timestamp)

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "requirement_id": self.requirement_id,
            "policy_version": self.policy_version,
            "family_count": self.family_count,
            "provider_count": self.provider_count,
            "dimensions": {key: value.to_dict() for key, value in sorted(self.dimensions.items())},
            "research_grade_composite": self.research_grade_composite,
            "raw_status": self.raw_status,
            "status": self.status,
            "counter_position": dict(self.counter_position),
            "exception": dict(self.exception),
            "limitations": list(self.limitations),
            "corrective_queries": list(self.corrective_queries),
            "family_digest": self.family_digest,
            "requirement_digest": self.requirement_digest,
            "created_at": self.created_at,
        }


def _normalize_doi(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", text)


def _normalize_url(value: Any, strip_tracking: bool = True) -> str:
    parts = urlsplit(str(value or "").strip().lower())
    query = parse_qsl(parts.query, keep_blank_values=True)
    if strip_tracking:
        query = [
            (key, val)
            for key, val in query
            if not key.startswith("utm_") and key not in {"ref", "source"}
        ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path.rstrip("/"), urlencode(sorted(query)), "")
    )


def _value(source: Mapping[str, Any], dimension: str) -> Any:
    aliases = {
        "work_family": ("source_family_id", "canonical_work_id", "work_id", "doi", "isbn"),
        "publisher": ("publisher", "owner", "issuing_owner"),
        "venue": ("venue", "journal", "container_title"),
        "author_cluster": ("author_cluster", "author", "institution"),
        "geography": ("geography", "region", "jurisdiction", "country"),
        "language": ("language", "lang"),
        "period": ("period", "publication_period", "published_date", "year"),
        "methodology": ("methodology", "method", "method_family"),
        "source_type": ("source_type", "type"),
        "access_mode": ("access_mode", "access_status"),
        "stance": ("stance", "source_role", "position"),
    }
    for key in aliases.get(dimension, (dimension,)):
        if source.get(key) not in (None, ""):
            value = source[key]
            if dimension == "period" and isinstance(value, str):
                match = re.search(r"(\d{4})", value)
                if match:
                    value = f"{match.group(1)[:3]}0s"
            return value
    return None


def _metadata(source: Mapping[str, Any], dimension: str, value: Any) -> dict[str, Any]:
    declared = source.get("metadata_status", {})
    if isinstance(declared, Mapping):
        state = declared.get(dimension)
    else:
        state = None
    metadata = source.get("metadata", {})
    if isinstance(metadata, Mapping) and isinstance(metadata.get(dimension), Mapping):
        state = metadata[dimension].get("status", state)
        if value is None:
            value = metadata[dimension].get("value")
    state = str(state or ("unknown" if value in (None, "") else "observed"))
    if state not in KNOWN_METADATA_STATES:
        state = "unknown"
    return {
        "value": str(value) if value not in (None, "") else None,
        "status": state,
        "provenance": str(source.get("metadata_provenance") or "declared"),
    }


def canonicalize_source_families(sources: Sequence[Any], policy: FamilyIdentityPolicy) -> FamilySet:
    groups: dict[str, dict[str, Any]] = {}
    source_to_family: dict[str, str] = {}
    for raw in sources:
        item = _mapping(raw)
        source_id = str(item.get("source_id") or item.get("id") or canonical_digest(item)[:16])
        identity = ""
        for field_name in policy.identity_fields:
            value = item.get(field_name)
            if value not in (None, ""):
                identity = (
                    _normalize_doi(value) if field_name == "doi" else str(value).strip().lower()
                )
                if field_name == "title":
                    identity = re.sub(r"\W+", " ", identity).strip()
                break
        if not identity and policy.title_fallback:
            identity = re.sub(r"\W+", " ", str(item.get("title") or "")).strip().lower()
        if not identity:
            identity = _normalize_url(item.get("url"), policy.strip_url_tracking)
        key = identity or source_id
        family_id = "family-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        group = groups.setdefault(
            key,
            {
                "family_id": family_id,
                "source_ids": [],
                "provider_ids": [],
                "metadata": {},
                "titles": [],
                "identifiers": {},
            },
        )
        group["source_ids"].append(source_id)
        provider = item.get("provider")
        if provider not in (None, ""):
            group["provider_ids"].append(str(provider))
        if item.get("title"):
            group["titles"].append(str(item["title"]))
        for field_name in ("doi", "isbn", "canonical_work_id", "work_id"):
            if item.get(field_name):
                group["identifiers"][field_name] = (
                    _normalize_doi(item[field_name])
                    if field_name == "doi"
                    else str(item[field_name])
                )
        for dimension in DIMENSIONS:
            value = _value(item, dimension)
            group["metadata"].setdefault(dimension, _metadata(item, dimension, value))
            # A verified value wins over an inferred/unknown duplicate edition.
            candidate = _metadata(item, dimension, value)
            current = group["metadata"][dimension]
            if current.get("status") in {"unknown", "inferred"} and candidate.get("status") in {
                "observed",
                "externally_verified",
            }:
                group["metadata"][dimension] = candidate
        source_to_family[source_id] = family_id
    families = tuple(
        SourceFamily(
            family_id=value["family_id"],
            canonical_key=key,
            source_ids=tuple(sorted(set(value["source_ids"]))),
            provider_ids=tuple(sorted(set(value["provider_ids"]))),
            metadata={
                dimension: dict(meta) for dimension, meta in sorted(value["metadata"].items())
            },
            titles=tuple(sorted(set(value["titles"]))),
            identifiers=dict(sorted(value["identifiers"].items())),
        )
        for key, value in sorted(groups.items(), key=lambda pair: pair[1]["family_id"])
    )
    return FamilySet(
        families=families,
        source_to_family=source_to_family,
        policy_digest=canonical_digest(policy.__dict__),
    )


def _hhi(counts: Mapping[str, float]) -> tuple[dict[str, float], float, float, float]:
    total = sum(counts.values())
    if total <= 0:
        return {}, 1.0, 0.0, 0.0
    shares = {key: value / total for key, value in counts.items()}
    hhi = sum(value * value for value in shares.values())
    effective = 1 / hhi if hhi else 0.0
    categories = len(shares)
    balance = (1 - hhi) / (1 - 1 / categories) if categories > 1 else 0.0
    return shares, hhi, effective, max(0.0, min(1.0, balance))


def _claim_source_ids(claim: Mapping[str, Any]) -> list[str]:
    values = claim.get("source_ids") or claim.get("sources") or claim.get("citations") or []
    if isinstance(values, Mapping):
        values = list(values)
    result = []
    for value in values:
        if isinstance(value, Mapping):
            value = value.get("source_id") or value.get("id")
        if value:
            result.append(str(value))
    if claim.get("source_id"):
        result.append(str(claim["source_id"]))
    return list(dict.fromkeys(result))


def _valid_exception(exception: Mapping[str, Any] | None) -> bool:
    if not isinstance(exception, Mapping):
        return False
    required = ("sdl_decision_id", "rationale", "scope", "expires_at")
    if any(not str(exception.get(key) or "").strip() for key in required):
        return False
    try:
        date = str(exception["expires_at"]).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(date)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed > datetime.now(timezone.utc)
    except ValueError:
        return False


def measure_source_diversity(
    *,
    families: FamilySet,
    admitted_claims: Sequence[Mapping[str, Any]],
    requirements: DiversityRequirement,
    policy: FamilyIdentityPolicy | None = None,
    exception: Mapping[str, Any] | None = None,
) -> SourceDiversityReport:
    admitted_ids = {
        source_id for claim in admitted_claims for source_id in _claim_source_ids(claim)
    }
    selected = [
        family
        for family in families
        if not admitted_ids or any(source_id in admitted_ids for source_id in family.source_ids)
    ]
    exposure: dict[str, int] = {family.family_id: 0 for family in selected}
    for claim in admitted_claims:
        for source_id in _claim_source_ids(claim):
            family_id = families.source_to_family.get(source_id)
            if family_id in exposure:
                exposure[family_id] += 1
    dimensions: dict[str, DimensionReport] = {}
    corrective: list[str] = []
    balances: list[float] = []
    caps: list[float] = []
    for dimension in requirements.dimensions:
        applicable = dimension in DIMENSIONS
        values = [family.dimension(dimension) for family in selected] if applicable else []
        known = [
            value
            for value in values
            if value.get("status") in {"observed", "externally_verified"}
            and value.get("value") not in (None, "")
        ]
        counts: dict[str, int] = {}
        for value in known:
            key = str(value["value"])
            counts[key] = counts.get(key, 0) + 1
        shares, hhi, effective, balance = _hhi({key: float(value) for key, value in counts.items()})
        source_counts = {key: float(value) for key, value in counts.items()}
        exposure_counts: dict[str, float] = {}
        for family in selected:
            metadata = family.dimension(dimension)
            if metadata.get("status") in {"observed", "externally_verified"} and metadata.get(
                "value"
            ) not in (None, ""):
                key = str(metadata["value"])
                exposure_counts[key] = exposure_counts.get(key, 0.0) + max(
                    1, exposure.get(family.family_id, 0)
                )
        _, source_hhi, _, _ = _hhi(source_counts)
        _, exposure_hhi, _, _ = _hhi(exposure_counts)
        required = tuple(str(item) for item in requirements.required_strata.get(dimension, ()))
        covered = tuple(sorted(set(counts).intersection(required)))
        missing = tuple(sorted(set(required) - set(covered)))
        coverage = len(covered) / len(required) if required else 1.0
        total = len(values)
        unknown = total - len(known)
        completeness = len(known) / total if total else 0.0
        unknown_rate = unknown / total if total else 1.0
        failed = (
            not applicable
            or unknown_rate > requirements.max_unknown_rate
            or coverage < 1.0
            or max(shares.values(), default=1.0) > requirements.max_share
            or max(source_hhi, exposure_hhi) > requirements.max_hhi
            or (
                len(selected) >= requirements.min_family_count
                and balance < requirements.min_composite
            )
        )
        status = "fail" if failed else "pass"
        query = ""
        if missing:
            query = f"{dimension} {' '.join(missing)} independent source"
        elif failed:
            query = f"independent source evidence across {dimension}"
        if query:
            corrective.append(query)
        if applicable:
            balances.append(balance)
            caps.append(min(completeness, coverage))
        dimensions[dimension] = DimensionReport(
            dimension=dimension,
            applicable=applicable,
            sample_size=total,
            known_count=len(known),
            unknown_count=unknown,
            metadata_completeness=completeness,
            unknown_rate=unknown_rate,
            category_counts=counts,
            shares=shares,
            max_share=max(shares.values(), default=1.0),
            hhi=max(source_hhi, exposure_hhi),
            effective_categories=effective,
            normalized_balance=balance,
            required_strata=required,
            covered_strata=covered,
            missing_strata=missing,
            required_strata_coverage=coverage,
            source_count_hhi=source_hhi,
            claim_exposure_hhi=exposure_hhi,
            status=status,
            corrective_query=query,
        )
    composite = (
        math.prod(balances) ** (1 / len(balances))
        if balances and all(value >= 0 for value in balances)
        else 0.0
    )
    if caps:
        composite = min(composite, min(caps))
    stance_values = dimensions.get("stance")
    counter_present = bool(
        stance_values
        and any(
            value in {"counter", "opposing", "rival", "contradictory"}
            for value in stance_values.category_counts
        )
    )
    counter_position = {
        "required": requirements.counter_position_required,
        "status": "present"
        if counter_present
        else ("missing" if requirements.counter_position_required else "not_required"),
    }
    raw_failures = [item for item in dimensions.values() if item.status == "fail"]
    if requirements.counter_position_required and not counter_present:
        raw_failures.append(
            stance_values
            or DimensionReport(
                "stance", True, 0, 0, 0, 0, 1, {}, {}, 1, 1, 0, 0, (), (), (), 0, 1, 1, "fail"
            )
        )
        corrective.append("counter position contradictory evidence source")
    minimum_family_count = requirements.min_family_count
    if len(selected) < 3:
        raw_status = "fail"
    elif len(selected) < minimum_family_count:
        raw_status = "review_required"
    elif raw_failures or composite < requirements.min_composite:
        raw_status = "fail"
    else:
        raw_status = "pass"
    limitations: list[str] = []
    exception_payload = dict(exception or {}) if _valid_exception(exception) else {}
    status = raw_status
    if exception_payload:
        limitations.append(
            f"Narrow-corpus exception {exception_payload['sdl_decision_id']} applies only to {exception_payload['scope']} until {exception_payload['expires_at']}."
        )
        if raw_status == "fail":
            status = "review_required"
    if len(selected) < minimum_family_count:
        limitations.append(
            f"Only {len(selected)} distinct canonical source families were admitted; the configured minimum is {minimum_family_count}; provider count is not diversity."
        )
    if any(item.unknown_count for item in dimensions.values()):
        limitations.append("Unknown or inferred metadata does not count as coverage.")
    report_id = (
        "diversity-"
        + canonical_digest(
            {
                "families": [family.family_id for family in selected],
                "requirement": requirements.to_dict(),
            }
        )[:24]
    )
    providers = {provider for family in selected for provider in family.provider_ids}
    return SourceDiversityReport(
        report_id=report_id,
        requirement_id=requirements.requirement_id,
        policy_version="2.0.0",
        family_count=len(selected),
        provider_count=len(providers),
        dimensions=dimensions,
        research_grade_composite=max(0.0, min(1.0, composite)),
        raw_status=raw_status,
        status=status,
        counter_position=counter_position,
        exception=exception_payload,
        limitations=tuple(dict.fromkeys(limitations)),
        corrective_queries=tuple(dict.fromkeys(corrective)),
        family_digest=canonical_digest([family.to_dict() for family in selected]),
        requirement_digest=canonical_digest(requirements.to_dict()),
    )


def source_diversity_index_v1(sources: Sequence[Any]) -> float:
    """Compatibility-only provider scalar; never used by the v2 gate."""

    providers = {str(_mapping(source).get("provider") or "unknown") for source in sources}
    return min(1.0, len(providers) / 5) if providers else 0.0
