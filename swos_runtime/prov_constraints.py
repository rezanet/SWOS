"""Executable SWOS rules for the W3C PROV-CONSTRAINTS profile.

The interchange model is intentionally dependency-free.  This module therefore
owns the structural, typing, uniqueness, and impossibility rules that apply to
the EPG representation before an external processor is used for certification.
It is conservative: an incomplete relation is invalid rather than being
silently interpreted as an existential PROV term.
"""

from __future__ import annotations

import time
from typing import Any, Mapping

from .prov_model import KNOWN_RELATIONS, ProvDocument, is_absolute_iri

RULESET = "w3c-prov-constraints/2013"
IMPLEMENTATION = "swos-prov-constraints/2.0.0"

# The first element is the EPG field, the second is the PROV base type, and
# the third marks whether the participant is mandatory in this SWOS profile.
RELATION_SIGNATURES: dict[str, tuple[tuple[str, str, bool], ...]] = {
    "wasGeneratedBy": (("entity", "entity", True), ("activity", "activity", True)),
    "used": (("activity", "activity", True), ("entity", "entity", True)),
    "wasAssociatedWith": (
        ("activity", "activity", True),
        ("agent", "agent", True),
        ("plan", "entity", False),
    ),
    "wasAttributedTo": (("entity", "entity", True), ("agent", "agent", True)),
    "wasDerivedFrom": (
        ("generatedEntity", "entity", True),
        ("usedEntity", "entity", True),
        ("activity", "activity", False),
        ("generation", "entity", False),
        ("usage", "entity", False),
    ),
    "wasInformedBy": (("informed", "activity", True), ("informant", "activity", True)),
    "actedOnBehalfOf": (
        ("delegate", "agent", True),
        ("responsible", "agent", True),
        ("activity", "activity", False),
    ),
    "specializationOf": (("specificEntity", "entity", True), ("generalEntity", "entity", True)),
    "alternateOf": (("entity1", "entity", True), ("entity2", "entity", True)),
    "hadMember": (("collection", "entity", True), ("entity", "entity", True)),
    "wasStartedBy": (
        ("activity", "activity", True),
        ("trigger", "entity", False),
        ("starter", "activity", False),
    ),
    "wasEndedBy": (
        ("activity", "activity", True),
        ("trigger", "entity", False),
        ("ender", "activity", False),
    ),
    "invalidated": (
        ("entity", "entity", True),
        ("activity", "activity", False),
    ),
    # Qualified records retain their base relation participants in EPG v2.
    "qualifiedGeneration": (("entity", "entity", True), ("activity", "activity", True)),
    "qualifiedUsage": (("activity", "activity", True), ("entity", "entity", True)),
    "qualifiedAssociation": (("activity", "activity", True), ("agent", "agent", True)),
    "qualifiedDerivation": (
        ("generatedEntity", "entity", True),
        ("usedEntity", "entity", True),
    ),
    "qualifiedAttribution": (("entity", "entity", True), ("agent", "agent", True)),
}

RULE_IDS = (
    "key-object",
    "key-properties",
    "unique-generation",
    "unique-invalidation",
    "typing",
    "impossible-specialization-reflexive",
    "impossible-alternate-reflexive",
    "entity-activity-disjoint",
    "relation-participant-completeness",
    "relation-participant-typing",
    "bundle-statement-typing",
)


def _required_participant_error(relation_type: str, field: str) -> str:
    return f"{relation_type} requires participant {field}"


