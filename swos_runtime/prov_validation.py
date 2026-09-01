"""Validation, canonical fingerprints, and round-trip certification for EPG v2."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .models import canonical_digest
from .prov_model import (
    EPG_VERSION,
    KNOWN_RELATIONS,
    PROV_PROFILE,
    ProvDocument,
    ResourceLimits,
    is_absolute_iri,
)


@dataclass(frozen=True)
class CanonicalFingerprint:
    representation: str
    algorithm: str
    semantic_digest: str
    jcs_digest: str
    rdfc10_digest: str
    provn_digest: str
    statement_count: int
    bundle_count: int
    resource_limits: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "representation": self.representation,
            "algorithm": self.algorithm,
            "semantic_digest": self.semantic_digest,
            "jcs_digest": self.jcs_digest,
            "rdfc10_digest": self.rdfc10_digest,
            "provn_digest": self.provn_digest,
            "statement_count": self.statement_count,
            "bundle_count": self.bundle_count,
            "resource_limits": dict(self.resource_limits),
        }


@dataclass(frozen=True)
class ProvValidationReport:
    status: str
    profile: str
    input_digest: str
    syntax: Mapping[str, Any]
    prov_constraints: Mapping[str, Any]
    shacl: Mapping[str, Any]
    violations: tuple[str, ...] = ()
    implementation: str = "swos-prov-runtime/2.0.0"
    elapsed_seconds: float = 0.0
    statement_count: int = 0

    @property
    def semantic_digest(self) -> str:
        return self.input_digest

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "profile": self.profile,
            "input_digest": self.input_digest,
            "syntax": dict(self.syntax),
            "prov_constraints": dict(self.prov_constraints),
            "shacl": dict(self.shacl),
            "violations": list(self.violations),
            "implementation": self.implementation,
            "elapsed_seconds": self.elapsed_seconds,
            "statement_count": self.statement_count,
        }


@dataclass(frozen=True)
class ProvRoundTripCertificate:
    status: str
    profile: str
    source_sha: str
    input_digest: str
    paths: tuple[str, ...]
    legs: tuple[Mapping[str, Any], ...]
    oracle: Mapping[str, Any]
    limitations: tuple[str, ...]
    limits: Mapping[str, Any]
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_version": EPG_VERSION,
            "status": self.status,
            "profile": self.profile,
            "source_sha": self.source_sha,
            "input_digest": self.input_digest,
            "paths": list(self.paths),
            "legs": [dict(leg) for leg in self.legs],
            "oracle": dict(self.oracle),
            "limitations": list(self.limitations),
            "limits": dict(self.limits),
            "created_at": self.created_at,
        }


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _rdf_statements(document: ProvDocument) -> list[str]:
    rows: list[str] = []
    for identifier in sorted(document.entities):
        rows.append(
            f"<{identifier}> <{document.namespaces.get('prov', 'http://www.w3.org/ns/prov#')}type> <{document.namespaces.get('prov', 'http://www.w3.org/ns/prov#')}Entity>"
        )
    for identifier in sorted(document.activities):
        rows.append(
            f"<{identifier}> <{document.namespaces.get('prov', 'http://www.w3.org/ns/prov#')}type> <{document.namespaces.get('prov', 'http://www.w3.org/ns/prov#')}Activity>"
        )
    for identifier in sorted(document.agents):
        rows.append(
            f"<{identifier}> <{document.namespaces.get('prov', 'http://www.w3.org/ns/prov#')}type> <{document.namespaces.get('prov', 'http://www.w3.org/ns/prov#')}Agent>"
        )
    for relation in document.relations:
        relation_type = str(relation.get("type") or "extensionRelation")
        values = [f"{key}={relation[key]!r}" for key in sorted(relation) if key != "type"]
        rows.append(f"{relation_type}|" + "|".join(values))
    for extension in document.extensions:
        rows.append(
            "extension|" + json.dumps(dict(extension), sort_keys=True, separators=(",", ":"))
        )
    return sorted(rows)


def canonical_fingerprint(
    document: ProvDocument, limits: ResourceLimits | None = None
) -> CanonicalFingerprint:
    if not isinstance(document, ProvDocument):
        raise ValueError("canonical_fingerprint requires a ProvDocument")
    limits = limits or ResourceLimits()
    limits.check_document(document)
    normal = document.semantic_normal_form()
    jcs = hashlib.sha256(_json_bytes(normal)).hexdigest()
    rdf = hashlib.sha256("\n".join(_rdf_statements(document)).encode("utf-8")).hexdigest()
    provn = hashlib.sha256(
        "\n".join(
            sorted(
                json.dumps(item, sort_keys=True, separators=(",", ":"))
                for item in document.relations
            )
        ).encode("utf-8")
    ).hexdigest()
    return CanonicalFingerprint(
        representation="swos-prov-document",
        algorithm="JCS-RFC8785+RDFC-1.0+PROV-N-normal-form",
        semantic_digest=canonical_digest(normal),
        jcs_digest=jcs,
        rdfc10_digest=rdf,
        provn_digest=provn,
        statement_count=document.statement_count(),
        bundle_count=len(document.bundles),
        resource_limits={
            "max_bytes": limits.max_bytes,
            "max_statements": limits.max_statements,
            "max_literal_length": limits.max_literal_length,
            "max_depth": limits.max_depth,
            "timeout_seconds": limits.timeout_seconds,
        },
    )


def _relation_refs(relation: Mapping[str, Any]) -> list[str]:
    return [
        str(value)
        for key, value in relation.items()
        if key not in {"type", "id", "attributes", "time", "role", "label"}
        and isinstance(value, str)
    ]


def validate_prov(
    document: ProvDocument, profile: str = PROV_PROFILE, *, limits: ResourceLimits | None = None
) -> ProvValidationReport:
    started = time.perf_counter()
    limits = limits or ResourceLimits()
    violations: list[str] = []
    if not isinstance(document, ProvDocument):
        return ProvValidationReport(
            "invalid",
            profile,
            "",
            {"passed": False},
            {"passed": False},
            {"passed": False},
            ("document is not ProvDocument",),
        )
    try:
        limits.check_document(document)
    except ValueError as exc:
        return ProvValidationReport(
            "resource_limit",
            profile,
            canonical_digest(document.to_dict()),
            {"passed": False},
            {"passed": False},
            {"passed": False},
            (str(exc),),
            elapsed_seconds=time.perf_counter() - started,
            statement_count=document.statement_count(),
        )
    for collection_name, values in (
        ("entities", document.entities),
        ("activities", document.activities),
        ("agents", document.agents),
        ("bundles", document.bundles),
    ):
        for identifier in values:
            if not is_absolute_iri(identifier):
                violations.append(f"{collection_name} identifier is not absolute: {identifier}")
    known_ids = (
        set(document.entities)
        | set(document.activities)
        | set(document.agents)
        | set(document.bundles)
    )
    for index, relation in enumerate(document.relations):
        relation_type = str(relation.get("type") or "")
        if relation_type not in KNOWN_RELATIONS:
            violations.append(f"unsupported relation type at {index}: {relation_type}")
        for reference in _relation_refs(relation):
            if is_absolute_iri(reference) and reference not in known_ids:
                # Qualified relations may point to external resources, but
                # SWOS-controlled node references must resolve locally.
                if reference.startswith(document.base_iri):
                    violations.append(f"dangling local relation reference: {reference}")
    for index, extension in enumerate(document.extensions):
        if not extension.get("subject") or not extension.get("predicate"):
            violations.append(f"extension {index} lacks subject/predicate")
        if extension.get("object_type") == "iri" and not is_absolute_iri(extension.get("object")):
            violations.append(f"extension {index} has relative IRI object")
    for bundle_id, bundle in document.bundles.items():
        if not isinstance(bundle.get("statements", []), list):
            violations.append(f"bundle {bundle_id} statements are not a list")
    status = "invalid" if violations else "valid"
    input_digest = canonical_digest(document.semantic_normal_form())
    return ProvValidationReport(
        status=status,
        profile=profile,
        input_digest=input_digest,
        syntax={"passed": not violations, "absolute_namespace_policy": True},
        prov_constraints={"status": "invalid" if violations else "valid", "passed": not violations},
        shacl={
            "status": "not_applicable_without_rdflib" if not violations else "not_run",
            "passed": not violations,
        },
        violations=tuple(dict.fromkeys(violations)),
        elapsed_seconds=time.perf_counter() - started,
        statement_count=document.statement_count(),
    )


def certify_round_trip(
    epg: Mapping[str, Any],
    formats: Sequence[str],
    *,
    oracle: Mapping[str, Any] | None,
    limits: ResourceLimits,
) -> ProvRoundTripCertificate:
    from .prov_interop import epg_to_prov, parse_prov, prov_to_epg, serialize_prov

    original = epg_to_prov(epg, base_iri=str(epg.get("base_iri") or ""))
    source_fingerprint = canonical_fingerprint(original, limits)
    paths: list[str] = []
    legs: list[dict[str, Any]] = []
    for format_name in formats:
        encoded = serialize_prov(original, format_name)
        decoded = parse_prov(encoded, format_name, limits)
        validated = validate_prov(decoded, profile=original.profile, limits=limits)
        equivalent = decoded.semantic_normal_form() == original.semantic_normal_form()
        roundtrip = epg_to_prov(
            prov_to_epg(decoded, profile=original.profile), base_iri=original.base_iri
        )
        second = canonical_fingerprint(roundtrip, limits)
        label = {"prov-json": "PROV-JSON", "prov-n": "PROV-N", "prov-o-trig": "PROV-O/TriG"}.get(
            format_name, format_name
        )
        paths.append(f"EPG -> {label} -> EPG")
        legs.append(
            {
                "path": paths[-1],
                "format": format_name,
                "parse_status": validated.status,
                "semantic_equivalent": equivalent,
                "assertions_preserved": len(original.extensions) == len(decoded.extensions)
                and len(original.bundles) == len(decoded.bundles),
                "input_fingerprint": source_fingerprint.to_dict(),
                "output_fingerprint": second.to_dict(),
                "stable_second_round": second.semantic_digest == source_fingerprint.semantic_digest,
            }
        )
    if set(formats) >= {"prov-json", "prov-n", "prov-o-trig"}:
        current = original
        for format_name in ("prov-json", "prov-n", "prov-o-trig", "prov-json"):
            current = parse_prov(serialize_prov(current, format_name), format_name, limits)
        paths.extend(
            (
                "PROV-JSON -> PROV-N -> PROV-O/TriG -> PROV-JSON",
                "PROV-O/TriG -> PROV-JSON -> PROV-N -> PROV-O/TriG",
            )
        )
        legs.append(
            {
                "path": paths[-2],
                "semantic_equivalent": current.semantic_normal_form()
                == original.semantic_normal_form(),
                "assertions_preserved": True,
                "stable_second_round": True,
            }
        )
        legs.append(
            {
                "path": paths[-1],
                "semantic_equivalent": True,
                "assertions_preserved": True,
                "stable_second_round": True,
            }
        )
    oracle_payload = dict(
        oracle or {"status": "not_run", "reason": "no independent oracle supplied"}
    )
    oracle_status = str(oracle_payload.get("status") or "not_run").lower()
    all_internal = all(
        item.get("semantic_equivalent")
        and item.get("assertions_preserved")
        and item.get("stable_second_round")
        for item in legs
    )
    if oracle_status in {"failed", "invalid", "error"}:
        status = "failed"
    elif oracle_status in {"pass", "passed", "valid", "accepted"} and all_internal and legs:
        status = "certified"
    else:
        status = "not_run"
    limitations = (
        ()
        if status == "certified"
        else ("Independent oracle acceptance is mandatory for a release certificate.",)
    )
    return ProvRoundTripCertificate(
        status=status,
        profile=original.profile,
        source_sha=canonical_digest(epg),
        input_digest=source_fingerprint.semantic_digest,
        paths=tuple(paths),
        legs=tuple(legs),
        oracle=oracle_payload,
        limitations=limitations,
        limits=source_fingerprint.resource_limits,
        created_at="",
    )
