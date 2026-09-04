"""Rights-aware, resumable preparation of unlabelled citation candidates.

This module deliberately does not share the final adjudicated-pair validator.  A
candidate is useful for annotation only while its human fields are empty and its
source approval is still explicitly pending.  Promotion into the immutable
``SOURCE-LICENCE-MANIFEST.json`` and final corpus remains a separate, human-owned
operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AcquisitionValidationError(ValueError):
    """Raised when a candidate source or annotation packet is unsafe to use."""


SUPPORTED_DISCIPLINES = (
    "art_history",
    "art_criticism",
    "engineering",
    "humanities",
    "interdisciplinary",
    "materials_science",
    "philosophy",
    "psychology",
    "technical_writing",
)

SOURCE_STATES = (
    "CANDIDATE",
    "ADMISSIBLE_PENDING_REVIEW",
    "REJECTED_RIGHTS",
    "REJECTED_CONTENT",
    "REJECTED_DUPLICATE",
    "REJECTED_UNRESOLVED_LICENCE",
)

ADMISSIBLE_LICENSES = {
    "CC-BY-4.0",
    "CC0-1.0",
    "PUBLIC-DOMAIN",
}

ALLOWED_USES = {
    "candidate_generation",
    "human_annotation",
    "provenance_audit",
}
REQUIRED_CANDIDATE_USES = {"candidate_generation", "human_annotation"}

_SOURCE_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "manifest_type",
        "status",
        "generated_at",
        "catalog_uri",
        "catalog_sha256",
        "acquisition",
        "semantic_split_policy",
        "sources",
    }
)
_SOURCE_RECORD_FIELDS = frozenset(
    {
        "source_id",
        "doi",
        "stable_uri",
        "exact_acquired_copy_uri",
        "canonical_source_family",
        "title",
        "authors",
        "publisher",
        "publication_date",
        "disciplines",
        "licence",
        "attribution",
        "acquired_at",
        "sha256",
        "allowed_uses",
        "third_party",
        "state",
        "approval",
        "rejection_reason",
        "semantic_split_default",
    }
)
_LICENCE_FIELDS = frozenset(
    {
        "spdx",
        "uri",
        "version",
        "article_rights_uri",
        "verification",
        "evidence_uri",
        "verification_basis",
    }
)
_THIRD_PARTY_FIELDS = frozenset({"status", "warning"})
_APPROVAL_FIELDS = frozenset({"status", "reviewer_id"})

SEMANTIC_POLICY_VERSION = "2.0.0"
TEMPORAL_CRITERIA_ID = "T070-TEMPORAL-LATER-YEAR-V1"
TEMPORAL_START_YEAR = 2020
TEMPORAL_DEFINITION = "publication_year >= 2020 and catalog_declared_held_out_domain is not true"

CANDIDATE_STRATA = (
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
)

STRATUM_DEFINITIONS = {
    "S1": "direct/complete candidate",
    "S2": "partial candidate",
    "S3": "same-topic/context candidate",
    "S4": "contradiction candidate",
    "S5": "hard negative candidate",
}

ADVERSARIAL_PATTERN_IDS = tuple(f"A{index:02d}" for index in range(1, 16))

ADVERSARIAL_PATTERN_DEFINITIONS = {
    "A04": "some to all / quantifier scope",
    "A05": "may to does / modality strength",
    "A06": "association to causation",
    "A07": "local to whole / scope inflation",
    "A08": "signal to identity / proxy inflation",
    "A09": "method to object / material confusion",
    "A10": "non-detection to absence",
    "A11": "historical to current",
    "A12": "range inflation",
    "A13": "citation laundering",
    "A14": "summary stronger than passage",
    "A15": "neighboring mechanism",
}

_PATTERN_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("A04", ("some", "all", "every", "each", "only", "most")),
    ("A05", ("may", "might", "could", "can", "does", "will", "must")),
    ("A06", ("associat", "correlat", "linked", "caus", "result", "lead")),
    ("A07", ("local", "regional", "whole", "overall", "global", "system")),
    ("A08", ("indicat", "suggest", "proxy", "signal", "identif", "confirm")),
    ("A09", ("method", "technique", "measure", "object", "material", "specimen")),
    ("A10", ("no ", "not ", "absence", "without", "undetect")),
    ("A11", ("histor", "past", "ancient", "current", "today", "modern")),
    ("A12", ("range", "approximately", "estimate", "percent", "%")),
    ("A13", ("launder", "citation", "attributed", "reported")),
    ("A14", ("overview", "summary", "conclud", "finding", "result")),
    ("A15", ("mechanism", "pathway", "process", "technique")),
)

SEMANTIC_PARTITIONS = ("in_domain", "temporal", "ood")

DEFAULT_SEMANTIC_POLICY: dict[str, Any] = {
    "version": SEMANTIC_POLICY_VERSION,
    "temporal": {
        "criteria_id": TEMPORAL_CRITERIA_ID,
        "definition": TEMPORAL_DEFINITION,
        "start_year": TEMPORAL_START_YEAR,
    },
    "ood": {
        "criteria_id": "T070-OOD-DOMAIN-V1",
        "definition": "catalog_declared_held_out_domain is true",
    },
}

_IN_DOMAIN_CRITERIA_ID = "T070-IN-DOMAIN-V1"
_TEXT_KEYS = {
    "abstract",
    "body",
    "bodytext",
    "body_text",
    "content",
    "fulltext",
    "full_text",
    "paragraph",
    "paragraphs",
    "section",
    "sections",
    "sentence",
    "sentences",
    "text",
    "title",
}
_NEGATION_MARKERS = (
    " not ",
    " no ",
    " never ",
    " failed ",
    " fails ",
    " unlike ",
    " however ",
    " absence ",
    " without ",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _reject_undeclared_fields(
    value: Mapping[str, Any], allowed: frozenset[str], *, label: str
) -> None:
    undeclared = sorted(str(name) for name in value if name not in allowed)
    if undeclared:
        raise AcquisitionValidationError(
            f"{label} contains undeclared fields: " + ", ".join(undeclared)
        )


def _require_declared_fields(
    value: Mapping[str, Any], required: frozenset[str], *, label: str
) -> None:
    missing = sorted(str(name) for name in required if name not in value)
    if missing:
        raise AcquisitionValidationError(
            f"{label} lacks required fields: " + ", ".join(missing)
        )


def _normalise_license(value: Any) -> str:
    raw = str(value or "").strip().upper().replace(" ", "-").replace("_", "-")
    raw = raw.replace("CREATIVE-COMMONS-", "CC-")
    aliases = {
        "CC-BY": "CC-BY-4.0",
        "CC-BY-4": "CC-BY-4.0",
        "CC-BY-4.0-INTERNATIONAL": "CC-BY-4.0",
        "CC-BY-SA": "CC-BY-SA",
        "CC0": "CC0-1.0",
        "CC0-1": "CC0-1.0",
        "CC0-1.0": "CC0-1.0",
        "PUBLIC-DOMAIN": "PUBLIC-DOMAIN",
        "PUBLICDOMAIN": "PUBLIC-DOMAIN",
        "PD": "PUBLIC-DOMAIN",
        "UNKNOWN": "UNKNOWN",
        "OTHER-OA": "OTHER-OA",
    }
    return aliases.get(raw, raw or "UNKNOWN")


def canonical_source_family(source: Mapping[str, Any]) -> str:
    """Return a stable work-family identity, independent of URL decoration."""

    explicit = str(source.get("canonical_source_family") or "").strip().lower()
    if explicit:
        return explicit
    doi = str(source.get("doi") or "").strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi).strip().rstrip(".")
    if doi:
        return f"doi:{doi}"
    uri = str(source.get("stable_uri") or source.get("content_uri") or "").strip()
    parsed = urllib.parse.urlsplit(uri)
    if parsed.scheme and parsed.netloc:
        path = re.sub(r"/+", "/", parsed.path).rstrip("/") or "/"
        return f"uri:{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    return f"uri:{uri.lower().rstrip('/')}"


def _validate_semantic_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, Mapping) or policy.get("version") != SEMANTIC_POLICY_VERSION:
        raise AcquisitionValidationError(
            f"semantic split policy must be version {SEMANTIC_POLICY_VERSION}"
        )
    _reject_undeclared_fields(
        policy,
        frozenset({"version", "temporal", "ood"}),
        label="semantic split policy",
    )
    temporal = policy.get("temporal")
    ood = policy.get("ood")
    if not isinstance(temporal, Mapping) or not isinstance(ood, Mapping):
        raise AcquisitionValidationError("semantic split policy requires temporal and ood criteria")
    _reject_undeclared_fields(
        temporal,
        frozenset({"criteria_id", "definition", "start_year"}),
        label="temporal split policy",
    )
    _reject_undeclared_fields(
        ood,
        frozenset({"criteria_id", "definition"}),
        label="OOD split policy",
    )
    if temporal.get("criteria_id") != TEMPORAL_CRITERIA_ID:
        raise AcquisitionValidationError("temporal split criteria ID is not predeclared")
    if temporal.get("definition") != TEMPORAL_DEFINITION:
        raise AcquisitionValidationError("temporal split definition is not predeclared")
    start_year = temporal.get("start_year")
    if (
        isinstance(start_year, bool)
        or not isinstance(start_year, int)
        or start_year != TEMPORAL_START_YEAR
    ):
        raise AcquisitionValidationError(
            "temporal split start year must be the frozen 2020 later-window boundary"
        )
    if ood.get("criteria_id") != DEFAULT_SEMANTIC_POLICY["ood"]["criteria_id"]:
        raise AcquisitionValidationError("OOD split criteria ID is not predeclared")
    if ood.get("definition") != DEFAULT_SEMANTIC_POLICY["ood"]["definition"]:
        raise AcquisitionValidationError("OOD split definition is not predeclared")
    return {
        "version": SEMANTIC_POLICY_VERSION,
        "temporal": {
            "criteria_id": str(temporal["criteria_id"]),
            "definition": str(temporal["definition"]),
            "start_year": int(start_year),
        },
        "ood": {
            "criteria_id": str(ood["criteria_id"]),
            "definition": str(ood["definition"]),
        },
    }


def _validate_semantic_assignment(
    value: Any, *, policy: Mapping[str, Any] = DEFAULT_SEMANTIC_POLICY
) -> dict[str, Any]:
    policy = _validate_semantic_policy(policy)
    if not isinstance(value, Mapping):
        raise AcquisitionValidationError("candidate lacks a semantic temporal/OOD assignment")
    allowed_fields = {
        "partition",
        "criteria_id",
        "publication_year",
        "start_year",
        "catalog_declared_held_out_domain",
        "domain_id",
    }
    undeclared = sorted(str(name) for name in value if name not in allowed_fields)
    if undeclared:
        raise AcquisitionValidationError(
            "candidate semantic assignment contains undeclared fields: " + ", ".join(undeclared)
        )
    partition = value.get("partition")
    criteria_id = value.get("criteria_id")
    if partition not in SEMANTIC_PARTITIONS or not _nonempty(criteria_id):
        raise AcquisitionValidationError("candidate semantic assignment is incomplete")
    if "bucket" in value or "hash" in value or "hash_bucket" in value:
        raise AcquisitionValidationError("hash buckets cannot define temporal or OOD membership")
    result = dict(value)
    if partition == "temporal":
        if criteria_id != policy["temporal"]["criteria_id"]:
            raise AcquisitionValidationError(
                "temporal candidate does not use the declared criteria"
            )
        year = value.get("publication_year")
        start_year = value.get("start_year")
        if (
            isinstance(year, bool)
            or not isinstance(year, int)
            or year < policy["temporal"]["start_year"]
        ):
            raise AcquisitionValidationError(
                "temporal candidate lacks a publication year in the later window"
            )
        if start_year != policy["temporal"]["start_year"]:
            raise AcquisitionValidationError("temporal candidate start year does not match policy")
        if value.get("catalog_declared_held_out_domain") is True:
            raise AcquisitionValidationError("OOD candidate cannot be marked temporal")
    elif partition == "ood":
        if criteria_id != policy["ood"]["criteria_id"]:
            raise AcquisitionValidationError("OOD candidate does not use the declared criteria")
        if value.get("catalog_declared_held_out_domain") is not True:
            raise AcquisitionValidationError(
                "OOD candidate lacks catalog-declared held-out-domain evidence"
            )
        if not _nonempty(value.get("domain_id")):
            raise AcquisitionValidationError("OOD candidate lacks a named held-out domain")
    elif criteria_id != _IN_DOMAIN_CRITERIA_ID:
        raise AcquisitionValidationError("in-domain candidate does not use the declared criteria")
    if partition == "in_domain":
        year = value.get("publication_year")
        if (
            isinstance(year, int)
            and not isinstance(year, bool)
            and year >= policy["temporal"]["start_year"]
        ):
            raise AcquisitionValidationError("later-period candidate cannot be marked in-domain")
        if value.get("catalog_declared_held_out_domain") is True:
            raise AcquisitionValidationError("held-out-domain candidate cannot be marked in-domain")
    result["partition"] = str(partition)
    result["criteria_id"] = str(criteria_id)
    return result


def validate_source_candidate_manifest(
    manifest: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Validate pre-annotation source records without granting approval."""

    if not isinstance(manifest, Mapping):
        raise AcquisitionValidationError("source candidate manifest has an unsupported schema")
    _reject_undeclared_fields(manifest, _SOURCE_MANIFEST_FIELDS, label="source candidate manifest")
    if manifest.get("schema_version") != "2.0.0":
        raise AcquisitionValidationError("source candidate manifest has an unsupported schema")
    if manifest.get("manifest_type") != "citation_support_source_candidates":
        raise AcquisitionValidationError("source candidate manifest has an unsupported type")
    if manifest.get("status") not in {"ACQUISITION_INCOMPLETE", "READY_FOR_HUMAN_ANNOTATION"}:
        raise AcquisitionValidationError("source candidate manifest status is invalid")
    if not _nonempty(manifest.get("generated_at")):
        raise AcquisitionValidationError("source candidate manifest lacks generation time")
    policy = _validate_semantic_policy(manifest.get("semantic_split_policy"))
    sources = manifest.get("sources")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        raise AcquisitionValidationError("source candidate manifest sources must be a list")

    indexed: dict[str, dict[str, Any]] = {}
    families: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, Mapping):
            raise AcquisitionValidationError("source candidate record must be an object")
        _reject_undeclared_fields(source, _SOURCE_RECORD_FIELDS, label="source candidate record")
        source_id = str(source.get("source_id") or "").strip()
        if not source_id or source_id in indexed:
            raise AcquisitionValidationError("source candidate IDs must be non-empty and unique")
        required = (
            "stable_uri",
            "exact_acquired_copy_uri",
            "canonical_source_family",
            "title",
            "authors",
            "publisher",
            "publication_date",
            "disciplines",
            "licence",
            "attribution",
            "acquired_at",
            "allowed_uses",
            "third_party",
            "state",
            "approval",
            "rejection_reason",
            "doi",
            "sha256",
        )
        missing = [name for name in required if name not in source]
        if missing:
            raise AcquisitionValidationError(f"source {source_id} lacks " + ", ".join(missing))
        state = source.get("state")
        if state not in SOURCE_STATES:
            raise AcquisitionValidationError(f"source {source_id} has an invalid state")
        if not _nonempty(source.get("stable_uri")) or not _nonempty(
            source.get("canonical_source_family")
        ):
            raise AcquisitionValidationError(f"source {source_id} lacks stable identity")
        if not _nonempty(source.get("title")) or not _nonempty(source.get("publisher")):
            raise AcquisitionValidationError(f"source {source_id} lacks bibliographic metadata")
        authors = source.get("authors")
        disciplines = source.get("disciplines")
        authors_valid = (
            isinstance(authors, Sequence)
            and not isinstance(authors, (str, bytes))
            and all(_nonempty(item) for item in authors)
        )
        if not authors_valid or (
            state in {"CANDIDATE", "ADMISSIBLE_PENDING_REVIEW"} and not authors
        ):
            raise AcquisitionValidationError(f"source {source_id} authors are invalid")
        if (
            not isinstance(disciplines, Sequence)
            or isinstance(disciplines, (str, bytes))
            or not disciplines
            or not all(str(item) in SUPPORTED_DISCIPLINES for item in disciplines)
        ):
            raise AcquisitionValidationError(f"source {source_id} discipline mapping is invalid")
        licence = source.get("licence")
        if not isinstance(licence, Mapping):
            raise AcquisitionValidationError(f"source {source_id} licence record is invalid")
        _reject_undeclared_fields(licence, _LICENCE_FIELDS, label=f"source {source_id} licence")
        _require_declared_fields(
            licence,
            frozenset({"spdx", "uri", "version", "article_rights_uri", "verification"}),
            label=f"source {source_id} licence",
        )
        for field in ("spdx", "uri", "version", "verification"):
            if not _nonempty(licence.get(field)):
                raise AcquisitionValidationError(f"source {source_id} licence lacks {field}")
        spdx = _normalise_license(licence.get("spdx"))
        if spdx != licence.get("spdx"):
            raise AcquisitionValidationError(
                f"source {source_id} licence identifier is not canonical"
            )
        allowed = source.get("allowed_uses")
        if (
            not isinstance(allowed, Sequence)
            or isinstance(allowed, (str, bytes))
            or any(str(item) not in ALLOWED_USES for item in allowed)
            or len(set(map(str, allowed))) != len(allowed)
        ):
            raise AcquisitionValidationError(f"source {source_id} allowed uses are invalid")
        third_party = source.get("third_party")
        if not isinstance(third_party, Mapping) or third_party.get("status") not in {
            "clear",
            "warning",
            "unknown",
        }:
            raise AcquisitionValidationError(f"source {source_id} third-party status is invalid")
        _reject_undeclared_fields(
            third_party,
            _THIRD_PARTY_FIELDS,
            label=f"source {source_id} third-party record",
        )
        _require_declared_fields(
            third_party,
            frozenset({"status", "warning"}),
            label=f"source {source_id} third-party record",
        )
        if not _nonempty(third_party.get("warning")):
            raise AcquisitionValidationError(f"source {source_id} third-party warning is missing")
        approval = source.get("approval")
        if not isinstance(approval, Mapping) or approval.get("status") not in {
            "pending",
            "not_requested",
        }:
            raise AcquisitionValidationError(f"source {source_id} approval state is invalid")
        _reject_undeclared_fields(
            approval,
            _APPROVAL_FIELDS,
            label=f"source {source_id} approval record",
        )
        _require_declared_fields(
            approval,
            frozenset({"status", "reviewer_id"}),
            label=f"source {source_id} approval record",
        )
        if approval.get("reviewer_id") not in {None, ""}:
            raise AcquisitionValidationError(
                f"source {source_id} cannot record an approval reviewer"
            )
        rejection_reason = source.get("rejection_reason")
        accepted = state in {"CANDIDATE", "ADMISSIBLE_PENDING_REVIEW"}
        if accepted:
            if not _nonempty(source.get("attribution")):
                raise AcquisitionValidationError(f"source {source_id} attribution is missing")
            if spdx not in ADMISSIBLE_LICENSES:
                raise AcquisitionValidationError(
                    f"source {source_id} uses a non-admissible licence"
                )
            if not _nonempty(licence.get("article_rights_uri")):
                raise AcquisitionValidationError(
                    f"source {source_id} licence lacks article_rights_uri"
                )
            if licence.get("verification") != "article_level_verified":
                raise AcquisitionValidationError(
                    f"source {source_id} lacks article-level rights verification"
                )
            if not _nonempty(source.get("exact_acquired_copy_uri")) or not _is_sha256(
                source.get("sha256")
            ):
                raise AcquisitionValidationError(f"source {source_id} lacks an acquired-copy hash")
            if not allowed:
                raise AcquisitionValidationError(
                    f"source {source_id} has no permitted candidate use"
                )
            if not REQUIRED_CANDIDATE_USES.issubset(set(map(str, allowed))):
                raise AcquisitionValidationError(
                    f"source {source_id} lacks candidate-generation and human-annotation uses"
                )
            if approval.get("status") != "pending":
                raise AcquisitionValidationError(f"source {source_id} must remain pending review")
            if rejection_reason not in {None, ""}:
                raise AcquisitionValidationError(
                    f"source {source_id} cannot have a rejection reason"
                )
        else:
            if approval.get("status") != "not_requested":
                raise AcquisitionValidationError(f"rejected source {source_id} cannot be approved")
            if not _nonempty(rejection_reason):
                raise AcquisitionValidationError(
                    f"rejected source {source_id} lacks a rejection reason"
                )
            if source.get("sha256") is not None and not _is_sha256(source.get("sha256")):
                raise AcquisitionValidationError(
                    f"source {source_id} rejected record has an invalid hash"
                )
        semantic_split_default = source.get("semantic_split_default")
        if accepted and not isinstance(semantic_split_default, Mapping):
            raise AcquisitionValidationError(
                f"source {source_id} lacks a declared semantic_split_default"
            )
        if semantic_split_default is not None:
            _validate_semantic_assignment(semantic_split_default, policy=policy)
            expected_assignment = _source_semantic_assignment(source, policy)
            if dict(semantic_split_default) != expected_assignment:
                raise AcquisitionValidationError(
                    f"source {source_id} semantic assignment does not match source metadata"
                )
        family = str(source.get("canonical_source_family")).strip().lower()
        if family in families and state in {"CANDIDATE", "ADMISSIBLE_PENDING_REVIEW"}:
            raise AcquisitionValidationError(
                f"source family {family} appears more than once among admissible candidates"
            )
        if state in {"CANDIDATE", "ADMISSIBLE_PENDING_REVIEW"}:
            families[family] = source_id
        indexed[source_id] = dict(source)
        indexed[source_id]["licence"] = dict(licence)
        indexed[source_id]["semantic_split_policy"] = policy
    return indexed


