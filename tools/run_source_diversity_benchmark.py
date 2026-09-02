"""Run the source-diversity benchmark through the production runtime path.

The benchmark accepts reviewed JSON fixture packets.  It never infers a pass
from fixture names: expected outcomes are explicit fields in the reviewed
packet and every observed result is produced by ``measure_source_diversity``.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_calibration import metric_confidence_interval  # noqa: E402
from swos_runtime.source_diversity import (  # noqa: E402
    DIMENSIONS,
    DiversityRequirement,
    FamilyIdentityPolicy,
    canonicalize_source_families,
    measure_source_diversity,
)

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
PACKET_CATEGORIES = frozenset(
    {
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
        "single_family",
        "single_owner",
        "provider_only",
    }
)
REQUIRED_PACKETS_PER_DISCIPLINE = 10
LOCKED_REVIEW_STATUS = "locked_human_reviewed"
REQUIRED_EXPECTED_FIELDS = ("material_gap", "adequate", "justified_narrow")
REQUIRED_REQUIREMENT_FIELDS = (
    "requirement_id",
    "dimensions",
    "min_family_count",
    "max_hhi",
    "max_share",
    "min_composite",
    "max_unknown_rate",
    "declared_before_retrieval",
)
MANIFEST_PACKET_CATEGORIES = frozenset(
    {
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
    }
)

SEEDED_GAP_CATEGORIES = frozenset(
    {
        "single-family",
        "single_family",
        "single-owner",
        "single_owner",
        "provider-only",
        "provider_only",
        "provider-only-fake-diversity",
        "provider_only_fake_diversity",
        "duplicate",
        "fake-diversity",
        "fake_diversity",
        "missing-required-strata",
        "missing_required_strata",
        "missing-strata",
        "missing_strata",
    }
)
MATERIAL_GAP_RECALL_MIN = 0.90
FALSE_BLOCK_RATE_MAX = 0.10


class _LoadedPackets(list[dict[str, Any]]):
    """Packet list carrying manifest-level validation errors without API churn."""

    def __init__(
        self,
        packets: list[dict[str, Any]],
        *,
        manifest_errors: tuple[str, ...] = (),
    ) -> None:
        super().__init__(packets)
        self.manifest_errors = manifest_errors


def _manifest_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if payload.get("schema_version") != "2.0.0":
        errors.append("source-diversity packet manifest schema_version must be 2.0.0")
    if payload.get("status") != "frozen":
        errors.append("source-diversity packet manifest status must be frozen")
    if payload.get("review_status") != LOCKED_REVIEW_STATUS:
        errors.append(
            f"source-diversity packet manifest review_status must be {LOCKED_REVIEW_STATUS}"
        )
    required_count = payload.get("required_packets_per_discipline")
    if (
        not isinstance(required_count, int)
        or isinstance(required_count, bool)
        or required_count != REQUIRED_PACKETS_PER_DISCIPLINE
    ):
        errors.append(
            "source-diversity packet manifest required_packets_per_discipline must be "
            f"{REQUIRED_PACKETS_PER_DISCIPLINE}"
        )
    disciplines = payload.get("supported_disciplines")
    if not isinstance(disciplines, list) or disciplines != list(SUPPORTED_DISCIPLINES):
        errors.append("source-diversity packet manifest supported_disciplines are not frozen")
    categories = payload.get("packet_categories")
    if (
        not isinstance(categories, list)
        or any(not isinstance(item, str) for item in categories)
        or set(categories) != MANIFEST_PACKET_CATEGORIES
    ):
        errors.append("source-diversity packet manifest packet_categories are not frozen")
    return tuple(errors)


def _load_packets(path: Path) -> list[dict[str, Any]]:
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("packets"), list):
            packets = payload["packets"]
            if any(not isinstance(item, dict) for item in packets):
                raise ValueError("source-diversity packet manifest contains a non-object packet")
            return _LoadedPackets(list(packets), manifest_errors=_manifest_errors(payload))
        if isinstance(payload, dict):
            return [payload]
        raise ValueError("source-diversity packet manifest must be a JSON object")
    manifest_path = path / "manifest.json"
    if manifest_path.is_file():
        return _load_packets(manifest_path)
    packets: list[dict[str, Any]] = []
    for item in sorted(path.glob("*.json")):
        payload = json.loads(item.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"source-diversity packet is not a JSON object: {item}")
        packets.append(payload)
    return _LoadedPackets(packets)


def _packet_category(packet: dict[str, Any]) -> str:
    for key in ("category", "packet_category", "case_type"):
        value = packet.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ""


def _normalise_packet_category(packet: Mapping[str, Any]) -> str:
    category = _packet_category(dict(packet))
    return {
        "single-family": "single_family",
        "single-owner": "single_owner",
        "provider-only": "provider_only",
        "provider-only-fake-diversity": "fake_diversity",
        "provider_only_fake_diversity": "fake_diversity",
        "duplicate": "duplicate",
        "fake-diversity": "fake_diversity",
        "missing-required-strata": "missing_strata",
        "missing_required_strata": "missing_strata",
        "missing-strata": "missing_strata",
    }.get(category, category)


def _object_list(packet: Mapping[str, Any], field: str) -> list[dict[str, Any]]:
    if field not in packet:
        raise ValueError(f"source-diversity packet field {field!r} is required")
    value = packet[field]
    if not isinstance(value, list):
        raise ValueError(f"source-diversity packet field {field!r} must be an array")
    if any(not isinstance(item, dict) for item in value):
        raise ValueError(f"source-diversity packet field {field!r} contains a non-object entry")
    return list(value)


def _build_requirement(
    payload: Any,
    *,
    require_pre_retrieval_declaration: bool = False,
) -> DiversityRequirement:
    if not isinstance(payload, dict):
        raise ValueError("source-diversity packet requirement must be an object")
    if not isinstance(payload.get("requirement_id"), str) or not payload["requirement_id"].strip():
        raise ValueError("source-diversity packet requirement needs a non-empty requirement_id")
    dimensions = payload.get("dimensions")
    if (
        not isinstance(dimensions, list)
        or not dimensions
        or any(not isinstance(item, str) or item not in DIMENSIONS for item in dimensions)
        or len(set(dimensions)) != len(dimensions)
    ):
        raise ValueError("source-diversity packet requirement has invalid dimensions")
    required_strata = payload.get("required_strata", {})
    if not isinstance(required_strata, dict):
        raise ValueError("source-diversity packet requirement required_strata must be an object")
    for dimension, strata in required_strata.items():
        if dimension not in dimensions or not isinstance(strata, list):
            raise ValueError("source-diversity packet requirement has invalid required_strata")
        if any(not isinstance(item, str) or not item.strip() for item in strata):
            raise ValueError("source-diversity packet requirement strata must be non-empty strings")
        if len(set(strata)) != len(strata):
            raise ValueError("source-diversity packet requirement strata must be unique")
    if require_pre_retrieval_declaration:
        missing_fields = [field for field in REQUIRED_REQUIREMENT_FIELDS if field not in payload]
        if missing_fields:
            raise ValueError(
                "source-diversity packet requirement is missing " + ", ".join(missing_fields)
            )
        if payload.get("declared_before_retrieval") is not True:
            raise ValueError("source-diversity packet requirement is not declared before retrieval")
    min_family_count = payload.get("min_family_count")
    if isinstance(min_family_count, bool) or not isinstance(min_family_count, int):
        raise ValueError("source-diversity packet requirement min_family_count must be an integer")
    numeric_thresholds = ("max_hhi", "max_share", "min_composite", "max_unknown_rate")
    for field in numeric_thresholds:
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"source-diversity packet requirement {field} must be numeric")
        if not math.isfinite(float(value)):
            raise ValueError(f"source-diversity packet requirement {field} must be finite")
    if "counter_position_required" in payload and not isinstance(
        payload["counter_position_required"], bool
    ):
        raise ValueError(
            "source-diversity packet requirement counter_position_required must be boolean"
        )
    try:
        return DiversityRequirement(**payload)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid source-diversity packet requirement: {exc}") from exc


def _validate_benchmark_packets(packets: Any) -> list[str]:
    """Validate the held-out corpus contract before measuring any packet."""

    if not isinstance(packets, list):
        return ["source-diversity packet collection must be an array"]
    errors: list[str] = list(getattr(packets, "manifest_errors", ()))
    packet_ids: set[str] = set()
    discipline_counts = {discipline: 0 for discipline in SUPPORTED_DISCIPLINES}
    for index, packet in enumerate(packets):
        if not isinstance(packet, dict):
            errors.append(f"packet {index} is not a JSON object")
            continue
        packet_id = packet.get("packet_id")
        if not isinstance(packet_id, str) or not packet_id.strip():
            errors.append(f"packet {index} needs a non-empty packet_id")
        elif packet_id in packet_ids:
            errors.append(f"duplicate packet_id: {packet_id}")
        else:
            packet_ids.add(packet_id)
        if packet.get("review_status") != LOCKED_REVIEW_STATUS:
            errors.append(f"packet {packet_id or index} is not {LOCKED_REVIEW_STATUS}")
        discipline = packet.get("discipline")
        if not isinstance(discipline, str) or discipline not in SUPPORTED_DISCIPLINES:
            errors.append(f"packet {packet_id or index} has an unsupported discipline")
        else:
            discipline_counts[discipline] += 1
        category = _normalise_packet_category(packet)
        if category not in PACKET_CATEGORIES:
            errors.append(f"packet {packet_id or index} has an unsupported category")
        expected = packet.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"packet {packet_id or index} expected outcome must be an object")
        else:
            for field in REQUIRED_EXPECTED_FIELDS:
                if not isinstance(expected.get(field), bool):
                    errors.append(f"packet {packet_id or index} expected.{field} must be boolean")
            if "seeded_fake_or_missing_strata" in expected and not isinstance(
                expected["seeded_fake_or_missing_strata"], bool
            ):
                errors.append(
                    f"packet {packet_id or index} expected.seeded_fake_or_missing_strata must be boolean"
                )
            if expected.get("material_gap") is True and (
                expected.get("adequate") is True or expected.get("justified_narrow") is True
            ):
                errors.append(f"packet {packet_id or index} has conflicting expected outcomes")
        try:
            _build_requirement(
                packet.get("requirement"),
                require_pre_retrieval_declaration=True,
            )
            _object_list(packet, "sources")
            _object_list(packet, "claims")
            if packet.get("exception") is not None and not isinstance(packet["exception"], dict):
                raise ValueError("source-diversity packet exception must be an object")
        except ValueError as exc:
            errors.append(f"packet {packet_id or index}: {exc}")
    if not packets:
        errors.append("no source-diversity packets are available")
    for discipline, count in discipline_counts.items():
        if count < REQUIRED_PACKETS_PER_DISCIPLINE:
            errors.append(
                f"discipline {discipline} has {count} locked packets; "
                f"requires at least {REQUIRED_PACKETS_PER_DISCIPLINE}"
            )
    return errors


def _stable_report(report: Any) -> dict[str, Any]:
    """Return report semantics without the per-invocation creation timestamp."""

    payload = report.to_dict()
    payload.pop("created_at", None)
    return payload


def _result(packet: dict[str, Any]) -> dict[str, Any]:
    requirement = _build_requirement(packet.get("requirement"))
    sources = _object_list(packet, "sources")
    claims = _object_list(packet, "claims")
    families = canonicalize_source_families(sources, FamilyIdentityPolicy())
    report = measure_source_diversity(
        families=families,
        admitted_claims=claims,
        requirements=requirement,
        exception=packet.get("exception"),
    )
    reordered = list(reversed(sources))
    renamed = [{**item, "provider": f"renamed-{index}"} for index, item in enumerate(sources)]
    ordering_invariant = _stable_report(report) == _stable_report(
        measure_source_diversity(
            families=canonicalize_source_families(reordered, FamilyIdentityPolicy()),
            admitted_claims=claims,
            requirements=requirement,
            exception=packet.get("exception"),
        )
    )
    provider_invariant = _stable_report(report) == _stable_report(
        measure_source_diversity(
            families=canonicalize_source_families(renamed, FamilyIdentityPolicy()),
            admitted_claims=claims,
            requirements=requirement,
            exception=packet.get("exception"),
        )
    )
    expected = packet.get("expected", {})
    if not isinstance(expected, dict):
        raise ValueError("source-diversity packet expected outcome must be an object")
    detected = report.raw_status == "fail" or report.status == "review_required"
    return {
        "packet_id": packet.get("packet_id"),
        "discipline": packet.get("discipline"),
        "category": _normalise_packet_category(packet),
        "requirement_id": requirement.requirement_id,
        "requirement_digest": report.requirement_digest,
        "declared_before_retrieval": requirement.declared_before_retrieval,
        "observed": {
            "raw_status": report.raw_status,
            "status": report.status,
            "family_count": report.family_count,
            "research_grade_composite": report.research_grade_composite,
            "missing_strata": sorted(
                {item for dim in report.dimensions.values() for item in dim.missing_strata}
            ),
            "counter_position": dict(report.counter_position),
        },
        "expected": dict(expected) if isinstance(expected, dict) else {},
        "detected_material_gap": detected,
        "ordering_invariant": ordering_invariant,
        "provider_invariant": provider_invariant,
    }


def _rate(numerator: int, denominator: int) -> dict[str, float | int | None]:
    if denominator <= 0:
        return {
            "numerator": numerator,
            "denominator": denominator,
            "value": None,
            "lower_95": None,
            "upper_95": None,
        }
    lower, upper = metric_confidence_interval(numerator, denominator)
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator,
        "lower_95": lower,
        "upper_95": upper,
    }


def run_benchmark(fixtures: Path | str, output: Path | str | None = None) -> dict[str, Any]:
    packets = _load_packets(Path(fixtures))
    reviewed = [
        item
        for item in packets
        if isinstance(item, dict) and item.get("review_status") == LOCKED_REVIEW_STATUS
    ]
    input_validation_errors = _validate_benchmark_packets(packets)
    results = [] if input_validation_errors else [_result(item) for item in reviewed]
    inputs_complete = not input_validation_errors
    seeded_cases = [
        item
        for item in results
        if item.get("category") in SEEDED_GAP_CATEGORIES
        or item.get("expected", {}).get("seeded_fake_or_missing_strata") is True
    ]
    seeded_detected = sum(bool(item["detected_material_gap"]) for item in seeded_cases)
    expected_gaps = [item for item in results if bool(item.get("expected", {}).get("material_gap"))]
    true_positive = sum(item["detected_material_gap"] for item in expected_gaps)
    false_blocks = sum(
        not item["detected_material_gap"]
        for item in results
        if item.get("expected", {}).get("adequate")
        or item.get("expected", {}).get("justified_narrow")
    )
    adequate_total = sum(
        bool(
            item.get("expected", {}).get("adequate")
            or item.get("expected", {}).get("justified_narrow")
        )
        for item in results
    )
    seeded_rate = _rate(seeded_detected, len(seeded_cases))
    gap_rate = _rate(true_positive, len(expected_gaps))
    false_block_rate = _rate(false_blocks, adequate_total)
    ordering_invariant_numerator = sum(item["ordering_invariant"] for item in results)
    provider_invariant_numerator = sum(item["provider_invariant"] for item in results)
    all_invariant = bool(results) and all(
        item["ordering_invariant"] and item["provider_invariant"] for item in results
    )
    failures: list[str] = []
    if inputs_complete:
        if seeded_rate["denominator"] == 0:
            failures.append("seeded fake/missing-strata denominator is zero")
        elif seeded_rate["numerator"] != seeded_rate["denominator"]:
            failures.append("seeded fake/missing-strata detection is below 100%")
        if gap_rate["denominator"] == 0:
            failures.append("material-gap recall denominator is zero")
        elif float(gap_rate["lower_95"]) < MATERIAL_GAP_RECALL_MIN:
            failures.append(
                f"material-gap recall lower 95% bound is below {MATERIAL_GAP_RECALL_MIN:.2f}"
            )
        if false_block_rate["denominator"] == 0:
            failures.append("adequate/narrow false-block denominator is zero")
        elif float(false_block_rate["upper_95"]) > FALSE_BLOCK_RATE_MAX:
            failures.append(
                f"adequate/narrow false-block upper 95% bound is above {FALSE_BLOCK_RATE_MAX:.2f}"
            )
        if not all_invariant:
            failures.append("ordering/provider invariance failed")
    gate_pass = inputs_complete and not failures
    gate_result = "pass" if gate_pass else ("not_run" if not inputs_complete else "fail")
    report = {
        "schema_version": "2.0.0",
        "status": "frozen" if gate_pass else ("not_run" if not inputs_complete else "blocked"),
        "gate_result": gate_result,
        "reason": None
        if gate_pass
        else (
            "; ".join(input_validation_errors) if input_validation_errors else "; ".join(failures)
        ),
        "packet_count": len(packets),
        "locked_reviewed_packet_count": len(reviewed),
        "input_validation_errors": input_validation_errors,
        "pre_retrieval_requirements": [
            {
                "requirement_id": requirement_id,
                "requirement_digest": requirement_digest,
            }
            for requirement_id, requirement_digest in sorted(
                {
                    (
                        item["requirement_id"],
                        item["requirement_digest"],
                    )
                    for item in results
                    if isinstance(item.get("requirement_id"), str)
                    and isinstance(item.get("requirement_digest"), str)
                }
            )
        ],
        "metrics": {
            "fake_and_missing_strata_detection": seeded_rate["value"],
            "fake_and_missing_strata_detection_numerator": seeded_rate["numerator"],
            "fake_and_missing_strata_detection_denominator": seeded_rate["denominator"],
            "fake_and_missing_strata_detection_lower_95": seeded_rate["lower_95"],
            "fake_and_missing_strata_detection_upper_95": seeded_rate["upper_95"],
            "material_gap_recall": gap_rate["value"],
            "material_gap_recall_numerator": gap_rate["numerator"],
            "material_gap_recall_denominator": gap_rate["denominator"],
            "material_gap_recall_lower_95": gap_rate["lower_95"],
            "material_gap_recall_upper_95": gap_rate["upper_95"],
            "adequate_or_narrow_false_block_rate": false_block_rate["value"],
            "adequate_or_narrow_false_block_rate_numerator": false_block_rate["numerator"],
            "adequate_or_narrow_false_block_rate_denominator": false_block_rate["denominator"],
            "adequate_or_narrow_false_block_rate_lower_95": false_block_rate["lower_95"],
            "adequate_or_narrow_false_block_rate_upper_95": false_block_rate["upper_95"],
            "ordering_invariance_numerator": ordering_invariant_numerator,
            "ordering_invariance_denominator": len(results),
            "provider_invariance_numerator": provider_invariant_numerator,
            "provider_invariance_denominator": len(results),
            "ordering_provider_invariance": all_invariant,
        },
        "results": results,
        "production_path": "swos_runtime.source_diversity.measure_source_diversity",
    }
    if output is not None:
        target = Path(output)
        if target.exists():
            raise RuntimeError(f"immutable benchmark output already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", "--manifest", dest="fixtures", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    try:
        report = run_benchmark(args.fixtures, args.out)
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "not_run", "reason": str(exc)}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["gate_result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
