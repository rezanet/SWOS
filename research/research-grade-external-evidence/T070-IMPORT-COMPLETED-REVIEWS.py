#!/usr/bin/env python3
"""Import completed T070 human review records into a staged dataset input.

The importer is deliberately stricter than the preparation tools.  It accepts
only records that bind to the exact candidate and source-manifest bytes, carry
explicit human provenance, and contain complete rights, annotation, and
adjudication decisions.  It never changes the candidate labels itself.

The result is a deterministic, release-blocked staging directory containing
``pairs.jsonl`` and ``source-licence-manifest.json``.  The latter intentionally
requires a separate dataset-level approval before the production dataset
builder can consume it.  This keeps a successful import from being mistaken for
T070 completion or Research Grade evidence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_classifier import LABELS  # noqa: E402
from swos_runtime.citation_dataset import (  # noqa: E402
    DatasetValidationError,
    validate_pair_record,
    validate_pair_source_binding,
)

T070_LABELS = tuple(LABELS)
T070_PACKAGE_SCHEMA = "research-handoff.t070.human-review-package.v1"
T070_WORKSET_SCHEMA = "research-handoff.t070.blind-workset-manifest.v1"
T070_RIGHTS_SCHEMA = "research-handoff.t070.source-rights-workset.v1"
T070_ANNOTATION_SCHEMA = "research-handoff.t070.blind-annotation-item.v1"
T070_ADJUDICATION_SCHEMA = "research-handoff.t070.adjudication-binding.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DATASET_USES = ("train", "calibration", "locked_test", "ood", "temporal")
FORBIDDEN_HUMAN_KEYS = frozenset(
    {
        "acquisition_stratum",
        "candidate_pattern_id",
        "claim_origin",
        "pattern_basis",
        "semantic_split",
    }
)
HUMAN_REVIEW_STATUSES = frozenset({"human_reviewed", "completed_human_review"})


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(message: str) -> None:
    raise ValueError(message)


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{context} must be a non-empty string")
    return value.strip()


def _sha(value: Any, context: str) -> str:
    value = _text(value, context).lower()
    if not SHA256_RE.fullmatch(value):
        _fail(f"{context} must be lowercase SHA-256")
    return value


def _commit(value: Any, context: str) -> str:
    value = _text(value, context).lower()
    if not COMMIT_RE.fullmatch(value):
        _fail(f"{context} must be a full 40-character lowercase commit SHA")
    return value


def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{context} must be an object")
    return value


def _bool(value: Any, context: str) -> bool:
    if type(value) is not bool:
        _fail(f"{context} must be an explicit boolean")
    return value


def _list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{context} must be a list")
    return value


def _clear_conflict(value: Any, context: str) -> None:
    declaration = _mapping(value, context)
    if declaration.get("has_conflict") is not False:
        _fail(f"{context} must explicitly declare has_conflict=false")
    _text(declaration.get("details"), f"{context}.details")


def _record_digest(record: Mapping[str, Any], field: str) -> str:
    integrity = _mapping(record.get("integrity"), "integrity")
    if field not in integrity:
        _fail(f"integrity.{field} is required")
    candidate = copy.deepcopy(dict(record))
    candidate_integrity = _mapping(candidate.get("integrity"), "integrity")
    candidate_integrity[field] = None
    return sha256_json(candidate)


def _load_json(path: Path, context: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"unable to read {context}: {exc}")
    return _mapping(value, context)


def _load_jsonl(path: Path, context: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _fail(f"unable to read {context}: {exc}")
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            _fail(f"{context} line {line_number} is not JSON: {exc}")
        if not isinstance(value, dict):
            _fail(f"{context} line {line_number} must be an object")
        rows.append(value)
    return rows


def _require_exact_list(value: Any, expected: Sequence[str], context: str) -> None:
    if not isinstance(value, list) or value != list(expected):
        _fail(f"{context} must equal the frozen ordered label list")


def _validate_package(
    path: Path,
    candidate_pairs: Path,
    source_manifest: Path,
    rights_review: Path,
    annotator_a: Path,
    annotator_b: Path,
    adjudication: Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    package = dict(_load_json(path, "T070 package manifest"))
    if package.get("schema_version") != T070_PACKAGE_SCHEMA:
        _fail("T070 package manifest has an unsupported schema")
    if package.get("status") != "READY_FOR_GENUINE_HUMAN_REVIEW_NOT_T070_EVIDENCE":
        _fail("T070 package manifest is not a preparation-only package")
    if package.get("release_evidence") is not False:
        _fail("T070 package manifest must keep release_evidence=false")
    exact_head = _commit(package.get("exact_candidate_head"), "exact_candidate_head")
    source_head = _commit(package.get("source_workflow_head"), "source_workflow_head")
    requirements = _mapping(package.get("human_requirements"), "human_requirements")
    if requirements.get("annotations_per_pair") != 2:
        _fail("T070 package must require two annotations per pair")
    if requirements.get("annotators_independent") is not True:
        _fail("T070 package must require independent annotators")
    if requirements.get("adjudicator_distinct_from_both_annotators") is not True:
        _fail("T070 package must require a distinct adjudicator")

    inputs = _mapping(package.get("inputs"), "package inputs")
    input_digests = {
        "candidate_pairs_sha256": _sha(
            inputs.get("candidate_pairs_sha256"), "inputs.candidate_pairs_sha256"
        ),
        "source_manifest_sha256": _sha(
            inputs.get("source_manifest_sha256"), "inputs.source_manifest_sha256"
        ),
        "acquisition_report_sha256": _sha(
            inputs.get("acquisition_report_sha256"),
            "inputs.acquisition_report_sha256",
        ),
    }
    actual_inputs = {
        "candidate_pairs_sha256": sha256_file(candidate_pairs),
        "source_manifest_sha256": sha256_file(source_manifest),
    }
    for name in ("candidate_pairs_sha256", "source_manifest_sha256"):
        if actual_inputs[name] != input_digests[name]:
            _fail(
                f"{name.replace('_sha256', '')} digest does not match the exact T070 package binding"
            )

    payloads = _mapping(package.get("review_payloads"), "review_payloads")
    expected_names = {
        "source_rights": rights_review,
        "annotator_A": annotator_a,
        "annotator_B": annotator_b,
        "adjudication": adjudication,
    }
    for name, actual_path in expected_names.items():
        payload = _mapping(payloads.get(name), f"review_payloads.{name}")
        declared_path = _text(payload.get("path"), f"review_payloads.{name}.path")
        if Path(declared_path).name != actual_path.name:
            _fail(f"review_payloads.{name}.path does not identify the supplied file")
        _sha(payload.get("sha256"), f"review_payloads.{name}.sha256")

    pair_count = package.get("pair_count")
    source_count = package.get("source_count")
    if type(pair_count) is not int or pair_count <= 0:
        _fail("T070 package pair_count must be a positive integer")
    if type(source_count) is not int or source_count <= 0:
        _fail("T070 package source_count must be a positive integer")
    package["exact_candidate_head"] = exact_head
    package["source_workflow_head"] = source_head
    package["pair_count"] = pair_count
    package["source_count"] = source_count
    return package, input_digests


def _validate_workset_manifest(
    path: Path,
    candidate_pairs: Path,
    rights_review: Path,
    annotator_a: Path,
    annotator_b: Path,
    adjudication: Path,
    expected_pair_count: int,
) -> dict[str, Any]:
    manifest = dict(_load_json(path, "T070 blind workset manifest"))
    if manifest.get("schema_version") != T070_WORKSET_SCHEMA:
        _fail("T070 blind workset manifest has an unsupported schema")
    if manifest.get("status") != "READY_FOR_RIGHTS_BINDING_THEN_HUMAN_ANNOTATION":
        _fail("T070 blind workset manifest has an unsupported status")
    if manifest.get("release_evidence") is not False:
        _fail("T070 blind workset manifest must keep release_evidence=false")
    if _sha(manifest.get("source_pairs_sha256"), "source_pairs_sha256") != sha256_file(
        candidate_pairs
    ):
        _fail("workset source-pairs digest does not match candidate pairs")
    for field in ("pair_count", "unique_pair_ids", "unique_source_claim_quote_tuples"):
        if manifest.get(field) != expected_pair_count:
            _fail(f"workset {field} does not match the candidate pair count")
    if manifest.get("required_human_annotations_per_pair") != 2:
        _fail("workset must require two human annotations per pair")
    if manifest.get("required_independent_adjudications_per_pair") != 1:
        _fail("workset must require one independent adjudication per pair")

    worksets = _mapping(manifest.get("worksets"), "worksets")
    paths = {"A": annotator_a, "B": annotator_b, "adjudication": adjudication}
    for name, actual_path in paths.items():
        declared = _mapping(worksets.get(name), f"worksets.{name}")
        if Path(_text(declared.get("path"), f"worksets.{name}.path")).name != actual_path.name:
            _fail(f"worksets.{name}.path does not identify the supplied file")
        if _sha(declared.get("sha256"), f"worksets.{name}.sha256") != sha256_file(actual_path):
            _fail(f"worksets.{name} digest does not match the supplied completed review file")

    rights_binding = _mapping(manifest.get("source_rights_review"), "source_rights_review")
    if (
        Path(_text(rights_binding.get("path"), "source_rights_review.path")).name
        != rights_review.name
    ):
        _fail("source_rights_review.path does not identify the supplied rights file")
    if _sha(rights_binding.get("sha256"), "source_rights_review.sha256") != sha256_file(
        rights_review
    ):
        _fail("source rights digest does not match the supplied completed rights file")
    return manifest


def _validate_candidates(
    path: Path, expected_pair_count: int
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    rows = _load_jsonl(path, "T070 candidate pairs")
    if len(rows) != expected_pair_count:
        _fail(
            f"T070 candidate pairs count {len(rows)} does not match package count {expected_pair_count}"
        )
    pair_by_id: dict[str, dict[str, Any]] = {}
    packet_digests: dict[str, str] = {}
    semantic_keys: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows, 1):
        context = f"candidate pair line {index}"
        if row.get("schema_version") != "2.0.0":
            _fail(f"{context} has an unsupported schema")
        if row.get("packet_type") != "citation_support_unlabelled_annotation":
            _fail(f"{context} is not an unlabelled citation packet")
        for key in ("label", "relation", "retrieval_intent"):
            if key in row and row.get(key) not in (None, ""):
                _fail(f"{context} contains pre-supplied human truth in {key}")
        pair_id = _text(row.get("pair_id"), f"{context}.pair_id")
        if pair_id in pair_by_id:
            _fail(f"duplicate candidate pair_id {pair_id}")
        source_id = _text(row.get("source_id"), f"{context}.source_id")
        _sha(row.get("source_digest"), f"{context}.source_digest")
        claim = _text(row.get("candidate_claim"), f"{context}.candidate_claim")
        quote = _text(row.get("exact_quote"), f"{context}.exact_quote")
        _text(row.get("packet_id"), f"{context}.packet_id")
        _text(row.get("claim_family_id"), f"{context}.claim_family_id")
        _text(row.get("group_id"), f"{context}.group_id")
        _text(row.get("discipline"), f"{context}.discipline")
        _text(row.get("source_uri"), f"{context}.source_uri")
        _text(row.get("licence"), f"{context}.licence")
        annotations = row.get("annotations")
        if not isinstance(annotations, list) or len(annotations) != 2:
            _fail(f"{context} must retain exactly two blank annotation slots")
        for annotation in annotations:
            item = _mapping(annotation, f"{context}.annotation")
            if any(
                item.get(key) not in (None, "") for key in ("annotator_id", "label", "rationale")
            ):
                _fail(f"{context} is not an unlabelled candidate")
        adjudication = _mapping(row.get("adjudication"), f"{context}.adjudication")
        if adjudication.get("status") != "pending":
            _fail(f"{context} adjudication is already populated")
        if any(
            adjudication.get(key) not in (None, "")
            for key in ("adjudicator_id", "label", "rationale")
        ):
            _fail(f"{context} adjudication contains human truth")
        semantic_key = (source_id, claim, quote)
        if semantic_key in semantic_keys:
            _fail(f"duplicate candidate source/claim/span identity at line {index}")
        semantic_keys.add(semantic_key)
        pair_by_id[pair_id] = row
        packet_digests[pair_id] = sha256_json(row)
    return rows, pair_by_id, packet_digests


def _validate_source_manifest(
    path: Path,
    expected_source_count: int,
) -> dict[str, dict[str, Any]]:
    manifest = _load_json(path, "T070 source candidate manifest")
    if manifest.get("schema_version") != "2.0.0":
        _fail("T070 source candidate manifest has an unsupported schema")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or len(sources) != expected_source_count:
        _fail("T070 source candidate manifest source count does not match package")
    indexed: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(sources, 1):
        source = dict(_mapping(value, f"source {index}"))
        source_id = _text(source.get("source_id"), f"source {index}.source_id")
        if source_id in indexed:
            _fail(f"duplicate source_id {source_id}")
        source["source_id"] = source_id
        source["stable_uri"] = _text(source.get("stable_uri"), f"source {source_id}.stable_uri")
        source_digest = source.get("sha256")
        if source_digest is not None:
            source["sha256"] = _sha(source_digest, f"source {source_id}.sha256")
        indexed[source_id] = source
    return indexed


def _validate_rights_reviews(
    path: Path,
    source_manifest_digest: str,
    sources: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    payload = _load_json(path, "T070 source rights review workset")
    if payload.get("schema_version") != T070_RIGHTS_SCHEMA:
        _fail("T070 source rights workset has an unsupported schema")
    if payload.get("release_evidence") is not False:
        _fail("T070 source rights workset must keep release_evidence=false")
    if (
        _sha(payload.get("source_manifest_sha256"), "rights source_manifest_sha256")
        != source_manifest_digest
    ):
        _fail("rights workset is bound to a different source manifest")
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != len(sources):
        _fail("source rights workset must contain one record per source")
    indexed: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(records, 1):
        record = dict(_mapping(value, f"rights record {index}"))
        context = f"rights record {index}"
        if record.get("schema_version") != "research-handoff.t070.source-rights-review.v1":
            _fail(f"{context} has an unsupported schema")
        if record.get("status") not in HUMAN_REVIEW_STATUSES:
            _fail(f"{context} is not marked as completed human review")
        binding = _mapping(record.get("source_binding"), f"{context}.source_binding")
        source_id = _text(binding.get("source_id"), f"{context}.source_id")
        if source_id in indexed:
            _fail(f"duplicate rights review for source {source_id}")
        source = sources.get(source_id)
        if source is None:
            _fail(f"rights review references unknown source {source_id}")
        if (
            _sha(binding.get("source_manifest_sha256"), f"{context}.source_manifest_sha256")
            != source_manifest_digest
        ):
            _fail(f"{context} is bound to a different source manifest")
        expected_binding = {
            "stable_uri": source.get("stable_uri"),
            "source_uri": source.get("stable_uri"),
            "acquired_copy_uri": source.get("exact_acquired_copy_uri"),
            "manifest_expected_sha256": source.get("sha256"),
            "title": source.get("title"),
            "authors": source.get("authors"),
            "publisher": source.get("publisher"),
            "publication_date": source.get("publication_date"),
            "doi": source.get("doi"),
            "attribution": source.get("attribution"),
            "allowed_uses_claimed_by_manifest": source.get("allowed_uses"),
            "licence_metadata": source.get("licence"),
            "third_party_warning": source.get("third_party"),
        }
        for key, expected in expected_binding.items():
            if binding.get(key) != expected:
                _fail(f"{context}.{key} does not match the immutable source manifest")
        reviewer = _mapping(record.get("reviewer"), f"{context}.reviewer")
        _text(reviewer.get("reviewer_id"), f"{context}.reviewer_id")
        _text(reviewer.get("role"), f"{context}.reviewer.role")
        _text(reviewer.get("competence_basis"), f"{context}.reviewer.competence_basis")
        _clear_conflict(
            reviewer.get("conflict_declaration"), f"{context}.reviewer.conflict_declaration"
        )
        _text(reviewer.get("reviewed_at"), f"{context}.reviewer.reviewed_at")
        review = _mapping(record.get("review"), f"{context}.review")
        disposition = _text(review.get("disposition"), f"{context}.review.disposition")
        allowed_dispositions = review.get("allowed_dispositions")
        if not isinstance(allowed_dispositions, list) or disposition not in allowed_dispositions:
            _fail(f"{context}.review.disposition is not in its declared allowed set")
        _text(review.get("rationale"), f"{context}.review.rationale")
        if disposition == "approved_for_candidate_annotation":
            if source.get("sha256") is None:
                _fail(f"{context} approves a source without an exact source digest")
            if (
                _sha(
                    review.get("exact_acquired_copy_sha256_observed"),
                    f"{context}.review.exact_acquired_copy_sha256_observed",
                )
                != source["sha256"]
            ):
                _fail(f"{context} observed copy digest does not match the source manifest")
            for field in (
                "source_work_identity_confirmed",
                "acquired_copy_identity_confirmed",
                "article_or_work_level_licence_confirmed",
                "licence_identifier_confirmed",
                "licence_evidence_uri_confirmed",
                "human_annotation_permitted",
                "derived_annotation_storage_permitted",
                "evaluation_use_permitted",
                "attribution_complete_and_correct",
                "named_authors_complete_and_correct",
            ):
                if _bool(review.get(field), f"{context}.review.{field}") is not True:
                    _fail(f"{context} does not explicitly approve {field}")
            if _bool(
                review.get("third_party_material_inside_candidate_passages"),
                f"{context}.review.third_party_material_inside_candidate_passages",
            ):
                excluded = _list(
                    review.get("excluded_passage_locators"),
                    f"{context}.review.excluded_passage_locators",
                )
                if not excluded:
                    _fail(f"{context} has unbounded third-party material in candidate passages")
                _fail(f"{context} cannot approve candidate passages with third-party exclusions")
            if source.get("licence", {}).get("spdx") is None:
                _fail(f"{context} approves a source without a licence identifier")
        integrity = _mapping(record.get("integrity"), f"{context}.integrity")
        _sha(integrity.get("review_record_sha256"), f"{context}.review_record_sha256")
        if integrity["review_record_sha256"] != _record_digest(record, "review_record_sha256"):
            _fail(f"{context} review_record_sha256 is not the record self-digest")
        _text(
            integrity.get("immutable_external_record_uri"),
            f"{context}.immutable_external_record_uri",
        )
        indexed[source_id] = record
    if set(indexed) != set(sources):
        _fail("source rights workset does not cover exactly the source manifest IDs")
    return indexed


def _annotation_binding_expected(
    candidate: Mapping[str, Any], packet_digest: str
) -> dict[str, Any]:
    return {
        "pair_id": candidate["pair_id"],
        "packet_id": candidate["packet_id"],
        "packet_sha256": packet_digest,
        "source_id": candidate["source_id"],
        "source_sha256": candidate["source_digest"],
        "claim_family_id": candidate["claim_family_id"],
        "discipline": candidate["discipline"],
        "candidate_claim": candidate["candidate_claim"],
        "exact_quote": candidate["exact_quote"],
        "context": candidate["context"],
        "source_uri": candidate["source_uri"],
        "acquired_copy_uri": candidate.get("acquired_copy_uri"),
        "licence": candidate["licence"],
        "attribution": candidate.get("attribution"),
    }


def _validate_annotation_file(
    path: Path,
    slot: str,
    pair_by_id: Mapping[str, Mapping[str, Any]],
    packet_digests: Mapping[str, str],
    rights_by_source: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    rows = _load_jsonl(path, f"T070 annotator {slot} workset")
    if len(rows) != len(pair_by_id):
        _fail(f"annotator {slot} workset count does not match candidate pairs")
    indexed: dict[str, dict[str, Any]] = {}
    identities: set[str] = set()
    for index, value in enumerate(rows, 1):
        record = dict(_mapping(value, f"annotator {slot} record {index}"))
        context = f"annotator {slot} record {index}"
        if record.get("schema_version") != T070_ANNOTATION_SCHEMA:
            _fail(f"{context} has an unsupported schema")
        if record.get("status") not in HUMAN_REVIEW_STATUSES:
            _fail(f"{context} is not marked as completed human review")
        if FORBIDDEN_HUMAN_KEYS.intersection(record):
            _fail(f"{context} exposes acquisition or semantic partition intent")
        binding = _mapping(record.get("pair_binding"), f"{context}.pair_binding")
        pair_id = _text(binding.get("pair_id"), f"{context}.pair_id")
        if pair_id in indexed:
            _fail(f"duplicate annotator {slot} record for pair {pair_id}")
        candidate = pair_by_id.get(pair_id)
        if candidate is None:
            _fail(f"annotator {slot} record references unknown pair {pair_id}")
        expected_binding = _annotation_binding_expected(candidate, packet_digests[pair_id])
        for key, expected in expected_binding.items():
            if binding.get(key) != expected:
                _fail(f"{context}.{key} does not match the immutable candidate pair")
        rights_binding = _mapping(
            record.get("source_rights_review_binding"),
            f"{context}.source_rights_review_binding",
        )
        source_id = candidate["source_id"]
        rights_record = rights_by_source.get(source_id)
        if rights_record is None:
            _fail(f"{context} has no source-rights review")
        rights_integrity = _mapping(rights_record["integrity"], f"rights {source_id}.integrity")
        if rights_binding.get("review_record_id") != f"rights:{source_id}":
            _fail(f"{context} has a non-deterministic rights review record ID")
        if rights_binding.get("review_record_sha256") != rights_integrity.get(
            "review_record_sha256"
        ):
            _fail(f"{context} is bound to a different rights review record")
        if rights_binding.get("status_required") != "approved_for_candidate_annotation":
            _fail(f"{context} does not require approved candidate annotation rights")
        annotation = _mapping(record.get("annotation"), f"{context}.annotation")
        annotator_id = _text(annotation.get("annotator_id"), f"{context}.annotator_id")
        identities.add(annotator_id)
        _text(annotation.get("annotator_role"), f"{context}.annotator_role")
        _text(annotation.get("competence_basis"), f"{context}.competence_basis")
        _text(annotation.get("independence_attestation"), f"{context}.independence_attestation")
        _clear_conflict(annotation.get("conflict_declaration"), f"{context}.conflict_declaration")
        _text(annotation.get("reviewed_at"), f"{context}.reviewed_at")
        if annotation.get("decision_origin") != "human":
            _fail(f"{context} has no explicit human decision origin")
        _require_exact_list(
            annotation.get("allowed_labels"), T070_LABELS, f"{context}.allowed_labels"
        )
        if annotation.get("label") not in T070_LABELS:
            _fail(f"{context}.label is not an allowed T070 label")
        _text(annotation.get("rationale"), f"{context}.rationale")
        _text(annotation.get("quote_support_locator"), f"{context}.quote_support_locator")
        _text(annotation.get("disposition"), f"{context}.disposition")
        integrity = _mapping(record.get("integrity"), f"{context}.integrity")
        _sha(integrity.get("record_sha256"), f"{context}.record_sha256")
        if integrity["record_sha256"] != _record_digest(record, "record_sha256"):
            _fail(f"{context} record_sha256 is not the record self-digest")
        _text(
            integrity.get("signed_or_immutable_external_record_uri"),
            f"{context}.signed_or_immutable_external_record_uri",
        )
        indexed[pair_id] = record
    if set(indexed) != set(pair_by_id):
        _fail(f"annotator {slot} workset does not cover every candidate pair exactly once")
    if len(identities) != 1:
        _fail(f"annotator {slot} workset contains more than one annotator identity")
    return indexed, identities


def _validate_adjudications(
    path: Path,
    pair_by_id: Mapping[str, Mapping[str, Any]],
    packet_digests: Mapping[str, str],
    annotations_a: Mapping[str, Mapping[str, Any]],
    annotations_b: Mapping[str, Mapping[str, Any]],
    annotator_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    rows = _load_jsonl(path, "T070 adjudication workset")
    if len(rows) != len(pair_by_id):
        _fail("adjudication workset count does not match candidate pairs")
    indexed: dict[str, dict[str, Any]] = {}
    adjudicator_ids: set[str] = set()
    for index, value in enumerate(rows, 1):
        record = dict(_mapping(value, f"adjudication record {index}"))
        context = f"adjudication record {index}"
        if record.get("schema_version") != T070_ADJUDICATION_SCHEMA:
            _fail(f"{context} has an unsupported schema")
        if record.get("status") not in HUMAN_REVIEW_STATUSES:
            _fail(f"{context} is not marked as completed human review")
        binding = _mapping(record.get("pair_binding"), f"{context}.pair_binding")
        pair_id = _text(binding.get("pair_id"), f"{context}.pair_id")
        if pair_id in indexed:
            _fail(f"duplicate adjudication for pair {pair_id}")
        candidate = pair_by_id.get(pair_id)
        if candidate is None:
            _fail(f"adjudication references unknown pair {pair_id}")
        expected = {
            "pair_id": pair_id,
            "packet_sha256": packet_digests[pair_id],
            "source_sha256": candidate["source_digest"],
            "claim_family_id": candidate["claim_family_id"],
        }
        for key, expected_value in expected.items():
            if binding.get(key) != expected_value:
                _fail(f"{context}.{key} does not match the immutable candidate pair")
        annotation_bindings = record.get("annotation_bindings")
        if not isinstance(annotation_bindings, list) or len(annotation_bindings) != 2:
            _fail(f"{context} must bind exactly two annotations")
        by_slot: dict[str, Mapping[str, Any]] = {}
        for item in annotation_bindings:
            item = _mapping(item, f"{context}.annotation_binding")
            slot = _text(item.get("slot"), f"{context}.annotation_binding.slot")
            if slot not in {"A", "B"} or slot in by_slot:
                _fail(f"{context} annotation slots must be exactly A and B")
            by_slot[slot] = item
        if set(by_slot) != {"A", "B"}:
            _fail(f"{context} annotation slots must be exactly A and B")
        for slot, annotation_records in (("A", annotations_a), ("B", annotations_b)):
            annotation_record = annotation_records[pair_id]
            annotation = _mapping(annotation_record["annotation"], f"{context}.{slot}.annotation")
            expected_id = _text(annotation.get("annotator_id"), f"{context}.{slot}.annotator_id")
            binding_item = by_slot[slot]
            if binding_item.get("annotator_id") != expected_id:
                _fail(f"{context}.{slot} annotator identity does not match annotation")
            if binding_item.get("annotation_record_id") != f"annotation:{expected_id}:{pair_id}":
                _fail(f"{context}.{slot} annotation record ID is not deterministic")
            annotation_integrity = _mapping(
                annotation_record["integrity"], f"{context}.{slot}.integrity"
            )
            if binding_item.get("annotation_record_sha256") != annotation_integrity.get(
                "record_sha256"
            ):
                _fail(f"{context}.{slot} binds a different annotation record")
        adjudication = _mapping(record.get("adjudication"), f"{context}.adjudication")
        adjudicator_id = _text(adjudication.get("adjudicator_id"), f"{context}.adjudicator_id")
        adjudicator_ids.add(adjudicator_id)
        if adjudicator_id in annotator_ids:
            _fail(f"{context} adjudicator must be distinct from both annotators")
        _text(adjudication.get("adjudicator_role"), f"{context}.adjudicator_role")
        _text(adjudication.get("competence_basis"), f"{context}.competence_basis")
        _text(adjudication.get("independence_attestation"), f"{context}.independence_attestation")
        _clear_conflict(adjudication.get("conflict_declaration"), f"{context}.conflict_declaration")
        _text(adjudication.get("reviewed_at"), f"{context}.reviewed_at")
        if adjudication.get("decision_origin") != "human":
            _fail(f"{context} has no explicit human decision origin")
        if type(adjudication.get("annotation_agreement_before_adjudication")) is not bool:
            _fail(f"{context} must record annotation agreement explicitly")
        _require_exact_list(
            adjudication.get("allowed_labels"), T070_LABELS, f"{context}.allowed_labels"
        )
        final_label = adjudication.get("final_label")
        if final_label not in T070_LABELS:
            _fail(f"{context}.final_label is not an allowed T070 label")
        _text(adjudication.get("rationale"), f"{context}.rationale")
        _text(adjudication.get("disposition"), f"{context}.disposition")
        integrity = _mapping(record.get("integrity"), f"{context}.integrity")
        _sha(integrity.get("record_sha256"), f"{context}.record_sha256")
        if integrity["record_sha256"] != _record_digest(record, "record_sha256"):
            _fail(f"{context} record_sha256 is not the record self-digest")
        _text(
            integrity.get("signed_or_immutable_external_record_uri"),
            f"{context}.signed_or_immutable_external_record_uri",
        )
        indexed[pair_id] = record
    if set(indexed) != set(pair_by_id):
        _fail("adjudication workset does not cover every candidate pair exactly once")
    if len(adjudicator_ids) != 1:
        _fail("adjudication workset contains more than one adjudicator identity")
    return indexed, adjudicator_ids


def _build_rows(
    candidates: Sequence[Mapping[str, Any]],
    packet_digests: Mapping[str, str],
    annotations_a: Mapping[str, Mapping[str, Any]],
    annotations_b: Mapping[str, Mapping[str, Any]],
    adjudications: Mapping[str, Mapping[str, Any]],
    rights_by_source: Mapping[str, Mapping[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    used_sources: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        pair_id = str(candidate["pair_id"])
        annotation_records = (annotations_a[pair_id], annotations_b[pair_id])
        adjudication_record = adjudications[pair_id]
        adjudication = _mapping(adjudication_record["adjudication"], f"adjudication {pair_id}")
        source_id = str(candidate["source_id"])
        source = sources[source_id]
        rights_record = rights_by_source[source_id]
        rights_review = _mapping(rights_record["review"], f"rights {source_id}.review")
        if rights_review.get("disposition") != "approved_for_candidate_annotation":
            _fail(f"pair {pair_id} is bound to a source without candidate-annotation approval")
        source_digest = source.get("sha256")
        if not isinstance(source_digest, str):
            _fail(f"pair {pair_id} source has no exact source digest")
        if candidate.get("source_digest") != source_digest:
            _fail(f"pair {pair_id} source digest disagrees with source manifest")
        licence_metadata = _mapping(source.get("licence"), f"source {source_id}.licence")
        licence = _text(licence_metadata.get("spdx"), f"source {source_id}.licence.spdx")
        if candidate.get("licence") != licence:
            _fail(f"pair {pair_id} licence disagrees with source rights metadata")
        annotations = []
        for annotation_record in annotation_records:
            annotation = _mapping(annotation_record["annotation"], f"annotation {pair_id}")
            annotations.append(
                {
                    "annotator_id": annotation["annotator_id"],
                    "label": annotation["label"],
                    "rationale": annotation["rationale"],
                    "competence_basis": annotation["competence_basis"],
                    "independence_attestation": annotation["independence_attestation"],
                    "conflict_declaration": annotation["conflict_declaration"],
                    "record_sha256": _mapping(
                        annotation_record["integrity"], f"annotation {pair_id}.integrity"
                    )["record_sha256"],
                }
            )
        row = {
            "pair_id": candidate["pair_id"],
            "claim": candidate["candidate_claim"],
            "exact_quote": candidate["exact_quote"],
            "discipline": candidate["discipline"],
            "source_id": source_id,
            "source_uri": candidate["source_uri"],
            "source_digest": candidate["source_digest"],
            "licence": licence,
            "attribution": candidate.get("attribution"),
            "group_id": candidate["group_id"],
            "claim_family_id": candidate["claim_family_id"],
            "label": adjudication["final_label"],
            "annotations": annotations,
            "adjudication": {
                "status": "adjudicated",
                "label": adjudication["final_label"],
                "adjudicator_id": adjudication["adjudicator_id"],
                "rationale": adjudication["rationale"],
                "competence_basis": adjudication["competence_basis"],
                "independence_attestation": adjudication["independence_attestation"],
                "conflict_declaration": adjudication["conflict_declaration"],
                "record_sha256": _mapping(
                    adjudication_record["integrity"], f"adjudication {pair_id}.integrity"
                )["record_sha256"],
            },
            "review_evidence_binding": {
                "candidate_packet_sha256": packet_digests[pair_id],
                "source_rights_review_sha256": _mapping(
                    rights_record["integrity"], f"rights {source_id}.integrity"
                )["review_record_sha256"],
                "annotation_record_sha256": [item["record_sha256"] for item in annotations],
                "adjudication_record_sha256": _mapping(
                    adjudication_record["integrity"], f"adjudication {pair_id}.integrity"
                )["record_sha256"],
            },
        }
        if "semantic_split" in candidate:
            row["semantic_split"] = copy.deepcopy(candidate["semantic_split"])
        try:
            validate_pair_record(row)
        except DatasetValidationError as exc:
            _fail(f"pair {pair_id} is not compatible with the production dataset contract: {exc}")
        used_sources[source_id] = {
            "source_id": source_id,
            "uri": source["stable_uri"],
            "digest": source_digest,
            "licence": licence,
            "attribution": source.get("attribution"),
            "allowed_use": list(DATASET_USES),
            "review_record_sha256": _mapping(
                rights_record["integrity"], f"rights {source_id}.integrity"
            )["review_record_sha256"],
            "reviewer_id": _mapping(rights_record["reviewer"], f"rights {source_id}.reviewer")[
                "reviewer_id"
            ],
        }
        rows.append(row)
    for row in rows:
        try:
            validate_pair_source_binding(row, used_sources)
        except DatasetValidationError as exc:
            _fail(f"pair {row['pair_id']} failed staged source binding: {exc}")
    return rows, used_sources


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def import_completed_reviews(
    *,
    candidate_pairs: Path,
    source_manifest: Path,
    rights_review: Path,
    workset_manifest: Path,
    annotator_a: Path,
    annotator_b: Path,
    adjudication: Path,
    package_manifest: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Validate and atomically write a release-blocked T070 import staging set."""

    paths = {
        name: Path(value).resolve()
        for name, value in {
            "candidate_pairs": candidate_pairs,
            "source_manifest": source_manifest,
            "rights_review": rights_review,
            "workset_manifest": workset_manifest,
            "annotator_a": annotator_a,
            "annotator_b": annotator_b,
            "adjudication": adjudication,
            "package_manifest": package_manifest,
            "output_dir": output_dir,
        }.items()
    }
    for name, path in paths.items():
        if name != "output_dir" and not path.is_file():
            _fail(f"{name} input does not exist: {path}")
    package, package_inputs = _validate_package(
        paths["package_manifest"],
        paths["candidate_pairs"],
        paths["source_manifest"],
        paths["rights_review"],
        paths["annotator_a"],
        paths["annotator_b"],
        paths["adjudication"],
    )
    _validate_workset_manifest(
        paths["workset_manifest"],
        paths["candidate_pairs"],
        paths["rights_review"],
        paths["annotator_a"],
        paths["annotator_b"],
        paths["adjudication"],
        package["pair_count"],
    )
    candidates, pair_by_id, packet_digests = _validate_candidates(
        paths["candidate_pairs"], package["pair_count"]
    )
    sources = _validate_source_manifest(paths["source_manifest"], package["source_count"])
    rights_by_source = _validate_rights_reviews(
        paths["rights_review"], package_inputs["source_manifest_sha256"], sources
    )
    candidate_source_ids = {str(row["source_id"]) for row in candidates}
    for source_id in sorted(candidate_source_ids):
        rights = rights_by_source.get(source_id)
        if rights is None:
            _fail(f"candidate source {source_id} has no rights review")
        review = _mapping(rights["review"], f"rights {source_id}.review")
        if review.get("disposition") != "approved_for_candidate_annotation":
            _fail(f"candidate source {source_id} is not approved for annotation")
    annotations_a, annotator_ids_a = _validate_annotation_file(
        paths["annotator_a"], "A", pair_by_id, packet_digests, rights_by_source
    )
    annotations_b, annotator_ids_b = _validate_annotation_file(
        paths["annotator_b"], "B", pair_by_id, packet_digests, rights_by_source
    )
    if annotator_ids_a.intersection(annotator_ids_b):
        _fail("annotator A and B identities must be distinct")
    adjudications, adjudicator_ids = _validate_adjudications(
        paths["adjudication"],
        pair_by_id,
        packet_digests,
        annotations_a,
        annotations_b,
        annotator_ids_a.union(annotator_ids_b),
    )
    rows, used_sources = _build_rows(
        candidates,
        packet_digests,
        annotations_a,
        annotations_b,
        adjudications,
        rights_by_source,
        sources,
    )

    output = paths["output_dir"]
    if output.exists():
        _fail(f"refusing to overwrite existing T070 import directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        pairs_path = temporary / "pairs.jsonl"
        source_licence_path = temporary / "source-licence-manifest.json"
        _write_jsonl(pairs_path, rows)
        staged_source_manifest = {
            "schema_version": "2.0.0",
            "status": "pending_independent_dataset_approval",
            "manifest_type": "t070_imported_source_licence_manifest",
            "sources": list(used_sources.values()),
            "approval": {
                "status": "pending_independent_dataset_approval",
                "reviewer_id": None,
                "record_uri": None,
            },
            "release_evidence": False,
            "policy": "Allowed uses are mapped to all five governed dataset partitions only after the human review explicitly permits evaluation use; bytes remain governed by the source licence.",
        }
        _write_json(source_licence_path, staged_source_manifest)
        manifest = {
            "schema_version": "research-handoff.t070.imported-human-reviews.v1",
            "status": "READY_FOR_DATASET_APPROVAL_NOT_RELEASE_EVIDENCE",
            "release_evidence": False,
            "exact_candidate_head": package["exact_candidate_head"],
            "source_workflow_head": package["source_workflow_head"],
            "candidate_source_count": package["source_count"],
            "source_count": len(used_sources),
            "pair_count": len(rows),
            "input_bindings": {
                "package_manifest_sha256": sha256_file(paths["package_manifest"]),
                "candidate_pairs_sha256": package_inputs["candidate_pairs_sha256"],
                "source_manifest_sha256": package_inputs["source_manifest_sha256"],
                "workset_manifest_sha256": sha256_file(paths["workset_manifest"]),
                "rights_review_sha256": sha256_file(paths["rights_review"]),
                "annotator_A_sha256": sha256_file(paths["annotator_a"]),
                "annotator_B_sha256": sha256_file(paths["annotator_b"]),
                "adjudication_sha256": sha256_file(paths["adjudication"]),
            },
            "review_identities": {
                "annotator_A": sorted(annotator_ids_a),
                "annotator_B": sorted(annotator_ids_b),
                "adjudicator": sorted(adjudicator_ids),
                "source_rights_reviewers": sorted(
                    {
                        str(_mapping(record["reviewer"], "rights reviewer")["reviewer_id"])
                        for record in rights_by_source.values()
                        if _mapping(record["review"], "rights review").get("disposition")
                        == "approved_for_candidate_annotation"
                    }
                ),
            },
            "outputs": {
                "pairs": {
                    "path": "pairs.jsonl",
                    "sha256": sha256_file(pairs_path),
                },
                "source_licence_manifest": {
                    "path": "source-licence-manifest.json",
                    "sha256": sha256_file(source_licence_path),
                    "status": staged_source_manifest["status"],
                },
            },
            "promotion_requirements": [
                "independent dataset-level source-rights approval must be recorded",
                "T070 annotation agreement and adjudication evidence must be reviewed under the frozen task authority",
                "T073 locked evaluation and all Research Grade promotion gates remain outstanding",
            ],
        }
        _write_json(temporary / "manifest.json", manifest)
        os.replace(str(temporary), str(output))
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-pairs", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--rights-review", type=Path, required=True)
    parser.add_argument("--workset-manifest", type=Path, required=True)
    parser.add_argument("--annotator-a", type=Path, required=True)
    parser.add_argument("--annotator-b", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--package-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = import_completed_reviews(
            candidate_pairs=args.candidate_pairs,
            source_manifest=args.source_manifest,
            rights_review=args.rights_review,
            workset_manifest=args.workset_manifest,
            annotator_a=args.annotator_a,
            annotator_b=args.annotator_b,
            adjudication=args.adjudication,
            package_manifest=args.package_manifest,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "IMPORT_REFUSED", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": result["status"],
                "pair_count": result["pair_count"],
                "source_count": result["source_count"],
                "release_evidence": result["release_evidence"],
                "output_dir": str(args.output_dir.resolve()),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