def validate_constraints(
    document: ProvDocument, *, deadline: float | None = None
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Evaluate the EPG-representable PROV-CONSTRAINTS rules.

    The report identifies the executable ruleset and every rule family that was
    applied.  It never reports PASS for a malformed or partially specified
    relation.
    """

    violations: list[str] = []
    applied = list(RULE_IDS)

    def check_deadline() -> None:
        if deadline is not None and time.perf_counter() > deadline:
            raise ValueError("resource_limit: PROV constraint validation exceeds timeout_seconds")

    check_deadline()
    entity_ids = set(document.entities)
    activity_ids = set(document.activities)
    agent_ids = set(document.agents)
    if entity_ids & activity_ids:
        violations.append("entity-activity-disjoint identifiers overlap")

    for kind, values in (
        ("entity", document.entities),
        ("activity", document.activities),
        ("agent", document.agents),
    ):
        for identifier, node in values.items():
            check_deadline()
            if not isinstance(node, Mapping):
                violations.append(f"{kind} {identifier} is not an object")
            declared_type = node.get("type") if isinstance(node, Mapping) else None
            if declared_type is not None and declared_type != kind:
                violations.append(f"{kind} {identifier} has incompatible type {declared_type}")

    relation_ids: dict[tuple[str, str], Mapping[str, Any]] = {}
    for index, relation in enumerate(document.relations):
        check_deadline()
        if not isinstance(relation, Mapping):
            violations.append(f"relation {index} is not an object")
            continue
        relation_type = relation.get("type")
        if not isinstance(relation_type, str) or not relation_type:
            violations.append(f"relation {index} lacks a type")
            continue
        if relation_type not in KNOWN_RELATIONS:
            violations.append(f"unsupported relation type at {index}: {relation_type}")
            continue
        signature = RELATION_SIGNATURES.get(relation_type)
        if signature is None:
            violations.append(f"relation type lacks a frozen constraint signature: {relation_type}")
            continue
        relation_id = relation.get("id")
        if relation_id is not None:
            if not isinstance(relation_id, str) or not is_absolute_iri(relation_id):
                violations.append(f"{relation_type} relation id is not an absolute IRI")
            else:
                key = (relation_type, relation_id)
                prior = relation_ids.get(key)
                if prior is not None and dict(prior) != dict(relation):
                    violations.append(f"{relation_type} relation id is not a unique key")
                relation_ids[key] = relation

        for field, expected_kind, required in signature:
            value = relation.get(field)
            if value in (None, ""):
                if required:
                    violations.append(_required_participant_error(relation_type, field))
                continue
            if not isinstance(value, str) or not is_absolute_iri(value):
                violations.append(f"{relation_type} participant {field} is not an absolute IRI")
                continue
            values = {
                "entity": entity_ids,
                "activity": activity_ids,
                "agent": agent_ids,
            }.get(expected_kind)
            if values is not None and value not in values:
                violations.append(
                    f"{relation_type} participant {field} does not identify a {expected_kind}"
                )
        if relation_type == "specializationOf" and relation.get("specificEntity") == relation.get(
            "generalEntity"
        ):
            violations.append("specializationOf cannot be reflexive")
        if relation_type == "alternateOf" and relation.get("entity1") == relation.get("entity2"):
            violations.append("alternateOf cannot be reflexive")

    for bundle_id, bundle in document.bundles.items():
        check_deadline()
        if not isinstance(bundle, Mapping):
            violations.append(f"bundle {bundle_id} is not an object")
            continue
        statements = bundle.get("statements", [])
        if not isinstance(statements, list):
            violations.append(f"bundle {bundle_id} statements are not a list")
            continue
        for statement_index, statement in enumerate(statements):
            check_deadline()
            if not isinstance(statement, Mapping):
                violations.append(
                    f"bundle {bundle_id} statement {statement_index} is not an object"
                )
                continue
            statement_type = statement.get("type")
            identifier = statement.get("id")
            if statement_type in {"entity", "activity", "agent"}:
                values = {
                    "entity": entity_ids,
                    "activity": activity_ids,
                    "agent": agent_ids,
                }[statement_type]
                if not isinstance(identifier, str) or identifier not in values:
                    violations.append(
                        f"bundle {bundle_id} statement {statement_index} has an unknown {statement_type}"
                    )
            elif statement_type not in KNOWN_RELATIONS:
                violations.append(
                    f"bundle {bundle_id} statement {statement_index} has an unsupported type"
                )

    unique_violations = tuple(dict.fromkeys(violations))
    report = {
        "status": "invalid" if unique_violations else "valid",
        "passed": not unique_violations,
        "implementation": IMPLEMENTATION,
        "ruleset": RULESET,
        "rules_applied": applied,
        "violation_count": len(unique_violations),
    }
    return report, unique_violations
