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


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def candidate_digest(packet: dict[str, Any]) -> str:
    payload = {key: value for key, value in packet.items() if key not in {"packet_digest", "review"}}
    return sha256_json(payload)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_candidates(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(root.rglob("*.json")):
        try:
            packet = load_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        packet_id = packet.get("packet_id")
        if not nonempty(packet_id) or packet.get("schema_version") != "2.0.0-candidate":
            continue
        if packet_id in result:
            raise ValueError(f"duplicate T079 candidate packet_id: {packet_id}")
        if packet.get("status") != "READY_FOR_HUMAN_REVIEW":
            raise ValueError(f"{packet_id}: candidate status is not READY_FOR_HUMAN_REVIEW")
        if packet.get("review") is not None:
            raise ValueError(f"{packet_id}: automated candidate unexpectedly contains a review")
        expected = candidate_digest(packet)
        if packet.get("packet_digest") != expected:
            raise ValueError(f"{packet_id}: candidate packet_digest mismatch")
        result[str(packet_id)] = (path, packet)
    if not result:
        raise ValueError("no T079 candidate packets found")
    return result


def load_reviews(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(root.rglob("*.json")):
        review = load_json(path)
        binding = review.get("packet_binding")
        if not isinstance(binding, dict) or not nonempty(binding.get("packet_id")):
            continue
        packet_id = str(binding["packet_id"])
        if packet_id in result:
            raise ValueError(f"duplicate human review for packet {packet_id}")
        result[packet_id] = (path, review)
    if not result:
        raise ValueError("no T079 independent review records found")
    return result


def validate_lock(packet: dict[str, Any], review: dict[str, Any], review_path: Path) -> dict[str, Any]:
    packet_id = str(packet["packet_id"])
    if packet.get("partition") != "locked_candidate":
        raise ValueError(f"{packet_id}: tuning candidate cannot enter T080 locked inputs")
    if packet.get("discipline") not in SUPPORTED_DISCIPLINES:
        raise ValueError(f"{packet_id}: unsupported discipline")
    if packet.get("stress_category") not in PACKET_CATEGORIES:
        raise ValueError(f"{packet_id}: unsupported stress category")
    if review.get("schema_version") != "research-handoff.t079.independent-review.v1":
        raise ValueError(f"{packet_id}: unsupported review schema")
    binding = review.get("packet_binding")
    reviewer = review.get("reviewer")
    judgment = review.get("review")
    if not isinstance(binding, dict) or not isinstance(reviewer, dict) or not isinstance(judgment, dict):
        raise ValueError(f"{packet_id}: malformed review record")
    if binding.get("packet_id") != packet_id or binding.get("packet_sha256") != packet["packet_digest"]:
        raise ValueError(f"{packet_id}: review does not bind the exact candidate digest")
    for field, expected in (
        ("discipline", packet.get("discipline")),
        ("partition", packet.get("partition")),
        ("construction_stress_category", packet.get("stress_category")),
    ):
        if binding.get(field) != expected:
            raise ValueError(f"{packet_id}: review binding mismatch for {field}")
    for field in ("reviewer_id", "role", "discipline_competence_basis", "independence_attestation", "reviewed_at"):
        if not nonempty(reviewer.get(field)):
            raise ValueError(f"{packet_id}: missing genuine reviewer field {field}")
    if judgment.get("disposition") != "lock":
        raise ValueError(f"{packet_id}: review disposition is not lock")
    if not nonempty(judgment.get("rationale")):
        raise ValueError(f"{packet_id}: locked review lacks rationale")
    truth = judgment.get("benchmark_truth")
    if not isinstance(truth, dict):
        raise ValueError(f"{packet_id}: locked review lacks benchmark_truth")
    expected_fields = ("material_gap", "adequate", "justified_narrow", "seeded_fake_or_missing_strata")
    for field in expected_fields:
        if type(truth.get(field)) is not bool:
            raise ValueError(f"{packet_id}: benchmark_truth.{field} must be an explicit human boolean")
    if truth["material_gap"] and (truth["adequate"] or truth["justified_narrow"]):
        raise ValueError(f"{packet_id}: conflicting human benchmark truth")
    if not (truth["material_gap"] or truth["adequate"] or truth["justified_narrow"]):
        raise ValueError(f"{packet_id}: human benchmark truth has no applicable outcome")
    review_digest = sha256_file(review_path)
    integrity = review.get("integrity")
    if isinstance(integrity, dict) and integrity.get("review_record_sha256") not in (None, "", review_digest):
        raise ValueError(f"{packet_id}: declared review digest does not match review bytes")
    return {
        "packet_id": packet_id,
        "discipline": packet["discipline"],
        "category": packet["stress_category"],
        "review_status": "locked_human_reviewed",
        "review_record_sha256": review_digest,
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
        "packets": sorted(locked, key=lambda item: item["packet_id"]),
        "provenance": {
            "candidate_root": str(candidate_dir),
            "review_root": str(review_dir),
            "importer": Path(__file__).name,
            "note": "Human benchmark truth was copied from bound review records, never inferred from construction category or machine_result."
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
        args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "NOT_RUN", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "status": "READY_FOR_T080_EXECUTION",
        "packet_count": len(manifest["packets"]),
        "output": str(args.output),
        "output_sha256": sha256_file(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
