#!/usr/bin/env python3
"""Import completed human T111 reviews into a provider-evaluation candidate manifest.

The importer is deliberately stricter than the blank-packet generator. It binds
every review to the exact candidate-manifest bytes and every reviewed asset to its
canonical record and byte digest. All six T111 review legs must be present as
explicit human decisions before a provider-evaluation manifest is emitted. The
output is still ``release_evidence=false``: a subsequent independent provider
run and the frozen T111 gates remain required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

RIGHTS_ACTIONS = (
    "view",
    "analyse",
    "transform",
    "create_derivative",
    "quote",
    "cache",
    "export",
    "redistribute",
)
ANALYSIS_STATUSES = frozenset({"complete", "partial", "insufficient", "denied", "error"})
REVIEW_SCHEMA = "research-handoff.t111.independent-review.v1"
CANDIDATE_SCHEMA = "research-handoff.t111.review-candidate-corpus.v1"
OUTPUT_SCHEMA = "2.0.0"
MINIMUMS = {
    "objects": 60,
    "renditions": 96,
    "region_grounding_claims": 80,
    "region_assets": 20,
    "cross_modal_pairs": 120,
    "discipline_tasks": 48,
    "discipline_works": 24,
    "adversarial_cases": 96,
    "media_material_classes": 6,
    "mediation_conditions": 3,
}
REVIEW_STATUSES = frozenset({"human_reviewed", "completed_human_review"})


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.name


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read JSON input {path}") from exc


def _read_reviews(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() != ".jsonl":
        payload = _read_json(path)
        if isinstance(payload, dict) and isinstance(payload.get("reviews"), list):
            values = payload["reviews"]
        elif isinstance(payload, list):
            values = payload
        else:
            values = [payload]
    else:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"unable to read review JSONL {path}") from exc
        values = []
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"review JSONL line {line_number} is invalid JSON") from exc
    if not values or not all(isinstance(value, dict) for value in values):
        raise ValueError("completed T111 reviews must be one or more JSON objects")
    return [dict(value) for value in values]


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty human-supplied string")
    return value


def _require_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be an explicit human boolean")
    return value


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return dict(value)


def _require_ids(value: Any, field: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item for item in value)
    ):
        raise ValueError(f"{field} must be a non-empty list of IDs")
    result = [str(item) for item in value]
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicate IDs")
    return result


def _object_digest(asset: Mapping[str, Any]) -> str:
    return canonical_digest(
        {
            "object_id": str(asset["object_id"]),
            "institution": asset["institution"],
            "object_source_uri": asset["object_source_uri"],
        }
    )


def _without_asset_digest(asset: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(asset)
    value.pop("asset_record_sha256", None)
    return value


def load_candidate_manifest(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    if not isinstance(value, dict) or value.get("schema_version") != CANDIDATE_SCHEMA:
        raise ValueError("unsupported T111 review-candidate manifest")
    if value.get("status") != "READY_FOR_INDEPENDENT_HUMAN_REVIEW_NOT_T111_EVIDENCE":
        raise ValueError("T111 candidate manifest is not at the human-review boundary")
    if value.get("release_evidence") is not False or value.get("human_review") is not None:
        raise ValueError("T111 candidate manifest must remain a blank non-release candidate")
    assets = value.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("T111 candidate manifest has no assets")
    asset_ids: set[str] = set()
    byte_digests: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("T111 candidate asset is not an object")
        asset_id = _require_text(asset.get("asset_id"), "asset_id")
        if asset_id in asset_ids:
            raise ValueError(f"duplicate T111 asset_id: {asset_id}")
        asset_ids.add(asset_id)
        _require_text(asset.get("object_id"), f"{asset_id}.object_id")
        for field in (
            "institution",
            "source_uri",
            "object_source_uri",
            "rights_uri",
            "attribution_statement",
            "required_licence_statement",
        ):
            _require_text(asset.get(field), f"{asset_id}.{field}")
        digest = _require_sha256(asset.get("byte_digest"), f"{asset_id}.byte_digest")
        if digest in byte_digests:
            raise ValueError(f"duplicate T111 rendition byte digest: {asset_id}")
        byte_digests.add(digest)
        if type(asset.get("byte_size")) is not int or asset["byte_size"] <= 0:
            raise ValueError(f"{asset_id}.byte_size must be a positive integer")
        if type(asset.get("width")) is not int or asset["width"] <= 0:
            raise ValueError(f"{asset_id}.width must be a positive integer")
        if type(asset.get("height")) is not int or asset["height"] <= 0:
            raise ValueError(f"{asset_id}.height must be a positive integer")
        expected_object_digest = _object_digest(asset)
        if asset.get("object_record_sha256") != expected_object_digest:
            raise ValueError(f"{asset_id}.object_record_sha256 does not match the candidate object")
        expected_asset_digest = canonical_digest(_without_asset_digest(asset))
        if asset.get("asset_record_sha256") != expected_asset_digest:
            raise ValueError(f"{asset_id}.asset_record_sha256 does not match the candidate asset")
        if (
            asset.get("human_rights_review") is not None
            or asset.get("human_identity_review") is not None
        ):
            raise ValueError(f"{asset_id} unexpectedly contains human review truth")
        actions = asset.get("allowed_actions")
        if (
            not isinstance(actions, list)
            or not actions
            or not set(actions).issubset(RIGHTS_ACTIONS)
        ):
            raise ValueError(f"{asset_id}.allowed_actions is invalid")
    candidate_ids = {
        "regions": _candidate_ids(value, "region_grounding_candidates", "region_claim_id"),
        "cross": _candidate_ids(value, "cross_modal_candidates", "pair_id"),
        "discipline": _candidate_ids(value, "discipline_task_candidates", "task_id"),
        "adversarial": _candidate_ids(value, "adversarial_candidates", "case_id"),
        "accessibility": _candidate_ids(value, "accessibility_candidates", "accessibility_id"),
    }
    if len({str(asset["object_id"]) for asset in assets}) < 1:
        raise ValueError("T111 candidate manifest has no object identities")
    return {
        **value,
        "_asset_map": {asset["asset_id"]: asset for asset in assets},
        "_candidate_ids": candidate_ids,
    }


def _candidate_ids(manifest: Mapping[str, Any], field: str, id_field: str) -> set[str]:
    values = manifest.get(field)
    if not isinstance(values, list) or not values:
        raise ValueError(f"T111 candidate manifest lacks {field}")
    result: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            raise ValueError(f"{field} contains a non-object")
        item_id = _require_text(item.get(id_field), f"{field}.{id_field}")
        if item_id in result:
            raise ValueError(f"duplicate T111 candidate ID: {item_id}")
        result.add(item_id)
    return result


def _validate_leg_origin(leg: Mapping[str, Any], name: str) -> None:
    if leg.get("decision_origin") != "human":
        raise ValueError(f"{name} lacks human decision origin")
    _require_text(leg.get("rationale"), f"{name}.rationale")


def _validate_decisions(
    leg: Mapping[str, Any],
    *,
    list_field: str,
    decision_field: str,
    expected_ids: set[str],
    name: str,
) -> dict[str, dict[str, Any]]:
    _validate_leg_origin(leg, name)
    ids = set(_require_ids(leg.get(list_field), f"{name}.{list_field}"))
    decisions = leg.get(decision_field)
    if not isinstance(decisions, Mapping):
        raise ValueError(f"{name}.{decision_field} must be an object")
    normalized = {
        str(key): dict(value) for key, value in decisions.items() if isinstance(value, Mapping)
    }
    if len(normalized) != len(decisions) or set(normalized) != ids:
        raise ValueError(f"{name} decisions do not exactly match reviewed IDs")
    if not ids.issubset(expected_ids):
        raise ValueError(f"{name} contains an unknown candidate ID")
    return normalized


def validate_review_record(
    record: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_manifest_sha256: str,
) -> dict[str, Any]:
    value = dict(record)
    if value.get("schema_version") != REVIEW_SCHEMA:
        raise ValueError("unsupported T111 independent review schema")
    if value.get("status") not in REVIEW_STATUSES:
        raise ValueError("T111 review is not marked as completed human review")
    if value.get("release_evidence") is not False:
        raise ValueError("T111 review must keep release_evidence=false")
    if value.get("candidate_manifest_sha256") != candidate_manifest_sha256:
        raise ValueError("T111 review candidate manifest digest does not match exact input bytes")
    _require_text(value.get("review_id"), "review_id")
    object_binding = _require_mapping(value.get("object_binding"), "object_binding")
    asset_map = candidate["_asset_map"]
    object_id = str(object_binding.get("object_id") or "")
    if not object_id:
        raise ValueError("T111 review object binding lacks object_id")
    assets = value.get("asset_bindings")
    if not isinstance(assets, list) or not assets:
        raise ValueError("T111 review has no asset bindings")
    bound_asset_ids: set[str] = set()
    for binding in assets:
        binding = _require_mapping(binding, "asset_binding")
        asset_id = _require_text(binding.get("asset_id"), "asset_binding.asset_id")
        if asset_id in bound_asset_ids:
            raise ValueError(f"duplicate T111 review asset binding: {asset_id}")
        if asset_id not in asset_map:
            raise ValueError(f"T111 review binds unknown asset: {asset_id}")
        bound_asset_ids.add(asset_id)
        expected = asset_map[asset_id]
        if str(binding.get("object_id") or expected["object_id"]) != str(expected["object_id"]):
            raise ValueError(f"{asset_id}: review object binding mismatch")
        if binding.get("object_record_sha256") != expected["object_record_sha256"]:
            raise ValueError(f"{asset_id}: review object digest mismatch")
        if binding.get("asset_record_sha256") != expected["asset_record_sha256"]:
            raise ValueError(f"{asset_id}: review asset digest mismatch")
        if (
            binding.get("source_uri") != expected["source_uri"]
            or binding.get("rights_uri") != expected["rights_uri"]
        ):
            raise ValueError(f"{asset_id}: review source/right URI mismatch")
        if binding.get("byte_sha256") != expected["byte_digest"]:
            raise ValueError(f"{asset_id}: review byte digest mismatch")
        expected_parent = (expected.get("derivative_lineage") or {}).get("parent_byte_digest")
        if binding.get("derivative_parent_sha256") != expected_parent:
            raise ValueError(f"{asset_id}: review derivative lineage mismatch")

    reviewer = _require_mapping(value.get("reviewer"), "reviewer")
    for field in (
        "reviewer_id",
        "role",
        "discipline_competence_basis",
        "independence_attestation",
        "reviewed_at",
    ):
        _require_text(reviewer.get(field), f"reviewer.{field}")
    _require_text(
        reviewer.get("rights_review_competence_basis"), "reviewer.rights_review_competence_basis"
    )
    conflict = _require_mapping(
        reviewer.get("conflict_declaration"), "reviewer.conflict_declaration"
    )
    if conflict.get("has_conflict") is not False:
        raise ValueError("T111 reviewer conflict declaration is not explicit and clear")
    if reviewer.get("decision_origin") != "human":
        raise ValueError("T111 reviewer identity lacks human decision origin")

    rights = _require_mapping(value.get("rights_review"), "rights_review")
    _validate_leg_origin(rights, "rights_review")
    for field in (
        "object_asset_identity_correct",
        "rights_designation_verified",
        "third_party_restrictions_checked",
        "attribution_or_credit_correct",
        "derivative_lineage_correct",
    ):
        _require_bool(rights.get(field), f"rights_review.{field}")
    if rights.get("disposition") != "admit":
        raise ValueError("T111 rights review is not admitted; obtain a reviewed replacement")
    verified_actions = rights.get("allowed_actions_verified")
    if (
        not isinstance(verified_actions, list)
        or not verified_actions
        or not set(verified_actions).issubset(RIGHTS_ACTIONS)
    ):
        raise ValueError("rights_review.allowed_actions_verified is invalid")
    if "analyse" not in verified_actions:
        raise ValueError("T111 rights review does not explicitly permit analyse")

    candidate_ids = candidate["_candidate_ids"]
    grounding = _validate_decisions(
        _require_mapping(value.get("grounding_review"), "grounding_review"),
        list_field="region_claim_records_reviewed",
        decision_field="decisions",
        expected_ids=candidate_ids["regions"],
        name="grounding_review",
    )
    for item_id, decision in grounding.items():
        _require_text(
            decision.get("observation"), f"grounding_review.decisions.{item_id}.observation"
        )
        _require_ids(
            decision.get("observation_ids"), f"grounding_review.decisions.{item_id}.observation_ids"
        )
        _require_bool(
            decision.get("grounding_correct"),
            f"grounding_review.decisions.{item_id}.grounding_correct",
        )
        _require_text(decision.get("rationale"), f"grounding_review.decisions.{item_id}.rationale")
        region = decision.get("expected_region")
        if (
            not isinstance(region, list)
            or len(region) != 4
            or not all(type(value) is int for value in region)
        ):
            raise ValueError(f"grounding_review.decisions.{item_id}.expected_region is invalid")

    cross = _validate_decisions(
        _require_mapping(value.get("cross_modal_review"), "cross_modal_review"),
        list_field="pair_records_reviewed",
        decision_field="decisions",
        expected_ids=candidate_ids["cross"],
        name="cross_modal_review",
    )
    for item_id, decision in cross.items():
        _require_bool(
            decision.get("expected_supported"),
            f"cross_modal_review.decisions.{item_id}.expected_supported",
        )
        _require_text(decision.get("relation"), f"cross_modal_review.decisions.{item_id}.relation")
        _require_text(
            decision.get("rationale"), f"cross_modal_review.decisions.{item_id}.rationale"
        )

    discipline = _validate_decisions(
        _require_mapping(value.get("discipline_review"), "discipline_review"),
        list_field="task_records_reviewed",
        decision_field="decisions",
        expected_ids=candidate_ids["discipline"],
        name="discipline_review",
    )
    for item_id, decision in discipline.items():
        _require_bool(
            decision.get("appropriate"), f"discipline_review.decisions.{item_id}.appropriate"
        )
        _require_text(
            decision.get("expected_answer"),
            f"discipline_review.decisions.{item_id}.expected_answer",
        )
        _require_text(decision.get("rationale"), f"discipline_review.decisions.{item_id}.rationale")

    accessibility = _validate_decisions(
        _require_mapping(value.get("accessibility_review"), "accessibility_review"),
        list_field="accessibility_records_reviewed",
        decision_field="decisions",
        expected_ids=candidate_ids["accessibility"],
        name="accessibility_review",
    )
    for item_id, decision in accessibility.items():
        if decision.get("purpose") not in {"decorative", "functional", "evidentiary"}:
            raise ValueError(f"accessibility_review.decisions.{item_id}.purpose is invalid")
        _require_text(
            decision.get("short_alternative"),
            f"accessibility_review.decisions.{item_id}.short_alternative",
        )
        if decision["purpose"] == "evidentiary":
            _require_text(
                decision.get("long_description"),
                f"accessibility_review.decisions.{item_id}.long_description",
            )
        _require_bool(
            decision.get("fit_for_purpose"),
            f"accessibility_review.decisions.{item_id}.fit_for_purpose",
        )
        if decision.get("human_validated") is not True:
            raise ValueError(
                f"accessibility_review.decisions.{item_id}.human_validated must be true"
            )
        _require_text(
            decision.get("rationale"), f"accessibility_review.decisions.{item_id}.rationale"
        )

    adversarial = _validate_decisions(
        _require_mapping(value.get("adversarial_review"), "adversarial_review"),
        list_field="case_records_reviewed",
        decision_field="decisions",
        expected_ids=candidate_ids["adversarial"],
        name="adversarial_review",
    )
    for item_id, decision in adversarial.items():
        _require_bool(
            decision.get("unsafe_or_false"),
            f"adversarial_review.decisions.{item_id}.unsafe_or_false",
        )
        _require_text(
            decision.get("expected_disposition"),
            f"adversarial_review.decisions.{item_id}.expected_disposition",
        )
        _require_text(
            decision.get("rationale"), f"adversarial_review.decisions.{item_id}.rationale"
        )

    expectations = value.get("evaluation_expectations")
    if not isinstance(expectations, Mapping) or set(expectations) != bound_asset_ids:
        raise ValueError("T111 evaluation_expectations must cover exactly the reviewed assets")
    normalized_expectations: dict[str, dict[str, Any]] = {}
    for asset_id, expectation in expectations.items():
        expectation = _require_mapping(expectation, f"evaluation_expectations.{asset_id}")
        if expectation.get("status") not in ANALYSIS_STATUSES:
            raise ValueError(f"evaluation_expectations.{asset_id}.status is invalid")
        questions = _require_ids(
            expectation.get("target_questions"),
            f"evaluation_expectations.{asset_id}.target_questions",
        )
        actions = expectation.get("allowed_actions")
        if (
            not isinstance(actions, list)
            or not actions
            or not set(actions).issubset(RIGHTS_ACTIONS)
            or "analyse" not in actions
        ):
            raise ValueError(f"evaluation_expectations.{asset_id}.allowed_actions is invalid")
        if not set(actions).issubset(set(rights["allowed_actions_verified"])):
            raise ValueError(
                f"evaluation_expectations.{asset_id}.allowed_actions exceed human rights review"
            )
        discipline_name = expectation.get("discipline")
        if discipline_name not in {"art_history", "art_criticism"}:
            raise ValueError(f"evaluation_expectations.{asset_id}.discipline is invalid")
        normalized_expectations[asset_id] = {
            **expectation,
            "target_questions": questions,
            "allowed_actions": actions,
        }

    overall = _require_mapping(value.get("overall"), "overall")
    if overall.get("disposition") != "lock" or overall.get("decision_origin") != "human":
        raise ValueError("T111 overall review is not a human lock")
    _require_text(overall.get("rationale"), "overall.rationale")
    if not isinstance(overall.get("limitations"), list):
        raise ValueError("overall.limitations must be an explicit list")
    integrity = _require_mapping(value.get("integrity"), "integrity")
    _require_text(
        integrity.get("immutable_external_record_uri"), "integrity.immutable_external_record_uri"
    )
    if not str(integrity["immutable_external_record_uri"]).startswith("https://"):
        raise ValueError("T111 review integrity URI must be HTTPS")
    recorded_digest = _require_sha256(
        integrity.get("review_record_sha256"), "integrity.review_record_sha256"
    )
    unsigned = json.loads(json.dumps(value))
    unsigned["integrity"]["review_record_sha256"] = None
    if recorded_digest != canonical_digest(unsigned):
        raise ValueError("T111 review record digest does not match immutable fields")
    return {
        **value,
        "_asset_ids": bound_asset_ids,
        "_grounding": grounding,
        "_cross": cross,
        "_discipline": discipline,
        "_accessibility": accessibility,
        "_adversarial": adversarial,
        "_expectations": normalized_expectations,
    }


def _asset_for_evaluation(
    asset: Mapping[str, Any],
    accessibility: Mapping[str, Any],
    *,
    reviewer_id: str,
    review_uri: str,
    review_record_sha256: str,
) -> dict[str, Any]:
    asset_id = str(asset["asset_id"])
    parent = asset.get("derivative_lineage") or {}
    allowed = set(accessibility.get("allowed_actions") or asset.get("allowed_actions") or [])
    rights = {
        action: {
            "status": "allowed" if action in allowed else "denied",
            "source_uri": asset["rights_uri"],
            "review_record_uri": review_uri,
        }
        for action in RIGHTS_ACTIONS
    }
    return {
        "asset_id": asset_id,
        "object_id": str(asset["object_id"]),
        "role": "generated" if parent else "surrogate",
        "mime_type": asset.get("mime_type") or "image/jpeg",
        "byte_size": asset["byte_size"],
        "width": asset["width"],
        "height": asset["height"],
        "byte_digest": asset["byte_digest"],
        "acquisition_uri": asset.get("acquisition_uri") or asset["source_uri"],
        "source_uri": asset["source_uri"],
        "rights": rights,
        "view_conditions": {"mediation_condition": asset["mediation_condition"]},
        "parent_asset_ids": [parent["parent_asset_id"]] if parent else [],
        "parent_digests": [parent["parent_byte_digest"]] if parent else [],
        "provenance": {
            "candidate_asset_record_sha256": asset["asset_record_sha256"],
            "candidate_object_record_sha256": asset["object_record_sha256"],
            "review_record_uri": review_uri,
            "review_record_sha256": review_record_sha256,
            "human_rights_reviewed": True,
        },
        "accessibility": {
            "asset_digest": asset["byte_digest"],
            "purpose": accessibility["purpose"],
            "short_alternative": accessibility["short_alternative"],
            "long_description": accessibility.get("long_description"),
            "origin": "human_reviewed",
            "review_status": "reviewed",
            "reviewer_id": reviewer_id,
            "reviewed_at": accessibility.get("reviewed_at"),
        },
        "generated": bool(parent),
    }


def _case_for_asset(
    asset: Mapping[str, Any],
    candidate: Mapping[str, Any],
    review: Mapping[str, Any],
    evaluation_asset: Mapping[str, Any],
) -> dict[str, Any]:
    asset_id = str(asset["asset_id"])
    expectation = review["_expectations"][asset_id]
    regions = []
    interpretations = []
    region_map = {
        item["region_claim_id"]: item for item in candidate["region_grounding_candidates"]
    }
    for region_id, decision in review["_grounding"].items():
        region = region_map[region_id]
        if region["asset_id"] != asset_id or not decision["grounding_correct"]:
            continue
        regions.append({"asset_id": asset_id, "normalized": decision["expected_region"]})
        interpretations.append(
            {
                "interpretation_id": region_id,
                "observation_ids": list(decision["observation_ids"]),
                "statement": decision["observation"],
            }
        )
    cross = []
    textual = []
    cross_map = {item["pair_id"]: item for item in candidate["cross_modal_candidates"]}
    for pair_id, decision in review["_cross"].items():
        pair = cross_map[pair_id]
        if pair["asset_id"] != asset_id:
            continue
        claim = {
            "claim_id": pair_id,
            "asset_id": asset_id,
            "claim_text": pair["claim_text"],
            "text_source_uri": pair["text_source_uri"],
        }
        cross.append({"claim": claim, "expected_supported": decision["expected_supported"]})
        textual.append(
            {
                "evidence_id": pair_id,
                "text": pair["claim_text"],
                "source_uri": pair["text_source_uri"],
            }
        )
    safety = []
    adversarial_map = {item["case_id"]: item for item in candidate["adversarial_candidates"]}
    for case_id, decision in review["_adversarial"].items():
        case = adversarial_map[case_id]
        if case["asset_id"] != asset_id:
            continue
        safety.append(
            {
                "kind": case["category_intent"],
                "unsafe": decision["unsafe_or_false"],
                "claim": {
                    "claim_id": case_id,
                    "asset_id": asset_id,
                    "claim_text": case["candidate_claim"],
                    "text_source_uri": case["comparison_source_uri"],
                },
            }
        )
    return {
        "case_id": f"T111-{asset_id}",
        "object": {"object_id": str(asset["object_id"])},
        "assets": [dict(evaluation_asset)],
        "request": {
            "work_id": f"T111-work-{asset['object_id']}",
            "run_id": f"T111-run-{asset_id}",
            "object_id": str(asset["object_id"]),
            "target_questions": list(expectation["target_questions"]),
            "allowed_actions": list(expectation["allowed_actions"]),
            "discipline": expectation["discipline"],
            "ontology_binding": dict(expectation.get("ontology_binding") or {}),
            "resource_limits": dict(expectation.get("resource_limits") or {}),
            "provider_policy": dict(expectation.get("provider_policy") or {}),
        },
        "textual_evidence": textual,
        "expected": {
            "status": expectation["status"],
            "regions": regions,
            "interpretations": interpretations,
            "cross_modal_pairs": cross,
            "safety_cases": safety,
            "accessibility_required": True,
        },
    }


def _minimum_failures(candidate: Mapping[str, Any], minimums: Mapping[str, int]) -> list[str]:
    counts = candidate.get("counts") or {}
    aliases = {
        "region_grounding_claims": "region_grounding_candidates",
        "cross_modal_pairs": "cross_modal_candidates",
        "adversarial_cases": "adversarial_candidates",
    }
    failures = []
    for name, threshold in minimums.items():
        observed = counts.get(aliases.get(name, name))
        if not isinstance(observed, int) or observed < threshold:
            failures.append(f"candidate count {name}={observed!r} is below {threshold}")
    return failures


def import_completed_reviews(
    candidate_manifest: Path,
    completed_reviews: Path,
    output_dir: Path,
    *,
    minimums: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    candidate_path = candidate_manifest.resolve()
    candidate = load_candidate_manifest(candidate_path)
    candidate_digest = sha256_file(candidate_path)
    review_records = _read_reviews(completed_reviews.resolve())
    seen_review_ids: set[str] = set()
    seen_assets: set[str] = set()
    seen_leg_ids = {
        name: set() for name in ("grounding", "cross", "discipline", "accessibility", "adversarial")
    }
    validated: list[dict[str, Any]] = []
    for record in review_records:
        review = validate_review_record(record, candidate, candidate_digest)
        review_id = str(review["review_id"])
        if review_id in seen_review_ids:
            raise ValueError(f"duplicate T111 review_id: {review_id}")
        seen_review_ids.add(review_id)
        if seen_assets & review["_asset_ids"]:
            raise ValueError("a T111 asset is bound to more than one completed review")
        seen_assets.update(review["_asset_ids"])
        for name, key in (
            ("grounding", "_grounding"),
            ("cross", "_cross"),
            ("discipline", "_discipline"),
            ("accessibility", "_accessibility"),
            ("adversarial", "_adversarial"),
        ):
            overlap = seen_leg_ids[name] & set(review[key])
            if overlap:
                raise ValueError(
                    f"T111 {name} candidate is reviewed more than once: {sorted(overlap)[0]}"
                )
            seen_leg_ids[name].update(review[key])
        validated.append(review)

    if seen_assets != set(candidate["_asset_map"]):
        missing = sorted(set(candidate["_asset_map"]) - seen_assets)
        raise ValueError(f"T111 completed reviews do not cover every asset; missing {missing[0]}")
    for name, key in (
        ("grounding", "regions"),
        ("cross", "cross"),
        ("discipline", "discipline"),
        ("accessibility", "accessibility"),
        ("adversarial", "adversarial"),
    ):
        if seen_leg_ids[name] != set(candidate["_candidate_ids"][key]):
            missing = sorted(set(candidate["_candidate_ids"][key]) - seen_leg_ids[name])
            raise ValueError(
                f"T111 completed reviews do not cover every {name} candidate; missing {missing[0]}"
            )
    minimum_failures = _minimum_failures(candidate, minimums or MINIMUMS)
    if minimum_failures:
        raise ValueError("; ".join(minimum_failures))

    review_by_asset: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for review in validated:
        reviewer_id = str(review["reviewer"]["reviewer_id"])
        review_uri = str(review["integrity"]["immutable_external_record_uri"])
        for asset_id in review["_asset_ids"]:
            review_by_asset[asset_id] = (
                review,
                {
                    **review["_accessibility"][f"ACC-{asset_id}"],
                    "allowed_actions": review["rights_review"]["allowed_actions_verified"],
                    "reviewed_at": review["reviewer"]["reviewed_at"],
                    "review_uri": review_uri,
                    "review_record_sha256": review["integrity"]["review_record_sha256"],
                    "reviewer_id": reviewer_id,
                },
            )

    evaluation_assets = []
    cases = []
    for asset_id, asset in candidate["_asset_map"].items():
        review, access = review_by_asset[asset_id]
        evaluation_asset = _asset_for_evaluation(
            asset,
            access,
            reviewer_id=access["reviewer_id"],
            review_uri=access["review_uri"],
            review_record_sha256=access["review_record_sha256"],
        )
        evaluation_assets.append(evaluation_asset)
        cases.append(_case_for_asset(asset, candidate, review, evaluation_asset))
    counts = dict(candidate["counts"])
    output = {
        "schema_version": OUTPUT_SCHEMA,
        "manifest_id": "swos-multimodal-evaluation-corpus-v2",
        "status": "ready",
        "release_evidence": False,
        "candidate_manifest_sha256": candidate_digest,
        "candidate_manifest_path": _stable_path(candidate_path),
        "review_record_count": len(validated),
        "checksum_algorithm": "sha256",
        "licence_boundary": "DATA-LICENCE.md",
        "required_counts": {
            name: int(value) for name, value in (minimums or MINIMUMS).items() if name in MINIMUMS
        },
        "required_strata": {
            "media_material_classes": 6,
            "mediation_conditions": 3,
            "disciplines": ["art_history", "art_criticism"],
        },
        "observed_counts": counts,
        "cases": cases,
        "asset_records": evaluation_assets,
        "review": {
            "status": "human_reviewed",
            "human_adjudication": "complete",
            "independent_provider_review": "required",
            "exact_head_binding": "candidate manifest digest bound; code-head/provider evidence still required",
            "review_record_digests": [
                {
                    "review_id": review["review_id"],
                    "review_record_sha256": review["integrity"]["review_record_sha256"],
                    "immutable_external_record_uri": review["integrity"][
                        "immutable_external_record_uri"
                    ],
                }
                for review in validated
            ],
        },
        "warning": "Human review has been imported, but no provider result, T111 PASS, or release evidence is created by this importer.",
    }
    out = output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty T111 reviewed output directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "review-records.jsonl").write_text(
        "".join(
            json.dumps(
                {key: value for key, value in review.items() if not key.startswith("_")},
                sort_keys=True,
            )
            + "\n"
            for review in validated
        ),
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--completed-reviews", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = import_completed_reviews(
            args.candidate_manifest, args.completed_reviews, args.output_dir
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"status": "IMPORT_BLOCKED", "reason": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": result["status"],
                "release_evidence": result["release_evidence"],
                "case_count": len(result["cases"]),
                "output": str(args.output_dir.resolve() / "manifest.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
