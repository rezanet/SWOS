"""Run the source-diversity benchmark through the production runtime path.

The benchmark accepts reviewed JSON fixture packets.  It never infers a pass
from fixture names: expected outcomes are explicit fields in the reviewed
packet and every observed result is produced by ``measure_source_diversity``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_calibration import metric_confidence_interval  # noqa: E402
from swos_runtime.source_diversity import (  # noqa: E402
    DiversityRequirement,
    FamilyIdentityPolicy,
    canonicalize_source_families,
    measure_source_diversity,
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


def _load_packets(path: Path) -> list[dict[str, Any]]:
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("packets"), list):
            packets = payload["packets"]
            if any(not isinstance(item, dict) for item in packets):
                raise ValueError("source-diversity packet manifest contains a non-object packet")
            return list(packets)
        if isinstance(payload, dict):
            return [payload]
        raise ValueError("source-diversity packet manifest must be a JSON object")
    packets: list[dict[str, Any]] = []
    for item in sorted(path.glob("*.json")):
        payload = json.loads(item.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"source-diversity packet is not a JSON object: {item}")
        packets.append(payload)
    return packets


def _packet_category(packet: dict[str, Any]) -> str:
    for key in ("category", "packet_category", "case_type"):
        value = packet.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ""


def _stable_report(report: Any) -> dict[str, Any]:
    """Return report semantics without the per-invocation creation timestamp."""

    payload = report.to_dict()
    payload.pop("created_at", None)
    return payload


def _result(packet: dict[str, Any]) -> dict[str, Any]:
    requirement = DiversityRequirement(**dict(packet["requirement"]))
    sources = list(packet.get("sources") or [])
    families = canonicalize_source_families(sources, FamilyIdentityPolicy())
    report = measure_source_diversity(
        families=families,
        admitted_claims=[item for item in packet.get("claims", []) if isinstance(item, dict)],
        requirements=requirement,
        exception=packet.get("exception"),
    )
    reordered = list(reversed(sources))
    renamed = [
        {**item, "provider": f"renamed-{index}"}
        for index, item in enumerate(sources)
        if isinstance(item, dict)
    ]
    ordering_invariant = _stable_report(report) == _stable_report(
        measure_source_diversity(
            families=canonicalize_source_families(reordered, FamilyIdentityPolicy()),
            admitted_claims=[item for item in packet.get("claims", []) if isinstance(item, dict)],
            requirements=requirement,
            exception=packet.get("exception"),
        )
    )
    provider_invariant = _stable_report(report) == _stable_report(
        measure_source_diversity(
            families=canonicalize_source_families(renamed, FamilyIdentityPolicy()),
            admitted_claims=[item for item in packet.get("claims", []) if isinstance(item, dict)],
            requirements=requirement,
            exception=packet.get("exception"),
        )
    )
    expected = packet.get("expected", {})
    detected = report.raw_status == "fail" or report.status == "review_required"
    return {
        "packet_id": packet.get("packet_id"),
        "discipline": packet.get("discipline"),
        "category": _packet_category(packet),
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
    reviewed = [item for item in packets if item.get("review_status") == "locked_human_reviewed"]
    results = [_result(item) for item in reviewed]
    inputs_complete = bool(packets) and len(reviewed) == len(packets)
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
            "locked human-reviewed packets are unavailable or incomplete"
            if not inputs_complete
            else "; ".join(failures)
        ),
        "packet_count": len(packets),
        "locked_reviewed_packet_count": len(reviewed),
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