def validate_unlabelled_candidate_pair(
    row: Mapping[str, Any], *, policy: Mapping[str, Any] = DEFAULT_SEMANTIC_POLICY
) -> None:
    """Validate an annotation packet while refusing any human answer."""

    if not isinstance(row, Mapping):
        raise AcquisitionValidationError("candidate packet must be an object")
    if "label" in row or "retrieval_intent" in row or "relation" in row:
        raise AcquisitionValidationError(
            "unlabelled packet exposes a forbidden label or retrieval intent"
        )
    required = (
        "schema_version",
        "packet_type",
        "packet_id",
        "pair_id",
        "claim_family_id",
        "group_id",
        "discipline",
        "claim_origin",
        "candidate_claim",
        "exact_quote",
        "context",
        "source_id",
        "source_uri",
        "acquired_copy_uri",
        "source_digest",
        "licence",
        "attribution",
        "acquisition_stratum",
        "candidate_pattern_id",
        "pattern_basis",
        "semantic_split",
        "annotations",
        "adjudication",
    )
    undeclared = sorted(str(name) for name in row if name not in required)
    if undeclared:
        raise AcquisitionValidationError(
            "candidate packet contains undeclared top-level fields: " + ", ".join(undeclared)
        )
    missing = [
        name
        for name in required
        if not _nonempty(row.get(name))
        and name not in {"annotations", "adjudication", "semantic_split"}
    ]
    if missing:
        raise AcquisitionValidationError("candidate packet lacks " + ", ".join(missing))
    if (
        row.get("schema_version") != "2.0.0"
        or row.get("packet_type") != "citation_support_unlabelled_annotation"
    ):
        raise AcquisitionValidationError("candidate packet schema or type is unsupported")
    if row.get("discipline") not in SUPPORTED_DISCIPLINES:
        raise AcquisitionValidationError("candidate packet discipline is not supported")
    if row.get("claim_origin") != "source-authored-sentence":
        raise AcquisitionValidationError("candidate claim origin must remain source-authored")
    if row.get("acquisition_stratum") not in CANDIDATE_STRATA:
        raise AcquisitionValidationError("candidate packet acquisition stratum is invalid")
    if row.get("candidate_pattern_id") not in ADVERSARIAL_PATTERN_IDS:
        raise AcquisitionValidationError("candidate packet pattern ID is invalid")
    if row.get("pattern_basis") not in {
        "stratum_defined",
        "lexical_heuristic",
        "fallback_pending_human_review",
    }:
        raise AcquisitionValidationError("candidate packet pattern basis is invalid")
    if row.get("licence") not in ADMISSIBLE_LICENSES:
        raise AcquisitionValidationError("candidate packet licence is not admissible")
    if not _is_sha256(row.get("source_digest")):
        raise AcquisitionValidationError("candidate packet source digest is not SHA-256")
    _validate_semantic_assignment(row.get("semantic_split"), policy=policy)
    annotations = row.get("annotations")
    if (
        not isinstance(annotations, Sequence)
        or isinstance(annotations, (str, bytes))
        or len(annotations) != 2
    ):
        raise AcquisitionValidationError("candidate packet must reserve two annotation fields")
    for item in annotations:
        if not isinstance(item, Mapping):
            raise AcquisitionValidationError("candidate annotation field must be an object")
        if set(item) != {"annotator_id", "label", "rationale"}:
            raise AcquisitionValidationError(
                "candidate annotation field must contain exactly the reserved keys"
            )
        if (
            item.get("annotator_id") is not None
            or item.get("label") is not None
            or item.get("rationale") is not None
        ):
            raise AcquisitionValidationError("candidate annotation fields must remain blank")
    adjudication = row.get("adjudication")
    if not isinstance(adjudication, Mapping) or set(adjudication) != {
        "status",
        "adjudicator_id",
        "label",
        "rationale",
    }:
        raise AcquisitionValidationError(
            "candidate adjudication field must contain exactly the reserved keys"
        )
    if (
        adjudication.get("status") != "pending"
        or adjudication.get("adjudicator_id") is not None
        or adjudication.get("label") is not None
        or adjudication.get("rationale") is not None
    ):
        raise AcquisitionValidationError("candidate adjudication fields must remain blank")


