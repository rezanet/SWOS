"""Canonical SWOS EPG v2 and PROV-DM interchange model.

The model deliberately contains no RDF or provider dependency.  Syntax adapters
serialise this representation and validation owns the release decision.
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Mapping
from urllib.parse import urlparse

EPG_VERSION = "2.0.0"
PROV_PROFILE = "swos.prov-dm-round-trip.v2"
PROV_NAMESPACES = {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "swos": "https://swos.dev/prov#",
}
KNOWN_RELATIONS = frozenset(
    {
        "wasGeneratedBy",
        "used",
        "wasAssociatedWith",
        "wasAttributedTo",
        "wasDerivedFrom",
        "wasInformedBy",
        "actedOnBehalfOf",
        "specializationOf",
        "alternateOf",
        "hadMember",
        "wasStartedBy",
        "wasEndedBy",
        "invalidated",
        "qualifiedGeneration",
        "qualifiedUsage",
        "qualifiedAssociation",
        "qualifiedDerivation",
        "qualifiedAttribution",
    }
)
_IRI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


def is_absolute_iri(value: Any) -> bool:
    return bool(_IRI_RE.fullmatch(str(value or ""))) and bool(urlparse(str(value)).scheme)


def _canonical(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 64,
    deadline: float | None = None,
    ancestors: set[int] | None = None,
) -> Any:
    if deadline is not None and time.perf_counter() > deadline:
        raise ValueError("resource_limit: PROV operation exceeds timeout_seconds")
    if ancestors is None:
        ancestors = set()
    container = isinstance(value, Mapping) or isinstance(value, (list, tuple, set, frozenset))
    if container and id(value) in ancestors:
        raise ValueError("resource_limit: cyclic PROV value")
    if depth > max_depth:
        raise ValueError("resource_limit: PROV canonicalization depth exceeds max_depth")
    if isinstance(value, Mapping):
        ancestors.add(id(value))
        try:
            return {
                str(key): _canonical(
                    value[key],
                    depth=depth + 1,
                    max_depth=max_depth,
                    deadline=deadline,
                    ancestors=ancestors,
                )
                for key in sorted(value, key=str)
            }
        finally:
            ancestors.remove(id(value))
    if isinstance(value, (list, tuple, set, frozenset)):
        ancestors.add(id(value))
        try:
            items = [
                _canonical(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    deadline=deadline,
                    ancestors=ancestors,
                )
                for item in value
            ]
        finally:
            ancestors.remove(id(value))
        return sorted(
            items,
            key=lambda item: json.dumps(
                item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ),
        )
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("non-finite PROV literal is not supported")
    return value


def _check_nested_limits(
    value: Any,
    *,
    max_literal_length: int,
    max_depth: int,
    deadline: float,
    depth: int = 0,
    ancestors: set[int] | None = None,
) -> None:
    if time.perf_counter() > deadline:
        raise ValueError("resource_limit: PROV operation exceeds timeout_seconds")
    if ancestors is None:
        ancestors = set()
    container = isinstance(value, Mapping) or isinstance(value, (list, tuple, set, frozenset))
    if container and id(value) in ancestors:
        raise ValueError("resource_limit: cyclic PROV value")
    if depth > max_depth:
        raise ValueError("resource_limit: PROV canonicalization depth exceeds max_depth")
    if isinstance(value, str):
        if len(value) > max_literal_length:
            raise ValueError("resource_limit: PROV literal exceeds max_literal_length")
        return
    if not container:
        return
    ancestors.add(id(value))
    try:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if isinstance(key, str) and len(key) > max_literal_length:
                    raise ValueError("resource_limit: PROV literal exceeds max_literal_length")
                _check_nested_limits(
                    item,
                    max_literal_length=max_literal_length,
                    max_depth=max_depth,
                    deadline=deadline,
                    depth=depth + 1,
                    ancestors=ancestors,
                )
        else:
            for item in value:
                _check_nested_limits(
                    item,
                    max_literal_length=max_literal_length,
                    max_depth=max_depth,
                    deadline=deadline,
                    depth=depth + 1,
                    ancestors=ancestors,
                )
    finally:
        ancestors.remove(id(value))


@dataclass(frozen=True)
class ResourceLimits:
    max_bytes: int = 5_000_000
    max_statements: int = 100_000
    max_literal_length: int = 1_000_000
    max_depth: int = 64
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        for name in ("max_bytes", "max_statements", "max_literal_length", "max_depth"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(float(self.timeout_seconds))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive finite number")

    def check_bytes(self, size: int) -> None:
        if size > self.max_bytes:
            raise ValueError("resource_limit: PROV input exceeds max_bytes")

    def operation_deadline(self, started_at: float | None = None) -> float:
        return (time.perf_counter() if started_at is None else started_at) + self.timeout_seconds

    def check_deadline(self, deadline: float) -> None:
        if time.perf_counter() > deadline:
            raise ValueError("resource_limit: PROV operation exceeds timeout_seconds")

    def check_document(self, document: "ProvDocument", *, deadline: float | None = None) -> None:
        deadline = self.operation_deadline() if deadline is None else deadline
        self.check_deadline(deadline)
        if document.statement_count() > self.max_statements:
            raise ValueError("resource_limit: PROV statement count exceeds limit")
        self.check_deadline(deadline)
        _check_nested_limits(
            document.to_dict(),
            max_literal_length=self.max_literal_length,
            max_depth=self.max_depth,
            deadline=deadline,
        )


@dataclass(frozen=True)
class ProvDocument:
    profile: str = PROV_PROFILE
    schema_version: str = EPG_VERSION
    base_iri: str = ""
    namespaces: Mapping[str, str] = field(default_factory=dict)
    scope: Mapping[str, Any] = field(default_factory=dict)
    entities: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    activities: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    agents: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    relations: tuple[Mapping[str, Any], ...] = ()
    bundles: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    extensions: tuple[Mapping[str, Any], ...] = ()
    integrity: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not is_absolute_iri(self.base_iri):
            raise ValueError("absolute base_iri is required")
        object.__setattr__(self, "namespaces", dict(self.namespaces))
        object.__setattr__(self, "scope", dict(self.scope))
        object.__setattr__(
            self, "entities", {str(key): dict(value) for key, value in self.entities.items()}
        )
        object.__setattr__(
            self, "activities", {str(key): dict(value) for key, value in self.activities.items()}
        )
        object.__setattr__(
            self, "agents", {str(key): dict(value) for key, value in self.agents.items()}
        )
        object.__setattr__(self, "relations", tuple(dict(value) for value in self.relations))
        object.__setattr__(
            self, "bundles", {str(key): dict(value) for key, value in self.bundles.items()}
        )
        object.__setattr__(self, "extensions", tuple(dict(value) for value in self.extensions))
        object.__setattr__(self, "integrity", dict(self.integrity))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile": self.profile,
            "base_iri": self.base_iri,
            "namespaces": dict(self.namespaces),
            "scope": dict(self.scope),
            "entities": dict(self.entities),
            "activities": dict(self.activities),
            "agents": dict(self.agents),
            "relations": list(self.relations),
            "bundles": dict(self.bundles),
            "extensions": list(self.extensions),
            "integrity": dict(self.integrity),
        }

    def semantic_normal_form(
        self, *, max_depth: int = 64, deadline: float | None = None
    ) -> dict[str, Any]:
        return _canonical(self.to_dict(), max_depth=max_depth, deadline=deadline)

    def statement_count(self) -> int:
        return (
            len(self.entities)
            + len(self.activities)
            + len(self.agents)
            + len(self.relations)
            + sum(len(dict(bundle).get("statements", [])) for bundle in self.bundles.values())
            + len(self.extensions)
        )

    def fingerprint(self) -> Any:
        from .prov_validation import canonical_fingerprint

        return canonical_fingerprint(self)


EPGv2Document = ProvDocument


def document_from_epg(epg: Mapping[str, Any], *, base_iri: str) -> ProvDocument:
    if not isinstance(epg, Mapping):
        raise ValueError("EPG v2 input must be a JSON object")
    if epg.get("schema_version") != EPG_VERSION:
        raise ValueError("EPG v2 requires explicit schema_version=2.0.0")
    if epg.get("profile") != PROV_PROFILE:
        raise ValueError("EPG v2 requires explicit profile=swos.prov-dm-round-trip.v2")
    if not is_absolute_iri(base_iri):
        raise ValueError("EPG v2 requires an absolute base IRI")

    def mapping_field(field: str) -> dict[str, Any]:
        value = epg.get(field, {})
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ValueError(f"EPG v2 field {field!r} must be a JSON object")
        return dict(value)

    def record_list(field: str) -> tuple[dict[str, Any], ...]:
        value = epg.get(field, [])
        if value is None:
            return ()
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"EPG v2 field {field!r} must be a JSON array")
        records = []
        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                raise ValueError(f"EPG v2 {field} entry {index} must be a JSON object")
            records.append(dict(item))
        return tuple(records)

    namespaces = {**PROV_NAMESPACES, **mapping_field("namespaces")}
    for prefix, namespace in namespaces.items():
        if not is_absolute_iri(namespace):
            raise ValueError(f"namespace {prefix!r} is not absolute")
    node_maps = {}
    for key in ("entities", "activities", "agents"):
        values = mapping_field(key)
        if any(not is_absolute_iri(identifier) for identifier in values):
            raise ValueError(f"{key} contains a relative identifier")
        if any(not isinstance(node, Mapping) for node in values.values()):
            raise ValueError(f"{key} entries must be JSON objects")
        node_maps[key] = values
    relations = record_list("relations")
    for relation in relations:
        for key, value in relation.items():
            if key in {"type", "attributes", "time", "role", "label", "id"} or isinstance(
                value, (bool, int, float, Mapping, list)
            ):
                continue
            if isinstance(value, str) and value and not is_absolute_iri(value):
                raise ValueError(f"relation value {value!r} is not an absolute IRI")
    bundles = mapping_field("bundles")
    if any(not is_absolute_iri(identifier) for identifier in bundles):
        raise ValueError("bundles contain a relative identifier")
    if any(not isinstance(bundle, Mapping) for bundle in bundles.values()):
        raise ValueError("bundles entries must be JSON objects")
    extensions = record_list("extensions")
    for item in extensions:
        for key in ("subject", "predicate"):
            if item.get(key) and not is_absolute_iri(item[key]):
                raise ValueError(f"extension {key} is not an absolute IRI")
        if item.get("object_type") == "iri" and not is_absolute_iri(item.get("object")):
            raise ValueError("IRI extension object is not absolute")
        if item.get("datatype") and not is_absolute_iri(item["datatype"]):
            raise ValueError("typed extension literal datatype is not absolute")
    return ProvDocument(
        profile=PROV_PROFILE,
        schema_version=EPG_VERSION,
        base_iri=base_iri,
        namespaces=namespaces,
        scope=mapping_field("scope"),
        entities=node_maps["entities"],
        activities=node_maps["activities"],
        agents=node_maps["agents"],
        relations=relations,
        bundles=bundles,
        extensions=extensions,
        integrity=mapping_field("integrity"),
    )
