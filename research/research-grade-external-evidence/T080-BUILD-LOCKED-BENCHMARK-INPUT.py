#!/usr/bin/env python3
"""Build the frozen T080 input manifest from genuinely locked T079 reviews.

PREPARATION/IMPORT ONLY. This tool never invents a reviewer identity, expected
outcome, material-gap truth, narrow-corpus judgment, or benchmark PASS. It only
binds completed independent reviews to the exact candidate packet digest and
translates the reviewed records into the schema already consumed by
``tools/run_source_diversity_benchmark.py``.

If fewer than ten genuinely locked packets exist for any supported discipline,
the tool fails closed and writes no frozen benchmark input.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

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
PACKET_CATEGORIES = (
    "balanced",
    "concentrated",
    "sparse",
    "narrow",
    "multilingual",
    "historical",
    "method_monoculture",
    "duplicate",
    "fake_diversity",
    "missing_strata",
)
REQUIRED_PER_DISCIPLINE = 10
T079_CANDIDATE_MANIFEST_SCHEMA = "research-handoff.t079.candidate-manifest.v1"
T079_CANDIDATE_SCHEMA = "2.0.0-candidate"
T079_REVIEW_SCHEMA = "research-handoff.t079.independent-review.v1"
HUMAN_REVIEW_STATUSES = frozenset({"human_reviewed", "completed_human_review"})
SHA256_HEX = frozenset("0123456789abcdef")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def candidate_digest(packet: dict[str, Any]) -> str:
    payload = {
        key: value for key, value in packet.items() if key not in {"packet_digest", "review"}
    }
    return sha256_json(payload)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_sha256(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context} must be lowercase SHA-256")
    digest = value.strip().lower()
    if len(digest) != 64 or any(char not in SHA256_HEX for char in digest) or value != digest:
        raise ValueError(f"{context} must be lowercase SHA-256")
    return digest


def require_no_conflict(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must explicitly declare has_conflict=false")
    if value.get("has_conflict") is not False or not nonempty(value.get("details")):
        raise ValueError(f"{context} must explicitly declare has_conflict=false")


def record_self_digest(record: dict[str, Any], field: str) -> str:
    integrity = record.get("integrity")
    if not isinstance(integrity, dict) or field not in integrity:
        raise ValueError(f"integrity.{field} is required")
    candidate = copy.deepcopy(record)
    candidate["integrity"][field] = None
    return sha256_value(candidate)


def validate_candidate_integrity(packet: dict[str, Any]) -> None:
    construction = packet.get("construction")
    requirement = packet.get("pre_retrieval_requirement")
    machine_result = packet.get("machine_result")
    canonical_families = packet.get("canonical_families")
    source_records = packet.get("source_records")
    if not all(isinstance(value, dict) for value in (construction, requirement, machine_result)):
        raise ValueError(
            f"{packet.get('packet_id', '<unknown>')}: missing candidate integrity objects"
        )
    expected = (
        (
            "construction.source_metadata_snapshot_digest",
            construction.get("source_metadata_snapshot_digest"),
            sha256_value(source_records),
        ),
        (
            "machine_result.family_digest",
            machine_result.get("family_digest"),
            sha256_value(canonical_families),
        ),
        (
            "machine_result.requirement_digest",
            machine_result.get("requirement_digest"),
            sha256_value(requirement),
        ),
    )
    for field, declared, computed in expected:
        if declared != computed:
            raise ValueError(
                f"{packet.get('packet_id', '<unknown>')}: {field} does not bind candidate bytes"
            )


def load_candidates(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"T079 candidate manifest is required: {manifest_path}")
    candidate_manifest = load_json(manifest_path)
    if candidate_manifest.get("schema_version") != T079_CANDIDATE_MANIFEST_SCHEMA:
        raise ValueError("T079 candidate manifest has an unsupported schema")
    if candidate_manifest.get("status") != "READY_FOR_HUMAN_REVIEW":
        raise ValueError("T079 candidate manifest is not ready for human review")
    if candidate_manifest.get("release_evidence") is not False:
        raise ValueError("T079 candidate manifest must keep release_evidence=false")
    if candidate_manifest.get("packet_count") != 108:
        raise ValueError("T079 candidate manifest must contain exactly 108 packets")
    manifest_records = candidate_manifest.get("packet_records")
    if not isinstance(manifest_records, list) or len(manifest_records) != 108:
        raise ValueError("T079 candidate manifest packet_records must contain 108 packets")
    manifest_by_id: dict[str, dict[str, Any]] = {}
    for record in manifest_records:
        if not isinstance(record, dict) or not nonempty(record.get("packet_id")):
            raise ValueError("T079 candidate manifest contains an invalid packet record")
        packet_id = str(record["packet_id"])
        if packet_id in manifest_by_id:
            raise ValueError(f"duplicate T079 manifest packet_id: {packet_id}")
        require_sha256(record.get("packet_digest"), f"{packet_id}.packet_digest")
        if record.get("review_status") != "not_run":
            raise ValueError(f"{packet_id}: candidate manifest has unexpected review status")
        manifest_by_id[packet_id] = record

    declared_disciplines = candidate_manifest.get("packets_by_discipline")
    if not isinstance(declared_disciplines, dict) or set(declared_disciplines) != set(
        SUPPORTED_DISCIPLINES
    ):
        raise ValueError("T079 candidate manifest must declare every supported discipline")
    if any(declared_disciplines[name] != 12 for name in SUPPORTED_DISCIPLINES):
        raise ValueError("T079 candidate manifest must declare 12 packets per discipline")
    declared_categories = candidate_manifest.get("categories")
    expected_categories = {
        "balanced": 18,
        "concentrated": 18,
        **{
            category: 9
            for category in PACKET_CATEGORIES
            if category not in {"balanced", "concentrated"}
        },
    }
    if declared_categories != expected_categories:
        raise ValueError(
            "T079 candidate manifest categories do not match the frozen packet allocation"
        )

    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(root.rglob("*.json")):
        if path == manifest_path:
            continue
        try:
            packet = load_json(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"malformed T079 candidate packet {path}: {exc}") from exc
        packet_id = packet.get("packet_id")
        if not nonempty(packet_id):
            raise ValueError(f"candidate packet is missing packet_id: {path}")
        if packet.get("schema_version") != T079_CANDIDATE_SCHEMA:
            raise ValueError(f"{packet_id}: unsupported candidate packet schema")
        if packet_id in result:
            raise ValueError(f"duplicate T079 candidate packet_id: {packet_id}")
        if packet.get("status") != "READY_FOR_HUMAN_REVIEW":
            raise ValueError(f"{packet_id}: candidate status is not READY_FOR_HUMAN_REVIEW")
        if "review" not in packet or packet.get("review") is not None:
            raise ValueError(f"{packet_id}: automated candidate unexpectedly contains a review")
        if any(key in packet for key in ("label", "truth", "benchmark_truth")):
            raise ValueError(f"{packet_id}: candidate unexpectedly contains human truth")
        expected = candidate_digest(packet)
        if packet.get("packet_digest") != expected:
            raise ValueError(f"{packet_id}: candidate packet_digest mismatch")
        validate_candidate_integrity(packet)
        manifest_record = manifest_by_id.get(str(packet_id))
        if manifest_record is None:
            raise ValueError(f"{packet_id}: candidate is absent from manifest")
        for field in ("discipline", "partition", "stress_category", "packet_digest"):
            if manifest_record.get(field) != packet.get(field):
                raise ValueError(f"{packet_id}: candidate manifest binding mismatch for {field}")
        result[str(packet_id)] = (path, packet)
    if set(result) != set(manifest_by_id) or len(result) != 108:
        raise ValueError("T079 candidate packet files do not exactly match the 108-record manifest")
    return result


def load_reviews(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(root.rglob("*.json")):
        try:
            review = load_json(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"malformed T079 review record {path}: {exc}") from exc
        if review.get("schema_version") != T079_REVIEW_SCHEMA:
            raise ValueError(f"{path}: unsupported T079 review schema")
        binding = review.get("packet_binding")
        if not isinstance(binding, dict) or not nonempty(binding.get("packet_id")):
            raise ValueError(f"{path}: review record is missing packet_binding.packet_id")
        packet_id = str(binding["packet_id"])
        if packet_id in result:
            raise ValueError(f"duplicate human review for packet {packet_id}")
        result[packet_id] = (path, review)
    if not result:
        raise ValueError("no T079 independent review records found")
    return result


def validate_lock(
    packet: dict[str, Any], review: dict[str, Any], review_path: Path
) -> dict[str, Any]:
    packet_id = str(packet["packet_id"])
    if packet.get("partition") != "locked_candidate":
        raise ValueError(f"{packet_id}: tuning candidate cannot enter T080 locked inputs")
    if packet.get("discipline") not in SUPPORTED_DISCIPLINES:
        raise ValueError(f"{packet_id}: unsupported discipline")
    if packet.get("stress_category") not in PACKET_CATEGORIES:
        raise ValueError(f"{packet_id}: unsupported stress category")
    if review.get("schema_version") != T079_REVIEW_SCHEMA:
        raise ValueError(f"{packet_id}: unsupported review schema")
    if review.get("status") not in HUMAN_REVIEW_STATUSES:
        raise ValueError(f"{packet_id}: review is not marked as completed human review")
    if review.get("release_evidence") is not False:
        raise ValueError(f"{packet_id}: review must keep release_evidence=false")
    binding = review.get("packet_binding")
    reviewer = review.get("reviewer")
    judgment = review.get("review")
    if (
        not isinstance(binding, dict)
        or not isinstance(reviewer, dict)
        or not isinstance(judgment, dict)
    ):
        raise ValueError(f"{packet_id}: malformed review record")
    if (
        binding.get("packet_id") != packet_id
        or binding.get("packet_sha256") != packet["packet_digest"]
    ):
        raise ValueError(f"{packet_id}: review does not bind the exact candidate digest")
    for field, expected in (
        ("discipline", packet.get("discipline")),
        ("partition", packet.get("partition")),
        ("construction_stress_category", packet.get("stress_category")),
    ):
        if binding.get(field) != expected:
            raise ValueError(f"{packet_id}: review binding mismatch for {field}")
    construction = packet.get("construction")
    machine_result = packet.get("machine_result")
    expected_digest_bindings = {
        "source_metadata_snapshot_sha256": (
            construction.get("source_metadata_snapshot_digest")
            if isinstance(construction, dict)
            else None
        ),
        "canonical_family_digest": (
            machine_result.get("family_digest") if isinstance(machine_result, dict) else None
        ),
        "requirement_digest": (
            machine_result.get("requirement_digest") if isinstance(machine_result, dict) else None
        ),
        "machine_result_digest": sha256_value(machine_result),
    }
    for field, expected in expected_digest_bindings.items():
        require_sha256(expected, f"{packet_id}.{field}")
        if binding.get(field) != expected:
            raise ValueError(f"{packet_id}: review binding mismatch for {field}")
    for field in (
        "reviewer_id",
        "role",
        "discipline_competence_basis",
        "independence_attestation",
        "reviewed_at",
    ):
        if not nonempty(reviewer.get(field)):
            raise ValueError(f"{packet_id}: missing genuine reviewer field {field}")
    require_no_conflict(
        reviewer.get("conflict_declaration"), f"{packet_id}: reviewer conflict_declaration"
    )
    allowed_dispositions = judgment.get("allowed_dispositions")
    if not isinstance(allowed_dispositions, list) or "lock" not in allowed_dispositions:
        raise ValueError(f"{packet_id}: review does not declare lock as an allowed disposition")
    if judgment.get("decision_origin") != "human":
        raise ValueError(f"{packet_id}: benchmark truth lacks an explicit human decision origin")
    if judgment.get("disposition") != "lock":
        raise ValueError(f"{packet_id}: review disposition is not lock")
    if not nonempty(judgment.get("rationale")):
        raise ValueError(f"{packet_id}: locked review lacks rationale")
    truth = judgment.get("benchmark_truth")
    if not isinstance(truth, dict):
        raise ValueError(f"{packet_id}: locked review lacks benchmark_truth")
    expected_fields = (
        "material_gap",
        "adequate",
        "justified_narrow",
        "seeded_fake_or_missing_strata",
    )
    for field in expected_fields:
        if type(truth.get(field)) is not bool:
            raise ValueError(
                f"{packet_id}: benchmark_truth.{field} must be an explicit human boolean"
            )
    if truth["material_gap"] and (truth["adequate"] or truth["justified_narrow"]):
        raise ValueError(f"{packet_id}: conflicting human benchmark truth")
    if not (truth["material_gap"] or truth["adequate"] or truth["justified_narrow"]):
        raise ValueError(f"{packet_id}: human benchmark truth has no applicable outcome")
    review_digest = sha256_file(review_path)
    integrity = review.get("integrity")
    if not isinstance(integrity, dict):
        raise ValueError(f"{packet_id}: review lacks immutable integrity binding")
    declared_self_digest = require_sha256(
        integrity.get("review_record_sha256"),
        f"{packet_id}: review_record_sha256",
    )
    if declared_self_digest != record_self_digest(review, "review_record_sha256"):
        raise ValueError(f"{packet_id}: declared review self-digest does not match review content")
    if not nonempty(integrity.get("immutable_external_record_uri")):
        raise ValueError(f"{packet_id}: review lacks immutable external record URI")
    return {
        "packet_id": packet_id,
        "discipline": packet["discipline"],
        "category": packet["stress_category"],
        "review_status": "locked_human_reviewed",
        "review_record_sha256": review_digest,
        "review_record_self_sha256": declared_self_digest,
        "reviewer_id": reviewer["reviewer_id"],
        "expected": {field: truth[field] for field in expected_fields},
        "requirement": packet["pre_retrieval_requirement"],
        "sources": packet["source_records"],
        "claims": packet["claim_exposure_records"],
        "exception": {},
        "candidate_packet_sha256": packet["packet_digest"],
    }


def build(candidate_dir: Path, review_dir: Path) -> dict[str, Any]:
    candidates = load_candidates(candidate_dir)
    reviews = load_reviews(review_dir)
    unknown_reviews = sorted(set(reviews) - set(candidates))
    if unknown_reviews:
        raise ValueError(
            "T080 review records are not bound to candidate packets: " + ", ".join(unknown_reviews)
        )
    non_locked_reviews = sorted(
        packet_id
        for packet_id in reviews
        if candidates[packet_id][1].get("partition") != "locked_candidate"
    )
    if non_locked_reviews:
        raise ValueError(
            "T080 reviews may bind only locked candidate packets: " + ", ".join(non_locked_reviews)
        )
    locked: list[dict[str, Any]] = []
    errors: list[str] = []
    for packet_id, (path, packet) in sorted(candidates.items()):
        if packet.get("partition") != "locked_candidate":
            continue
        review_item = reviews.get(packet_id)
        if review_item is None:
            errors.append(f"{packet_id}: missing independent review")
            continue
        review_path, review = review_item
        try:
            locked.append(validate_lock(packet, review, review_path))
        except ValueError as exc:
            errors.append(str(exc))
    counts = Counter(item["discipline"] for item in locked)
    for discipline in SUPPORTED_DISCIPLINES:
        if counts[discipline] < REQUIRED_PER_DISCIPLINE:
            errors.append(
                f"{discipline}: {counts[discipline]} valid locked packets; requires at least {REQUIRED_PER_DISCIPLINE}"
            )
    if errors:
        raise ValueError("T080 input not ready:\n- " + "\n- ".join(errors))
    manifest = {
        "schema_version": "2.0.0",
        "status": "frozen",
        "review_status": "locked_human_reviewed",
        "required_packets_per_discipline": REQUIRED_PER_DISCIPLINE,
        "supported_disciplines": list(SUPPORTED_DISCIPLINES),
        "packet_categories": list(PACKET_CATEGORIES),
        "release_evidence": False,
        "packets": sorted(locked, key=lambda item: item["packet_id"]),
        "provenance": {
            "candidate_root": str(candidate_dir),
            "review_root": str(review_dir),
            "importer": Path(__file__).name,
            "note": "Human benchmark truth was copied from bound review records, never inferred from construction category or machine_result.",
        },
    }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = build(args.candidate_dir.resolve(), args.review_dir.resolve())
        if args.output.exists():
            raise ValueError(f"refusing to overwrite immutable T080 input: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "NOT_RUN", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": "READY_FOR_T080_EXECUTION",
                "packet_count": len(manifest["packets"]),
                "output": str(args.output),
                "output_sha256": sha256_file(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