def validate_candidate_source_binding(
    row: Mapping[str, Any], sources: Mapping[str, Mapping[str, Any]]
) -> None:
    """Bind every packet to one pending source record and its exact copy."""

    source_id = str(row.get("source_id") or "").strip()
    source = sources.get(source_id)
    if source is None or source.get("state") not in {"CANDIDATE", "ADMISSIBLE_PENDING_REVIEW"}:
        raise AcquisitionValidationError(
            f"candidate {row.get('pair_id', '<unknown>')} lacks a pending source"
        )
    comparisons = (
        ("source_uri", source.get("stable_uri")),
        ("acquired_copy_uri", source.get("exact_acquired_copy_uri")),
        ("source_digest", source.get("sha256")),
        ("attribution", source.get("attribution")),
    )
    for field, expected in comparisons:
        if str(row.get(field) or "") != str(expected or ""):
            raise AcquisitionValidationError(
                f"candidate {row.get('pair_id', '<unknown>')} source binding mismatches {field}"
            )
    if row.get("licence") != source.get("licence", {}).get("spdx"):
        raise AcquisitionValidationError(
            f"candidate {row.get('pair_id', '<unknown>')} licence binding mismatches"
        )
    if row.get("discipline") not in source.get("disciplines", []):
        raise AcquisitionValidationError(
            f"candidate {row.get('pair_id', '<unknown>')} discipline binding mismatches"
        )
    policy = source.get("semantic_split_policy", DEFAULT_SEMANTIC_POLICY)
    declared_assignment = source.get("semantic_split_default")
    if not isinstance(declared_assignment, Mapping):
        raise AcquisitionValidationError(
            f"candidate {row.get('pair_id', '<unknown>')} source lacks a semantic split binding"
        )
    expected_assignment = _source_semantic_assignment(source, policy)
    if dict(declared_assignment) != expected_assignment:
        raise AcquisitionValidationError(
            f"candidate {row.get('pair_id', '<unknown>')} source split metadata mismatches"
        )
    actual_assignment = _validate_semantic_assignment(row.get("semantic_split"), policy=policy)
    if actual_assignment != expected_assignment:
        raise AcquisitionValidationError(
            f"candidate {row.get('pair_id', '<unknown>')} semantic split binding mismatches"
        )


