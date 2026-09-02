"""Provider-free PROV-JSON, PROV-N, and PROV-O/TriG adapters."""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Mapping

from .prov_model import (
    EPG_VERSION,
    PROV_NAMESPACES,
    PROV_PROFILE,
    ProvDocument,
    ResourceLimits,
    document_from_epg,
    is_absolute_iri,
)

ProvFormat = str
SUPPORTED_FORMATS = ("prov-json", "prov-n", "prov-o-trig")


def epg_to_prov(epg: Mapping[str, Any], *, base_iri: str) -> ProvDocument:
    return document_from_epg(epg, base_iri=base_iri)


def epg_v1_to_v2(epg: Mapping[str, Any], *, base_iri: str) -> dict[str, Any]:
    """Map the frozen array-shaped v1 EPG into the parallel v2 shape.

    Original v1 identifiers and relation records are retained as SWOS
    extension assertions so migration is auditable and does not rewrite v1.
    """

    if epg.get("schema_version") != "1.0.0":
        raise ValueError("v1 EPG conversion requires schema_version=1.0.0")
    if not is_absolute_iri(base_iri):
        raise ValueError("v2 migration requires an absolute base IRI")

    def identifier(value: Any) -> str:
        text = str(value or "")
        if is_absolute_iri(text):
            return text
        return base_iri.rstrip("/") + "/id/" + text

    def node_list(values: Any, node_type: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for item in values or []:
            if not isinstance(item, Mapping):
                continue
            original = str(
                item.get("entity_id") or item.get("activity_id") or item.get("agent_id") or ""
            )
            if not original:
                continue
            current = identifier(original)
            attrs = {
                key: {"value": value}
                for key, value in item.items()
                if key
                not in {
                    "entity_id",
                    "activity_id",
                    "agent_id",
                    "entity_type",
                    "activity_type",
                    "agent_kind",
                }
            }
            attrs["swos:v1_id"] = {
                "value": original,
                "datatype": PROV_NAMESPACES["swos"] + "V1Identifier",
            }
            result[current] = {"type": node_type, "attributes": attrs}
        return result

    extensions = []
    for relation in epg.get("relations", []) or []:
        if not isinstance(relation, Mapping):
            continue
        extensions.append(
            {
                "subject": identifier(relation.get("subject")),
                "predicate": "https://swos.dev/prov#v1RelationType",
                "object": str(relation.get("relation_type") or ""),
                "object_type": "literal",
                "datatype": "http://www.w3.org/2001/XMLSchema#string",
                "v1_relation": dict(relation),
            }
        )
    return {
        "schema_version": EPG_VERSION,
        "profile": PROV_PROFILE,
        "base_iri": base_iri,
        "namespaces": dict(PROV_NAMESPACES),
        "scope": {"work_id": epg.get("work_id")},
        "entities": node_list(epg.get("entities"), "entity"),
        "activities": node_list(epg.get("activities"), "activity"),
        "agents": node_list(epg.get("agents"), "agent"),
        "relations": [],
        "bundles": {},
        "extensions": extensions,
        "integrity": {
            "v1_source_digest": __import__("hashlib")
            .sha256(json.dumps(epg, sort_keys=True, separators=(",", ":")).encode("utf-8"))
            .hexdigest()
        },
    }


v1_epg_to_v2 = epg_v1_to_v2


def epg_v2_to_v1(
    document: ProvDocument | Mapping[str, Any], *, work_id: str | None = None
) -> dict[str, Any]:
    """Project a v2 document to the frozen v1 EPG envelope without mutating it."""

    if isinstance(document, Mapping):
        document = ProvDocument(**dict(document))
    if not isinstance(document, ProvDocument) or document.schema_version != EPG_VERSION:
        raise ValueError("v2 EPG conversion requires an EPG v2 document")

    def original(identifier: str, node: Mapping[str, Any]) -> str:
        attrs = node.get("attributes", {})
        marker = attrs.get("swos:v1_id") if isinstance(attrs, Mapping) else None
        if isinstance(marker, Mapping) and marker.get("value"):
            return str(marker["value"])
        return str(identifier)

    entities = []
    for identifier, node in document.entities.items():
        entities.append(
            {
                "entity_id": original(identifier, node),
                "entity_type": str(node.get("v1_entity_type") or "source_work"),
                "label": str(node.get("label") or identifier),
            }
        )
    activities = [
        {
            "activity_id": identifier,
            "activity_type": str(node.get("activity_type") or "classification"),
            "started_at": node.get("started_at") or "1970-01-01T00:00:00+00:00",
        }
        for identifier, node in document.activities.items()
    ]
    agents = [
        {
            "agent_id": identifier,
            "agent_kind": str(node.get("agent_kind") or "tool"),
            "label": str(node.get("label") or identifier),
        }
        for identifier, node in document.agents.items()
    ]
    relations = []
    for extension in document.extensions:
        if isinstance(extension.get("v1_relation"), Mapping):
            relations.append(dict(extension["v1_relation"]))
    for relation in document.relations:
        relations.append(
            {
                "relation_type": relation.get("type"),
                "subject": relation.get("subject") or relation.get("entity"),
                "object": relation.get("object") or relation.get("activity"),
            }
        )
    return {
        "schema_version": "1.0.0",
        "work_id": work_id or str(document.scope.get("work_id") or ""),
        "entities": entities,
        "activities": activities,
        "agents": agents,
        "relations": relations,
    }


v2_epg_to_v1 = epg_v2_to_v1


def prov_to_epg(document: ProvDocument, *, profile: str = PROV_PROFILE) -> dict[str, Any]:
    if not isinstance(document, ProvDocument):
        raise ValueError("prov_to_epg requires a ProvDocument")
    result = document.to_dict()
    result["schema_version"] = EPG_VERSION
    result["profile"] = profile
    return result


def _assert_format(format_name: str) -> None:
    if format_name not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported PROV format: {format_name}")


def _json_payload(document: ProvDocument) -> dict[str, Any]:
    relations_by_type: dict[str, dict[str, Any]] = {}
    for index, relation in enumerate(document.relations):
        relation_type = str(relation.get("type") or "extensionRelation")
        relation_id = str(relation.get("id") or f"{document.base_iri}relation/{index + 1}")
        relations_by_type.setdefault(relation_type, {})[relation_id] = {
            key: value for key, value in relation.items() if key != "type"
        }
    return {
        "prefix": dict(document.namespaces),
        "entity": dict(document.entities),
        "activity": dict(document.activities),
        "agent": dict(document.agents),
        **relations_by_type,
        "bundle": dict(document.bundles),
        "swos": {
            "schema_version": document.schema_version,
            "profile": document.profile,
            "base_iri": document.base_iri,
            "scope": dict(document.scope),
            "extensions": list(document.extensions),
            "integrity": dict(document.integrity),
            "relations": list(document.relations),
        },
    }


def _from_json_payload(payload: Mapping[str, Any]) -> ProvDocument:
    if not isinstance(payload, Mapping):
        raise ValueError("PROV-JSON payload must be a JSON object")
    swos = payload.get("swos") if isinstance(payload.get("swos"), Mapping) else {}
    base = str(swos.get("base_iri") or "")
    if not base:
        base = str(payload.get("base_iri") or "")
    if not is_absolute_iri(base):
        raise ValueError("PROV-JSON lacks an absolute base IRI")
    raw_relations = swos.get("relations")
    if not isinstance(raw_relations, list):
        raw_relations = []
        excluded = {"prefix", "entity", "activity", "agent", "bundle", "swos"}
        for relation_type, values in payload.items():
            if relation_type in excluded or not isinstance(values, Mapping):
                continue
            for relation_id, relation in values.items():
                if isinstance(relation, Mapping):
                    raw_relations.append(
                        {"type": relation_type, "id": relation_id, **dict(relation)}
                    )
    namespaces = dict(PROV_NAMESPACES)
    namespaces.update(dict(payload.get("prefix") or {}))
    return ProvDocument(
        profile=str(swos.get("profile") or PROV_PROFILE),
        schema_version=str(swos.get("schema_version") or EPG_VERSION),
        base_iri=base,
        namespaces=namespaces,
        scope=dict(swos.get("scope") or {}),
        entities=dict(payload.get("entity") or {}),
        activities=dict(payload.get("activity") or {}),
        agents=dict(payload.get("agent") or {}),
        relations=tuple(dict(item) for item in raw_relations if isinstance(item, Mapping)),
        bundles=dict(payload.get("bundle") or {}),
        extensions=tuple(
            dict(item) for item in swos.get("extensions", []) if isinstance(item, Mapping)
        ),
        integrity=dict(swos.get("integrity") or {}),
    )


def _payload_marker(document: ProvDocument) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(
            document.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).decode("ascii")
    return encoded.rstrip("=")


def _decode_marker(marker: str) -> ProvDocument:
    padding = "=" * (-len(marker) % 4)
    payload = json.loads(base64.urlsafe_b64decode(marker + padding).decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("lossless PROV payload must be a JSON object")
    return ProvDocument(**payload)


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _serialize_prov_n(document: ProvDocument) -> bytes:
    lines = [
        "document",
        f"  prefix swos <{document.namespaces.get('swos', PROV_NAMESPACES['swos'])}>",
        f"  prefix prov <{document.namespaces.get('prov', PROV_NAMESPACES['prov'])}>",
    ]
    for identifier in sorted(document.entities):
        lines.append(f"  entity({_quote(identifier)})")
    for identifier in sorted(document.activities):
        lines.append(f"  activity({_quote(identifier)})")
    for identifier in sorted(document.agents):
        lines.append(f"  agent({_quote(identifier)})")
    for relation in document.relations:
        relation_type = str(relation.get("type") or "extensionRelation")
        relation_id = relation.get("id") or ""
        args = [str(value) for key, value in sorted(relation.items()) if key not in {"type", "id"}]
        if relation_id:
            args.insert(0, str(relation_id))
        lines.append(f"  {relation_type}({', '.join(_quote(value) for value in args)})")
    lines.append(f"  swos:payload({_quote(_payload_marker(document))})")
    lines.append("endDocument")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _serialize_trig(document: ProvDocument) -> bytes:
    lines = [
        f"@prefix prov: <{document.namespaces.get('prov', PROV_NAMESPACES['prov'])}> .",
        f"@prefix swos: <{document.namespaces.get('swos', PROV_NAMESPACES['swos'])}> .",
        f"@base <{document.base_iri}> .",
        f"<{document.base_iri}> {{",
    ]
    for identifier in sorted(document.entities):
        lines.append(f"  <{identifier}> a prov:Entity .")
    for identifier in sorted(document.activities):
        lines.append(f"  <{identifier}> a prov:Activity .")
    for identifier in sorted(document.agents):
        lines.append(f"  <{identifier}> a prov:Agent .")
    lines.append("}")
    lines.append(f"# swos-payload: {_payload_marker(document)}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def serialize_prov(document: ProvDocument, format: ProvFormat) -> bytes:
    _assert_format(format)
    if not isinstance(document, ProvDocument):
        raise ValueError("serialize_prov requires a ProvDocument")
    if format == "prov-json":
        return (
            json.dumps(
                _json_payload(document), sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            + "\n"
        ).encode("utf-8")
    if format == "prov-n":
        return _serialize_prov_n(document)
    return _serialize_trig(document)


def _parse_marker(data: bytes, marker: str) -> ProvDocument:
    pattern = marker if isinstance(marker, bytes) else marker.encode("ascii")
    match = re.search(pattern, data)
    if not match:
        raise ValueError("unsupported PROV syntax without a SWOS lossless payload")
    return _decode_marker(match.group(1).decode("ascii"))


def parse_prov(
    data: bytes, format: ProvFormat, limits: ResourceLimits | None = None
) -> ProvDocument:
    _assert_format(format)
    limits = limits or ResourceLimits()
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("PROV input must be bytes")
    limits.check_bytes(len(data))
    if format == "prov-json":
        payload = json.loads(bytes(data).decode("utf-8"))
        document = _from_json_payload(payload)
    elif format == "prov-n":
        document = _parse_marker(bytes(data), rb"swos:payload\(\"([A-Za-z0-9_-]+)\"\)")
    else:
        document = _parse_marker(bytes(data), rb"swos-payload:\s*([A-Za-z0-9_-]+)")
    limits.check_document(document)
    return document
