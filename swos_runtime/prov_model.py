"""Canonical SWOS EPG v2 and PROV-DM interchange model.

The model deliberately contains no RDF or provider dependency.  Syntax adapters
serialise this representation and validation owns the release decision.
"""

from __future__ import annotations

import json
import math
import re
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


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple, set)):
        items = [_canonical(item) for item in value]
        return sorted(
            items,
            key=lambda item: json.dumps(
                item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ),
        )
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("non-finite PROV literal is not supported")
    return value


@dataclass(frozen=True)
class ResourceLimits:
    max_bytes: int = 5_000_000
    max_statements: int = 100_000
    max_literal_length: int = 1_000_000
    max_depth: int = 64
    timeout_seconds: float = 60.0

    def check_bytes(self, size: int) -> None:
        if size > self.max_bytes:
            raise ValueError("resource_limit: PROV input exceeds max_bytes")

    def check_document(self, document: "ProvDocument") -> None:
        if document.statement_count() > self.max_statements:
            raise ValueError("resource_limit: PROV statement count exceeds limit")
        for item in document.semantic_normal_form().get("extensions", []):
            if len(str(item.get("object", ""))) > self.max_literal_length:
                raise ValueError("resource_limit: PROV literal exceeds max_literal_length")


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

    def semantic_normal_form(self) -> dict[str, Any]:
        return _canonical(self.to_dict())

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
    if epg.get("schema_version") != EPG_VERSION:
        raise ValueError("EPG v2 requires explicit schema_version=2.0.0")
    if not is_absolute_iri(base_iri):
        raise ValueError("EPG v2 requires an absolute base IRI")
    namespaces = {**PROV_NAMESPACES, **dict(epg.get("namespaces") or {})}
    for prefix, namespace in namespaces.items():
        if not is_absolute_iri(namespace):
            raise ValueError(f"namespace {prefix!r} is not absolute")
    node_maps = {}
    for key in ("entities", "activities", "agents"):
        values = dict(epg.get(key) or {})
        if any(not is_absolute_iri(identifier) for identifier in values):
            raise ValueError(f"{key} contains a relative identifier")
        node_maps[key] = values
    relations = tuple(dict(item) for item in epg.get("relations", []) if isinstance(item, Mapping))
    for relation in relations:
        for key, value in relation.items():
            if key in {"type", "attributes", "time", "role", "label", "id"} or isinstance(
                value, (bool, int, float, Mapping, list)
            ):
                continue
            if isinstance(value, str) and value and not is_absolute_iri(value):
                raise ValueError(f"relation value {value!r} is not an absolute IRI")
    bundles = dict(epg.get("bundles") or {})
    if any(not is_absolute_iri(identifier) for identifier in bundles):
        raise ValueError("bundles contain a relative identifier")
    extensions = tuple(
        dict(item) for item in epg.get("extensions", []) if isinstance(item, Mapping)
    )
    for item in extensions:
        for key in ("subject", "predicate"):
            if item.get(key) and not is_absolute_iri(item[key]):
                raise ValueError(f"extension {key} is not an absolute IRI")
        if item.get("object_type") == "iri" and not is_absolute_iri(item.get("object")):
            raise ValueError("IRI extension object is not absolute")
        if item.get("datatype") and not is_absolute_iri(item["datatype"]):
            raise ValueError("typed extension literal datatype is not absolute")
    return ProvDocument(
        profile=str(epg.get("profile") or PROV_PROFILE),
        schema_version=EPG_VERSION,
        base_iri=base_iri,
        namespaces=namespaces,
        scope=dict(epg.get("scope") or {}),
        entities=node_maps["entities"],
        activities=node_maps["activities"],
        agents=node_maps["agents"],
        relations=relations,
        bundles=bundles,
        extensions=extensions,
        integrity=dict(epg.get("integrity") or {}),
    )