def _semantic_group_partition(
    rows: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]
) -> dict[str, tuple[str, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        validate_unlabelled_candidate_pair(row, policy=policy)
        groups[str(row["group_id"])].append(dict(row))
    result: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    for group_id, values in groups.items():
        partitions = {
            _validate_semantic_assignment(row["semantic_split"], policy=policy)["partition"]
            for row in values
        }
        if len(partitions) != 1:
            raise AcquisitionValidationError(f"group {group_id} mixes semantic split partitions")
        result[group_id] = (next(iter(partitions)), values)
    return result


def semantic_grouped_split(
    rows: Sequence[Mapping[str, Any]],
    *,
    policy: Mapping[str, Any] = DEFAULT_SEMANTIC_POLICY,
    seed: int = 0,
    proportions: Mapping[str, float] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Assign semantic temporal/OOD groups first, then hash only in-domain groups."""

    policy = _validate_semantic_policy(policy)
    groups = _semantic_group_partition(rows, policy)
    source_partitions: dict[str, set[str]] = defaultdict(set)
    claim_partitions: dict[str, set[str]] = defaultdict(set)
    for partition, values in groups.values():
        partition = _validate_semantic_assignment(values[0]["semantic_split"], policy=policy)[
            "partition"
        ]
        for row in values:
            source_partitions[str(row["source_id"])].add(partition)
            claim_partitions[str(row["claim_family_id"])].add(partition)
    for source_id, partitions in source_partitions.items():
        if len(partitions) > 1:
            raise AcquisitionValidationError(
                f"source {source_id} crosses semantic split partitions"
            )
    for claim_family_id, partitions in claim_partitions.items():
        if len(partitions) > 1:
            raise AcquisitionValidationError(
                f"claim family {claim_family_id} crosses semantic split partitions"
            )
    # Keep every source family together in the final train/calibration/locked-test
    # allocation as well. A source may contribute several claim families; those
    # groups form one deterministic assignment unit rather than being allowed to
    # leak across in-domain partitions.
    parent = {group_id: group_id for group_id in groups}

    def find(group_id: str) -> str:
        while parent[group_id] != group_id:
            parent[group_id] = parent[parent[group_id]]
            group_id = parent[group_id]
        return group_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    owners: dict[tuple[str, str], str] = {}
    for group_id, (_, values) in groups.items():
        for row in values:
            for key in (
                ("source", str(row["source_id"])),
                ("claim", str(row["claim_family_id"])),
            ):
                owner = owners.get(key)
                if owner is None:
                    owners[key] = group_id
                else:
                    union(group_id, owner)
    units: dict[str, tuple[str, list[dict[str, Any]], list[str]]] = {}
    for group_id, (partition, values) in groups.items():
        root = find(group_id)
        if root not in units:
            units[root] = (partition, [], [])
        unit_partition, unit_values, unit_groups = units[root]
        if unit_partition != partition:
            raise AcquisitionValidationError(
                f"canonical source/claim unit {root} crosses semantic split partitions"
            )
        unit_values.extend(values)
        unit_groups.append(group_id)
    names = ("train", "calibration", "locked_test", "temporal", "ood")
    raw = dict(proportions or {"train": 0.7, "calibration": 0.15, "locked_test": 0.15})
    if set(raw) - set(names) or not {"train", "calibration", "locked_test"}.issubset(raw):
        raise AcquisitionValidationError(
            "semantic split proportions must name in-domain partitions"
        )
    in_domain_names = ("train", "calibration", "locked_test")
    weights: dict[str, float] = {}
    for name in in_domain_names:
        value = raw[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or value <= 0
        ):
            raise AcquisitionValidationError(
                "semantic split proportions must be positive finite numbers"
            )
        weights[name] = float(value)
    result: dict[str, list[dict[str, Any]]] = {name: [] for name in names}
    special_units = sorted(
        (unit for unit, (partition, _, _) in units.items() if partition in {"temporal", "ood"}),
        key=lambda unit: min(units[unit][2]),
    )
    in_domain_units = sorted(
        (unit for unit, (partition, _, _) in units.items() if partition == "in_domain"),
        key=lambda unit: hashlib.sha256(f"{seed}:{min(units[unit][2])}".encode()).hexdigest(),
    )
    ordered = special_units + in_domain_units
    totals = {name: 0.0 for name in in_domain_names}
    target = {name: weights[name] for name in in_domain_names}
    for unit_id in ordered:
        partition, values, _ = units[unit_id]
        if partition in {"temporal", "ood"}:
            result[partition].extend(values)
            continue
        chosen = min(
            in_domain_names,
            key=lambda name: (totals[name] / target[name], in_domain_names.index(name)),
        )
        result[chosen].extend(values)
        totals[chosen] += len(values)
    source_locations: dict[str, set[str]] = defaultdict(set)
    claim_locations: dict[str, set[str]] = defaultdict(set)
    for split, values in result.items():
        for row in values:
            source_locations[str(row["source_id"])].add(split)
            claim_locations[str(row["claim_family_id"])].add(split)
    if any(len(locations) > 1 for locations in source_locations.values()):
        raise AcquisitionValidationError("source family crosses final semantic partitions")
    if any(len(locations) > 1 for locations in claim_locations.values()):
        raise AcquisitionValidationError("claim family crosses final semantic partitions")
    for values in result.values():
        values.sort(key=lambda row: str(row["pair_id"]))
    return result


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _content_path(uri: str) -> Path | None:
    if re.match(r"^[A-Za-z]:[\\/]", uri):
        return Path(uri).resolve()
    parsed = urllib.parse.urlsplit(uri)
    if parsed.scheme == "file":
        return Path(urllib.request.url2pathname(urllib.parse.unquote(parsed.path))).resolve()
    if not parsed.scheme:
        return Path(uri).expanduser().resolve()
    return None


def _copy_content(uri: str, target: Path, *, max_bytes: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    try:
        local = _content_path(uri)
        if local is not None:
            if not local.is_file():
                raise OSError(f"content file is missing: {local}")
            if local.stat().st_size > max_bytes:
                raise OSError(f"content exceeds resource limit: {max_bytes} bytes")
            with local.open("rb") as source, temporary.open("wb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
        else:
            request = urllib.request.Request(
                uri,
                headers={"User-Agent": "SWOS-T070-citation-acquisition/1.0"},
            )
            with urllib.request.urlopen(request, timeout=90) as source:
                length = source.headers.get("Content-Length")
                if length and int(length) > max_bytes:
                    raise OSError(f"content exceeds resource limit: {max_bytes} bytes")
                count = 0
                with temporary.open("wb") as destination:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        count += len(block)
                        if count > max_bytes:
                            raise OSError(f"content exceeds resource limit: {max_bytes} bytes")
                        destination.write(block)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _cached_source_is_current(
    content_uri: str,
    target: Path,
    cached: Mapping[str, Any],
    entry: Mapping[str, Any],
    *,
    max_bytes: int,
) -> bool:
    """Use a cached copy only when its source identity is still evidenced."""

    cached_digest = str(cached.get("sha256") or "").lower()
    if not target.is_file() or not _is_sha256(cached_digest):
        return False
    local = _content_path(content_uri)
    if local is not None:
        if not local.is_file():
            raise OSError(f"content file is missing: {local}")
        if local.stat().st_size > max_bytes:
            raise OSError(f"content exceeds resource limit: {max_bytes} bytes")
        return _sha256_file(local) == cached_digest

    # A remote URI is only reusable when the catalog has pinned its bytes.
    # Otherwise acquisition must fetch the current representation again.
    expected = entry.get("expected_sha256")
    return _is_sha256(expected) and str(expected).lower() == cached_digest


def _read_catalog(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, Mapping) or payload.get("schema_version") != "2.0.0":
        raise AcquisitionValidationError("source catalog must be a version 2.0.0 object")
    if payload.get("catalog_type") != "citation_source_candidate_catalog":
        raise AcquisitionValidationError("source catalog type is unsupported")
    sources = payload.get("sources")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        raise AcquisitionValidationError("source catalog sources must be a list")
    return dict(payload), _sha256_bytes(raw)


def _read_text_content(path: Path) -> str:
    raw = path.read_bytes()
    stripped = raw.lstrip()
    if path.suffix.lower() in {".json", ".jsonl"} or stripped[:1] in {b"{", b"["}:
        try:
            payload = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None
        if payload is not None:
            chunks: list[str] = []

            def collect(value: Any, *, selected: bool = False) -> None:
                if isinstance(value, Mapping):
                    for key, child in value.items():
                        key_name = re.sub(r"[^a-z0-9_]", "", str(key).lower())
                        collect(child, selected=selected or key_name in _TEXT_KEYS)
                elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                    for child in value:
                        collect(child, selected=selected)
                elif isinstance(value, str) and selected and value.strip():
                    chunks.append(value.strip())

            collect(payload)
            if chunks:
                return "\n".join(chunks)
    if path.suffix.lower() in {".xml", ".tei"} or stripped.startswith(b"<"):
        try:
            root = ET.fromstring(raw)
            if str(root.tag).rsplit("}", 1)[-1] == "article":
                parents = {child: parent for parent in root.iter() for child in parent}
                prose_nodes = []
                for element in root.iter():
                    tag = str(element.tag).rsplit("}", 1)[-1]
                    if tag == "body":
                        prose_nodes.append(element)
                    elif tag == "abstract":
                        ancestor = parents.get(element)
                        inside_body = False
                        while ancestor is not None:
                            if str(ancestor.tag).rsplit("}", 1)[-1] == "body":
                                inside_body = True
                                break
                            ancestor = parents.get(ancestor)
                        if not inside_body:
                            prose_nodes.append(element)
                if prose_nodes:
                    excluded = {
                        "ack",
                        "acknowledgments",
                        "author-notes",
                        "back",
                        "fn-group",
                        "front",
                        "ref-list",
                        "supplementary-material",
                    }

                    def collect(element: ET.Element) -> list[str]:
                        if str(element.tag).rsplit("}", 1)[-1] in excluded:
                            return []
                        values = [element.text or ""]
                        for child in element:
                            values.extend(collect(child))
                            values.append(child.tail or "")
                        return values

                    return " ".join(
                        " ".join("".join(collect(element)).split()) for element in prose_nodes
                    ).strip()
                return ""
            return "\n".join(" ".join(root.itertext()).split())
        except ET.ParseError:
            pass
    return raw.decode("utf-8-sig", errors="replace")


def _sentences(text: str) -> list[str]:
    normalised = re.sub(r"\s+", " ", text).strip()
    if not normalised:
        return []
    values = re.split(r"(?<=[.!?])\s+", normalised)
    return [value.strip() for value in values if len(value.strip().split()) >= 5]


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", value.lower()))


def _partial_quote(sentence: str) -> str:
    words = sentence.split()
    if len(words) < 8:
        return sentence
    count = max(5, min(len(words) - 1, round(len(words) * 0.6)))
    return " ".join(words[:count])


def _candidate_quotes(sentences: Sequence[str], index: int) -> list[str]:
    claim = sentences[index]
    others = [sentence for position, sentence in enumerate(sentences) if position != index]
    if not others:
        others = [claim]
    context = sentences[(index + 1) % len(sentences)]
    negated = [
        sentence
        for sentence in others
        if any(marker in f" {sentence.lower()} " for marker in _NEGATION_MARKERS)
    ]
    contradiction = negated[0] if negated else others[(index + 1) % len(others)]
    claim_tokens = _tokens(claim)
    hard_negative = max(
        others,
        key=lambda sentence: (
            len(claim_tokens & _tokens(sentence)),
            -abs(len(sentence) - len(claim)),
            sentence,
        ),
    )
    return [claim, _partial_quote(claim), context, contradiction, hard_negative]


def _candidate_span_identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["source_id"]),
        str(row["candidate_claim"]),
        str(row["exact_quote"]),
    )


def _candidate_rows_have_unique_spans(
    rows: Sequence[Mapping[str, Any]],
    seen_spans: set[tuple[str, str, str]],
) -> bool:
    identities = [_candidate_span_identity(row) for row in rows]
    return len(identities) == len(set(identities)) and not seen_spans.intersection(identities)


def _candidate_pattern_id(
    stratum: str, family_index: int, claim: str, quote: str
) -> tuple[str, str]:
    """Select an opaque pattern code without exposing retrieval intent."""

    offsets = {
        "S1": (0,),
        "S2": (1,),
        "S3": (2,),
        "S4": (3, 4, 5, 6, 7),
        "S5": (8, 9, 10, 11),
    }
    choices = offsets[stratum]
    if stratum in {"S1", "S2", "S3"}:
        return f"A{choices[0] + 1:02d}", "stratum_defined"
    text = f" {claim.lower()} {quote.lower()} "
    matches = [
        pattern_id
        for pattern_id, markers in _PATTERN_MARKERS
        if any(marker in text for marker in markers)
    ]
    if matches:
        return matches[family_index % len(matches)], "lexical_heuristic"
    return f"A{4 + family_index % len(_PATTERN_MARKERS):02d}", "fallback_pending_human_review"


def _publication_year(value: Any) -> int | None:
    match = re.match(r"^(\d{4})", str(value or ""))
    return int(match.group(1)) if match else None


def _source_semantic_assignment(
    source: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Derive a source partition from pre-annotation source metadata.

    The catalog's semantic assignment is an auditable declaration, not the
    authority for the partition itself.  Recomputing the assignment here
    prevents a packet or manifest from changing a source's date/domain facts
    and then changing its split along with them.
    """

    year = _publication_year(source.get("publication_date"))
    disciplines = source.get("disciplines")
    declared_disciplines = (
        {str(value) for value in disciplines}
        if isinstance(disciplines, Sequence) and not isinstance(disciplines, (str, bytes))
        else set()
    )
    held_out = (
        source.get("catalog_declared_held_out_domain") is True
        or _nonempty(source.get("held_out_domain_id"))
        or "technical_writing" in declared_disciplines
    )
    if held_out:
        domain_id = str(
            source.get("held_out_domain_id")
            or (
                "technical-writing-held-out-v1"
                if "technical_writing" in declared_disciplines
                else "catalog-declared-held-out-domain"
            )
        )
        expected = {
            "partition": "ood",
            "criteria_id": policy["ood"]["criteria_id"],
            "catalog_declared_held_out_domain": True,
            "domain_id": domain_id,
        }
    elif year is not None and year >= policy["temporal"]["start_year"]:
        expected = {
            "partition": "temporal",
            "criteria_id": policy["temporal"]["criteria_id"],
            "publication_year": year,
            "start_year": policy["temporal"]["start_year"],
            "catalog_declared_held_out_domain": False,
        }
    else:
        expected = {
            "partition": "in_domain",
            "criteria_id": _IN_DOMAIN_CRITERIA_ID,
            "publication_year": year,
            "catalog_declared_held_out_domain": False,
        }

    explicit = source.get("semantic_split") or source.get("semantic_split_default")
    if isinstance(explicit, Mapping):
        declared = _validate_semantic_assignment(explicit, policy=policy)
        for field, value in declared.items():
            if field in expected and value != expected[field]:
                raise AcquisitionValidationError(
                    "semantic assignment does not match source publication/domain metadata"
                )
        if set(declared) - set(expected):
            raise AcquisitionValidationError(
                "semantic assignment contains fields inconsistent with source metadata"
            )
    return _validate_semantic_assignment(expected, policy=policy)


def _safe_source_filename(source_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", source_id).strip("._")[:80] or "source"
    suffix = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:12]
    return f"{slug}-{suffix}.source"


def _source_record(
    entry: Mapping[str, Any],
    *,
    state: str,
    acquired_uri: str | None,
    digest: str | None,
    reason: str | None,
) -> dict[str, Any]:
    raw_licence = entry.get("licence", entry.get("license", {}))
    raw_licence = raw_licence if isinstance(raw_licence, Mapping) else {}
    spdx = _normalise_license(raw_licence.get("spdx", raw_licence.get("name")))
    disciplines = [
        str(value) for value in entry.get("disciplines", []) if str(value) in SUPPORTED_DISCIPLINES
    ]
    if not disciplines:
        disciplines = ["interdisciplinary"]
    stable_uri = str(
        entry.get("stable_uri") or entry.get("uri") or entry.get("content_uri") or ""
    ).strip()
    rights_uri = str(
        raw_licence.get("article_rights_uri") or entry.get("article_rights_uri") or ""
    ).strip()
    licence_uri = str(
        raw_licence.get("uri") or "https://spdx.org/licenses/NOASSERTION.html"
    ).strip()
    authors = [str(value).strip() for value in entry.get("authors", []) if str(value).strip()]
    title = str(entry.get("title") or "Untitled candidate source").strip()
    record: dict[str, Any] = {
        "source_id": str(entry.get("source_id") or "").strip(),
        "doi": entry.get("doi") if entry.get("doi") is not None else None,
        "stable_uri": stable_uri,
        "exact_acquired_copy_uri": acquired_uri,
        "canonical_source_family": canonical_source_family(entry),
        "title": title,
        "authors": authors,
        "publisher": str(entry.get("publisher") or "Unknown publisher").strip(),
        "publication_date": str(entry.get("publication_date") or "undated").strip(),
        "disciplines": disciplines,
        "licence": {
            "spdx": spdx,
            "uri": licence_uri,
            "version": str(raw_licence.get("version") or "unspecified").strip(),
            "article_rights_uri": rights_uri,
            "verification": str(raw_licence.get("verification") or "unverified").strip(),
            "evidence_uri": str(raw_licence.get("evidence_uri") or "").strip() or None,
            "verification_basis": str(raw_licence.get("verification_basis") or "").strip() or None,
        },
        "attribution": str(entry.get("attribution") or "").strip(),
        "acquired_at": _now(),
        "sha256": digest,
        "allowed_uses": [
            str(value) for value in entry.get("allowed_uses", []) if str(value) in ALLOWED_USES
        ],
        "third_party": {
            "status": str((entry.get("third_party") or {}).get("status") or "unknown")
            if isinstance(entry.get("third_party"), Mapping)
            else "unknown",
            "warning": str(
                (entry.get("third_party") or {}).get("warning")
                or "Article-level third-party rights require human review."
            )
            if isinstance(entry.get("third_party"), Mapping)
            else "Article-level third-party rights require human review.",
        },
        "state": state,
        "approval": {
            "status": "pending"
            if state in {"CANDIDATE", "ADMISSIBLE_PENDING_REVIEW"}
            else "not_requested",
            "reviewer_id": None,
        },
        "rejection_reason": reason,
    }
    return record


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _write_jsonl_atomic(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": "1.0.0", "sources": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"version": "1.0.0", "sources": {}}
    return (
        payload
        if isinstance(payload, Mapping) and isinstance(payload.get("sources"), Mapping)
        else {"version": "1.0.0", "sources": {}}
    )


def _entry_licence_error(entry: Mapping[str, Any]) -> tuple[str, str] | None:
    raw = entry.get("licence", entry.get("license", {}))
    if not isinstance(raw, Mapping):
        return "REJECTED_UNRESOLVED_LICENCE", "licence record is absent or not an object"
    spdx = _normalise_license(raw.get("spdx", raw.get("name")))
    if spdx not in ADMISSIBLE_LICENSES:
        if spdx in {"UNKNOWN", "", "OTHER-OA", "CC-BY-SA"} or not spdx:
            return (
                "REJECTED_UNRESOLVED_LICENCE",
                f"licence is not resolved to an admissible exact term: {spdx}",
            )
        return "REJECTED_RIGHTS", f"licence is outside the conservative admission policy: {spdx}"
    if not _nonempty(raw.get("uri")) or not _nonempty(raw.get("version")):
        return "REJECTED_UNRESOLVED_LICENCE", "exact licence URI or version is missing"
    if not _nonempty(raw.get("article_rights_uri")):
        return "REJECTED_UNRESOLVED_LICENCE", "article-level rights URI is missing"
    if raw.get("verification") != "article_level_verified":
        return "REJECTED_UNRESOLVED_LICENCE", "article-level licence verification is not recorded"
    allowed = raw_entry_allowed_uses(entry)
    if not REQUIRED_CANDIDATE_USES.issubset(set(allowed)):
        return (
            "REJECTED_RIGHTS",
            "candidate-generation and human-annotation uses are not both recorded",
        )
    return None


def raw_entry_allowed_uses(entry: Mapping[str, Any]) -> list[str]:
    values = entry.get("allowed_uses", [])
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return []
    return [str(value) for value in values if str(value) in ALLOWED_USES]


def _catalog_entry_validity(entry: Mapping[str, Any]) -> str | None:
    source_id = str(entry.get("source_id") or "").strip()
    if not source_id:
        return "source_id is missing"
    if not _nonempty(entry.get("stable_uri") or entry.get("uri") or entry.get("content_uri")):
        return "stable URI is missing"
    if not _nonempty(entry.get("content_uri")):
        return "content URI is missing"
    disciplines = entry.get("disciplines")
    if (
        not isinstance(disciplines, Sequence)
        or isinstance(disciplines, (str, bytes))
        or not disciplines
        or not all(str(value) in SUPPORTED_DISCIPLINES for value in disciplines)
    ):
        return "discipline mapping is missing or unsupported"
    if not _nonempty(entry.get("title")) or not _nonempty(entry.get("publisher")):
        return "bibliographic metadata is incomplete"
    if (
        not isinstance(entry.get("authors"), Sequence)
        or isinstance(entry.get("authors"), (str, bytes))
        or not entry.get("authors")
    ):
        return "authors are missing"
    return None


def _make_pair(
    source: Mapping[str, Any],
    sentences: Sequence[str],
    family_index: int,
    *,
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    claim = sentences[family_index]
    family_id = f"{source['source_id']}:claim-family:{family_index:06d}"
    semantic = _source_semantic_assignment(source, policy)
    rows: list[dict[str, Any]] = []
    for stratum, quote in zip(
        CANDIDATE_STRATA, _candidate_quotes(sentences, family_index), strict=True
    ):
        pattern_id, pattern_basis = _candidate_pattern_id(stratum, family_index, claim, quote)
        identity = {
            "source_id": source["source_id"],
            "family_id": family_id,
            "stratum": stratum,
            "claim": claim,
            "quote": quote,
        }
        pair_id = (
            "p-"
            + hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:24]
        )
        row = {
            "schema_version": "2.0.0",
            "packet_type": "citation_support_unlabelled_annotation",
            "packet_id": f"packet-{pair_id}",
            "pair_id": pair_id,
            "claim_family_id": family_id,
            "group_id": family_id,
            "discipline": source["disciplines"][0],
            "claim_origin": "source-authored-sentence",
            "candidate_claim": claim,
            "exact_quote": quote,
            "context": " ".join(
                sentences[max(0, family_index - 1) : min(len(sentences), family_index + 2)]
            ),
            "source_id": source["source_id"],
            "source_uri": source["stable_uri"],
            "acquired_copy_uri": source["exact_acquired_copy_uri"],
            "source_digest": source["sha256"],
            "licence": source["licence"]["spdx"],
            "attribution": source["attribution"],
            "acquisition_stratum": stratum,
            "candidate_pattern_id": pattern_id,
            "pattern_basis": pattern_basis,
            "semantic_split": semantic,
            "annotations": [
                {"annotator_id": None, "label": None, "rationale": None},
                {"annotator_id": None, "label": None, "rationale": None},
            ],
            "adjudication": {
                "status": "pending",
                "adjudicator_id": None,
                "label": None,
                "rationale": None,
            },
        }
        validate_unlabelled_candidate_pair(row, policy=policy)
        rows.append(row)
    return rows


def acquire_candidates(
    catalog_path: Path | str,
    output_dir: Path | str,
    *,
    max_pairs: int = 6000,
    seed: int = 0,
    max_bytes: int = 50 * 1024 * 1024,
) -> dict[str, Any]:
    """Acquire admissible source copies and emit deterministic unlabelled packets."""

    if (
        isinstance(max_pairs, bool)
        or not isinstance(max_pairs, int)
        or max_pairs <= 0
        or max_pairs % len(CANDIDATE_STRATA)
    ):
        raise AcquisitionValidationError(
            f"max_pairs must be a positive multiple of {len(CANDIDATE_STRATA)}"
        )
    catalog_path = Path(catalog_path).resolve()
    output_dir = Path(output_dir).resolve()
    catalog, catalog_digest = _read_catalog(catalog_path)
    policy = _validate_semantic_policy(
        catalog.get("semantic_split_policy", DEFAULT_SEMANTIC_POLICY)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    sources_dir = output_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / ".acquisition-state.json"
    state = _load_state(state_path)
    state_sources: dict[str, Any] = dict(state.get("sources", {}))
    previous_manifest: Mapping[str, Any] = {}
    previous_manifest_path = output_dir / "source-candidate-manifest.json"
    if previous_manifest_path.is_file():
        try:
            loaded_manifest = json.loads(previous_manifest_path.read_text(encoding="utf-8"))
            if (
                isinstance(loaded_manifest, Mapping)
                and loaded_manifest.get("catalog_sha256") == catalog_digest
            ):
                previous_manifest = loaded_manifest
        except (OSError, UnicodeError, json.JSONDecodeError):
            previous_manifest = {}
    source_records: list[dict[str, Any]] = []
    usable: list[tuple[dict[str, Any], list[str]]] = []
    seen_families: set[str] = set()
    seen_digests: set[str] = set()
    counts = Counter()
    downloaded = 0
    reused = 0

    catalog_sources = catalog.get("sources", [])
    for entry_value in catalog_sources:
        if not isinstance(entry_value, Mapping):
            continue
        entry = dict(entry_value)
        source_id = str(entry.get("source_id") or "").strip()
        validity = _catalog_entry_validity(entry)
        if validity:
            record = _source_record(
                entry, state="REJECTED_CONTENT", acquired_uri=None, digest=None, reason=validity
            )
            source_records.append(record)
            counts[record["state"]] += 1
            continue
        licence_error = _entry_licence_error(entry)
        if licence_error:
            record = _source_record(
                entry,
                state=licence_error[0],
                acquired_uri=None,
                digest=None,
                reason=licence_error[1],
            )
            source_records.append(record)
            counts[record["state"]] += 1
            continue
        family = canonical_source_family(entry)
        if family in seen_families:
            record = _source_record(
                entry,
                state="REJECTED_DUPLICATE",
                acquired_uri=None,
                digest=None,
                reason=f"canonical source family already admitted: {family}",
            )
            source_records.append(record)
            counts[record["state"]] += 1
            continue
        target = sources_dir / _safe_source_filename(source_id)
        content_uri = str(entry["content_uri"])
        cached = state_sources.get(source_id)
        is_reused = False
        digest: str | None = None
        try:
            if (
                target.is_file()
                and isinstance(cached, Mapping)
                and cached.get("content_uri") == content_uri
                and _is_sha256(cached.get("sha256"))
            ):
                if _cached_source_is_current(
                    content_uri, target, cached, entry, max_bytes=max_bytes
                ):
                    if target.stat().st_size > max_bytes:
                        raise OSError(
                            f"cached content exceeds resource limit: {max_bytes} bytes"
                        )
                    digest = _sha256_file(target)
                    if digest != str(cached["sha256"]).lower():
                        raise OSError("cached source digest does not match acquisition state")
                    is_reused = True
                else:
                    _copy_content(content_uri, target, max_bytes=max_bytes)
                    digest = _sha256_file(target)
            else:
                _copy_content(content_uri, target, max_bytes=max_bytes)
                digest = _sha256_file(target)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            record = _source_record(
                entry,
                state="REJECTED_CONTENT",
                acquired_uri=_file_uri(target) if target.is_file() else None,
                digest=None,
                reason=str(exc),
            )
            source_records.append(record)
            counts[record["state"]] += 1
            continue
        expected = entry.get("expected_sha256")
        if expected is not None and (not _is_sha256(expected) or str(expected).lower() != digest):
            record = _source_record(
                entry,
                state="REJECTED_CONTENT",
                acquired_uri=_file_uri(target),
                digest=digest,
                reason="acquired content does not match expected SHA-256",
            )
            source_records.append(record)
            counts[record["state"]] += 1
            continue
        if digest in seen_digests:
            record = _source_record(
                entry,
                state="REJECTED_DUPLICATE",
                acquired_uri=_file_uri(target),
                digest=digest,
                reason="acquired bytes duplicate an earlier source",
            )
            source_records.append(record)
            counts[record["state"]] += 1
            continue
        seen_families.add(family)
        seen_digests.add(digest)
        record = _source_record(
            entry,
            state="ADMISSIBLE_PENDING_REVIEW",
            acquired_uri=_file_uri(target),
            digest=digest,
            reason=None,
        )
        if is_reused and isinstance(cached, Mapping) and _nonempty(cached.get("acquired_at")):
            record["acquired_at"] = cached["acquired_at"]
        record["semantic_split_default"] = _source_semantic_assignment(entry, policy)
        source_records.append(record)
        counts[record["state"]] += 1
        state_sources[source_id] = {
            "content_uri": content_uri,
            "sha256": digest,
            "exact_acquired_copy_uri": _file_uri(target),
            "acquired_at": record["acquired_at"],
        }
        if is_reused:
            reused += 1
        else:
            downloaded += 1
        try:
            text = _read_text_content(target)
            sentences = _sentences(text)
        except (OSError, UnicodeError, ValueError) as exc:
            record["state"] = "REJECTED_CONTENT"
            record["approval"] = {"status": "not_requested", "reviewer_id": None}
            record["rejection_reason"] = f"source text extraction failed: {exc}"
            counts["ADMISSIBLE_PENDING_REVIEW"] -= 1
            counts["REJECTED_CONTENT"] += 1
            continue
        if not sentences:
            record["state"] = "REJECTED_CONTENT"
            record["approval"] = {"status": "not_requested", "reviewer_id": None}
            record["rejection_reason"] = "source contains no extractable bounded sentences"
            counts["ADMISSIBLE_PENDING_REVIEW"] -= 1
            counts["REJECTED_CONTENT"] += 1
            continue
        usable.append((record, sentences))

    source_manifest_status = "ACQUISITION_INCOMPLETE"
    # Round-robin by declared discipline gives every profile a fair opportunity
    # without pretending that a missing discipline can be filled synthetically.
    by_discipline: dict[str, list[tuple[dict[str, Any], list[str]]]] = defaultdict(list)
    for source, sentences in usable:
        # A multi-discipline source is mapped to its declared primary profile
        # for candidate balancing. Reusing it under every profile would create
        # duplicate claim groups with conflicting discipline identities.
        by_discipline[source["disciplines"][0]].append((source, sentences))
    source_positions = {discipline: 0 for discipline in by_discipline}
    all_disciplines = [
        discipline for discipline in SUPPORTED_DISCIPLINES if discipline in by_discipline
    ]
    families_needed = math.ceil(max_pairs / len(CANDIDATE_STRATA))
    candidate_rows: list[dict[str, Any]] = []
    seen_candidate_spans: set[tuple[str, str, str]] = set()
    candidate_families_rejected_for_span_collision = 0
    family_number = 0
    while family_number < families_needed and all_disciplines:
        made = False
        for discipline in all_disciplines:
            if family_number >= families_needed:
                break
            candidates = by_discipline[discipline]
            attempts = 0
            selected: tuple[dict[str, Any], list[str]] | None = None
            while attempts < len(candidates):
                position = source_positions[discipline] % len(candidates)
                source_positions[discipline] += 1
                attempts += 1
                source, sentences = candidates[position]
                sentence_index = (source_positions[discipline] - 1) // max(1, len(candidates))
                if sentence_index < len(sentences):
                    selected = (source, sentences)
                    break
            if selected is None:
                continue
            source, sentences = selected
            sentence_index = (source_positions[discipline] - 1) // max(1, len(candidates))
            family_rows = _make_pair(source, sentences, sentence_index, policy=policy)
            if not _candidate_rows_have_unique_spans(family_rows, seen_candidate_spans):
                # The source position has been consumed, so the next round can
                # backfill from another sentence or source.  A colliding family
                # is never counted toward the requested pair total.
                candidate_families_rejected_for_span_collision += 1
                made = True
                continue
            candidate_rows.extend(family_rows)
            seen_candidate_spans.update(_candidate_span_identity(row) for row in family_rows)
            family_number += 1
            made = True
        if not made:
            break
    candidate_rows = candidate_rows[:max_pairs]
    # Candidate groups must not be split by this preparatory truncation.
    complete_pairs = len(CANDIDATE_STRATA)
    if len(candidate_rows) % complete_pairs:
        candidate_rows = candidate_rows[
            : len(candidate_rows) - (len(candidate_rows) % complete_pairs)
        ]
    candidate_span_identities = [_candidate_span_identity(row) for row in candidate_rows]
    duplicate_candidate_span_count = len(candidate_span_identities) - len(
        set(candidate_span_identities)
    )
    if duplicate_candidate_span_count:
        raise AcquisitionValidationError(
            "candidate source/claim/span identities must be unique; "
            f"found {duplicate_candidate_span_count} duplicate rows"
        )
    if len(candidate_rows) >= max_pairs:
        source_manifest_status = "READY_FOR_HUMAN_ANNOTATION"

    manifest = {
        "schema_version": "2.0.0",
        "manifest_type": "citation_support_source_candidates",
        "status": source_manifest_status,
        "generated_at": str(previous_manifest.get("generated_at") or _now()),
        "catalog_uri": _file_uri(catalog_path),
        "catalog_sha256": catalog_digest,
        "acquisition": {
            "tool": "swos_runtime.citation_acquisition",
            "version": "1.0.0",
            "resumable": True,
            "cache_directory_uri": _file_uri(sources_dir),
            "seed": seed,
            "max_bytes_per_source": max_bytes,
            "review_boundary": "independent human source review remains required",
        },
        "semantic_split_policy": policy,
        "sources": source_records,
    }
    indexed_sources = validate_source_candidate_manifest(manifest)
    for row in candidate_rows:
        validate_candidate_source_binding(row, indexed_sources)
    state_payload = {"version": "1.0.0", "sources": state_sources}
    _write_json_atomic(state_path, state_payload)
    _write_json_atomic(output_dir / "source-candidate-manifest.json", manifest)
    _write_jsonl_atomic(output_dir / "unlabelled-candidate-pairs.jsonl", candidate_rows)
    semantic_splits = semantic_grouped_split(candidate_rows, policy=policy, seed=seed)
    group_locations: dict[str, set[str]] = defaultdict(set)
    for split, values in semantic_splits.items():
        for row in values:
            group_locations[str(row["group_id"])].add(split)
    group_leakage = [
        f"group {group_id} has multiple semantic split locations"
        for group_id, locations in sorted(group_locations.items())
        if len(locations) > 1
    ]
    source_locations: dict[str, set[str]] = defaultdict(set)
    claim_locations: dict[str, set[str]] = defaultdict(set)
    for split, values in semantic_splits.items():
        for row in values:
            source_locations[str(row["source_id"])].add(split)
            claim_locations[str(row["claim_family_id"])].add(split)
    source_family_leakage = [
        f"source family {source_id} has multiple semantic split locations"
        for source_id, locations in sorted(source_locations.items())
        if len(locations) > 1
    ]
    claim_family_split_leakage = [
        f"claim family {claim_family_id} has multiple semantic split locations"
        for claim_family_id, locations in sorted(claim_locations.items())
        if len(locations) > 1
    ]
    if source_family_leakage or claim_family_split_leakage:
        raise AcquisitionValidationError(
            "; ".join(source_family_leakage + claim_family_split_leakage)
        )
    source_family_counts = Counter()
    publication_year_histogram = Counter()
    for source in source_records:
        if source["state"] not in {"CANDIDATE", "ADMISSIBLE_PENDING_REVIEW"}:
            continue
        assignment = source.get("semantic_split_default")
        if isinstance(assignment, Mapping):
            source_family_counts[assignment["partition"]] += 1
        year = _publication_year(source.get("publication_date"))
        publication_year_histogram[str(year) if year is not None else "unknown"] += 1
    claim_family_locations: dict[str, set[str]] = defaultdict(set)
    pair_counts_by_partition = Counter()
    for row in candidate_rows:
        partition = row["semantic_split"]["partition"]
        claim_family_locations[str(row["claim_family_id"])].add(partition)
        pair_counts_by_partition[partition] += 1
    claim_family_leakage = [
        f"claim family {claim_family_id} has multiple semantic split locations"
        for claim_family_id, locations in sorted(claim_family_locations.items())
        if len(locations) > 1
    ]
    if claim_family_leakage:
        raise AcquisitionValidationError("; ".join(claim_family_leakage))
    claim_family_counts = Counter(
        next(iter(locations)) for locations in claim_family_locations.values()
    )
    semantic_partition_names = ("in_domain", "temporal", "ood")
    source_family_counts = {
        partition: source_family_counts[partition] for partition in semantic_partition_names
    }
    claim_family_counts = {
        partition: claim_family_counts[partition] for partition in semantic_partition_names
    }
    pair_counts_by_partition = {
        partition: pair_counts_by_partition[partition] for partition in semantic_partition_names
    }
    values_by_discipline: dict[str, Counter[str]] = defaultdict(Counter)
    values_by_stratum: dict[str, Counter[str]] = defaultdict(Counter)
    for row in candidate_rows:
        partition = row["semantic_split"]["partition"]
        values_by_discipline[str(row["discipline"])][partition] += 1
        values_by_stratum[str(row["acquisition_stratum"])][partition] += 1
    pair_counts_by_discipline_and_partition = {
        discipline: {
            partition: values_by_discipline[discipline][partition]
            for partition in semantic_partition_names
        }
        for discipline in SUPPORTED_DISCIPLINES
    }
    pair_counts_by_stratum_and_partition = {
        stratum: {
            partition: values_by_stratum[stratum][partition]
            for partition in semantic_partition_names
        }
        for stratum in CANDIDATE_STRATA
    }
    temporal_selection = {
        "policy_version": policy["version"],
        "criteria_id": policy["temporal"]["criteria_id"],
        "start_year": policy["temporal"]["start_year"],
        "rule": policy["temporal"]["definition"],
        "selection_basis": (
            "publication-year histogram and pre-annotation benchmark viability; "
            "no human labels or model performance were consulted"
        ),
        "rationale": (
            "The 2020 later window retains a useful temporal holdout while leaving "
            "substantial non-OOD material for in-domain train, calibration, and locked-test "
            "allocation. OOD membership remains independently predeclared and takes precedence "
            "over date."
        ),
        "publication_year_histogram": dict(
            sorted(publication_year_histogram.items(), key=lambda item: item[0])
        ),
        "source_families_by_partition": source_family_counts,
        "claim_families_by_partition": claim_family_counts,
        "pairs_by_partition": pair_counts_by_partition,
    }
    report = {
        "schema_version": "2.0.0",
        "status": source_manifest_status,
        "human_boundary": "READY_FOR_HUMAN_ANNOTATION"
        if source_manifest_status == "READY_FOR_HUMAN_ANNOTATION"
        else "ACQUISITION_INCOMPLETE",
        "release_status": "NOT_CERTIFIED",
        "catalog_uri": _file_uri(catalog_path),
        "catalog_sha256": catalog_digest,
        "target_pairs": max_pairs,
        "candidate_pairs": len(candidate_rows),
        "claim_families": len({row["claim_family_id"] for row in candidate_rows}),
        "candidate_families_rejected_for_span_collision": candidate_families_rejected_for_span_collision,
        "duplicate_candidate_span_count": duplicate_candidate_span_count,
        "scholarly_works_discovered": len(catalog_sources),
        "downloaded_sources": downloaded,
        "reused_sources": reused,
        "source_counts_by_state": dict(sorted(counts.items())),
        "licence_counts_by_reason": {
            "admissible_pending_review": counts["ADMISSIBLE_PENDING_REVIEW"],
            "rejected_rights": counts["REJECTED_RIGHTS"],
            "rejected_unresolved_licence": counts["REJECTED_UNRESOLVED_LICENCE"],
            "rejected_duplicate": counts["REJECTED_DUPLICATE"],
            "rejected_content": counts["REJECTED_CONTENT"],
        },
        "source_families": {
            "unique_admissible": len(
                {
                    source["canonical_source_family"]
                    for source in source_records
                    if source["state"] in {"CANDIDATE", "ADMISSIBLE_PENDING_REVIEW"}
                }
            ),
            "by_provider": dict(
                sorted(
                    Counter(
                        source["source_id"].split("-", 1)[0] for source in source_records
                    ).items()
                )
            ),
        },
        "third_party_warning_sources": sum(
            source["third_party"]["status"] == "warning" for source in source_records
        ),
        "candidate_pairs_by_discipline": {
            discipline: sum(values_by_discipline[discipline].values())
            for discipline in SUPPORTED_DISCIPLINES
        },
        "candidate_pairs_by_stratum": {
            stratum: sum(values_by_stratum[stratum].values()) for stratum in CANDIDATE_STRATA
        },
        "stratum_policy": STRATUM_DEFINITIONS,
        "candidate_pairs_by_pattern": dict(
            sorted(Counter(row["candidate_pattern_id"] for row in candidate_rows).items())
        ),
        "adversarial_pattern_policy": ADVERSARIAL_PATTERN_DEFINITIONS,
        "candidate_pairs_by_pattern_basis": dict(
            sorted(Counter(row["pattern_basis"] for row in candidate_rows).items())
        ),
        "candidate_pairs_by_semantic_partition": dict(
            sorted(Counter(row["semantic_split"]["partition"] for row in candidate_rows).items())
        ),
        "publication_year_histogram": temporal_selection["publication_year_histogram"],
        "temporal_holdout_selection": temporal_selection,
        "source_families_by_semantic_partition": source_family_counts,
        "claim_families_by_semantic_partition": claim_family_counts,
        "pairs_by_semantic_partition": pair_counts_by_partition,
        "pairs_by_discipline_and_semantic_partition": pair_counts_by_discipline_and_partition,
        "pairs_by_stratum_and_semantic_partition": pair_counts_by_stratum_and_partition,
        "semantic_split_policy": policy,
        "group_leakage": group_leakage,
        "source_family_leakage": source_family_leakage,
        "claim_family_leakage": claim_family_split_leakage,
        "output_digests": {
            "source_candidate_manifest_sha256": _sha256_file(
                output_dir / "source-candidate-manifest.json"
            ),
            "unlabelled_candidate_pairs_sha256": _sha256_file(
                output_dir / "unlabelled-candidate-pairs.jsonl"
            ),
        },
        "labels_present": [],
        "independent_approval": False,
        "human_annotation": {
            "packet_file": "unlabelled-candidate-pairs.jsonl",
            "required_independent_annotators_per_pair": 2,
            "required_independent_adjudicator": 1,
            "status": "READY_FOR_HUMAN_ANNOTATION"
            if source_manifest_status == "READY_FOR_HUMAN_ANNOTATION"
            else "NOT_READY",
        },
    }
    _write_json_atomic(output_dir / "acquisition-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-pairs", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-bytes", type=int, default=50 * 1024 * 1024)
    args = parser.parse_args()
    try:
        report = acquire_candidates(
            args.catalog,
            args.out_dir,
            max_pairs=args.max_pairs,
            seed=args.seed,
            max_bytes=args.max_bytes,
        )
    except (
        AcquisitionValidationError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(json.dumps({"status": "ACQUISITION_INCOMPLETE", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "READY_FOR_HUMAN_ANNOTATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
