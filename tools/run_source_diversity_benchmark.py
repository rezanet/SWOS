"""Run the source-diversity benchmark through the production runtime path.

The benchmark accepts reviewed JSON fixture packets.  It never infers a pass
from fixture names: expected outcomes are explicit fields in the reviewed
packet and every observed result is produced by ``measure_source_diversity``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from swos_runtime.citation_calibration import metric_confidence_interval
from swos_runtime.source_diversity import (
    DiversityRequirement,
    FamilyIdentityPolicy,
    canonicalize_source_families,
    measure_source_diversity,
)


def _load_packets(path: Path) -> list[dict[str, Any]]:
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("packets"), list):
            return [item for item in payload["packets"] if isinstance(item, dict)]
        return [payload] if isinstance(payload, dict) else []
    packets: list[dict[str, Any]] = []
    for item in sorted(path.glob("*.json")):
        payload = json.loads(item.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            packets.append(payload)
    return packets


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
    ordering_invariant = report.to_dict() == measure_source_diversity(
        families=canonicalize_source_families(reordered, FamilyIdentityPolicy()),
        admitted_claims=[item for item in packet.get("claims", []) if isinstance(item, dict)],
        requirements=requirement,
        exception=packet.get("exception"),
    ).to_dict()
    provider_invariant = report.to_dict() == measure_source_diversity(
        families=canonicalize_source_families(renamed, FamilyIdentityPolicy()),
        admitted_claims=[item for item in packet.get("claims", []) if isinstance(item, dict)],
        requirements=requirement,
        exception=packet.get("exception"),
    ).to_dict()
    expected = packet.get("expected", {})
    detected = report.raw_status == "fail" or report.status == "review_required"
    return {
        "packet_id": packet.get("packet_id"),
        "discipline": packet.get("discipline"),
        "observed": {
            "raw_status": report.raw_status,
            "status": report.status,
            "family_count": report.family_count,
            "research_grade_composite": report.research_grade_composite,
            "missing_strata": sorted({item for dim in report.dimensions.values() for item in dim.missing_strata}),
            "counter_position": dict(report.counter_position),
        },
        "expected": dict(expected) if isinstance(expected, dict) else {},
        "detected_material_gap": detected,
        "ordering_invariant": ordering_invariant,
        "provider_invariant": provider_invariant,
    }


def run_benchmark(fixtures: Path | str, output: Path | str) -> dict[str, Any]:
    packets = _load_packets(Path(fixtures))
    reviewed = [item for item in packets if item.get("review_status") == "locked_human_reviewed"]
    results = [_result(item) for item in reviewed]
    expected_gaps = [item for item in results if bool(item.get("expected", {}).get("material_gap"))]
    true_positive = sum(item["detected_material_gap"] for item in expected_gaps)
    false_blocks = sum(
        not item["detected_material_gap"]
        for item in results
        if item.get("expected", {}).get("adequate") or item.get("expected", {}).get("justified_narrow")
    )
    gap_lower, gap_upper = metric_confidence_interval(true_positive, len(expected_gaps)) if expected_gaps else (0.0, 0.0)
    adequate_total = sum(
        bool(item.get("expected", {}).get("adequate") or item.get("expected", {}).get("justified_narrow"))
        for item in results
    )
    false_block_rate = false_blocks / adequate_total if adequate_total else None
    all_invariant = all(item["ordering_invariant"] and item["provider_invariant"] for item in results)
    report = {
        "schema_version": "2.0.0",
        "status": "frozen" if reviewed and len(reviewed) == len(packets) else "not_run",
        "gate_result": "pass" if reviewed and len(reviewed) == len(packets) and all_invariant else "not_run",
        "reason": None if reviewed and len(reviewed) == len(packets) else "locked human-reviewed packets are unavailable or incomplete",
        "packet_count": len(packets),
        "locked_reviewed_packet_count": len(reviewed),
        "metrics": {
            "fake_and_missing_strata_detection": None if not results else sum(item["detected_material_gap"] for item in results) / len(results),
            "material_gap_recall": true_positive / len(expected_gaps) if expected_gaps else None,
            "material_gap_recall_lower_95": gap_lower if expected_gaps else None,
            "material_gap_recall_upper_95": gap_upper if expected_gaps else None,
            "adequate_or_narrow_false_block_rate": false_block_rate,
            "ordering_provider_invariance": all_invariant,
        },
        "results": results,
        "production_path": "swos_runtime.source_diversity.measure_source_diversity",
    }
    target = Path(output)
    if target.exists():
        raise RuntimeError(f"immutable benchmark output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
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
