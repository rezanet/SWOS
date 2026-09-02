"""Tests for the locked source-diversity benchmark gates."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from swos_runtime.source_diversity import DIMENSIONS
from tools import run_source_diversity_benchmark as benchmark


def _packet(packet_id: str) -> dict[str, str]:
    return {
        "packet_id": packet_id,
        "review_status": "locked_human_reviewed",
    }


def _result(
    *,
    packet_id: str,
    category: str = "balanced",
    material_gap: bool = False,
    adequate: bool = False,
    justified_narrow: bool = False,
    detected: bool = True,
) -> dict[str, object]:
    return {
        "packet_id": packet_id,
        "category": category,
        "expected": {
            "material_gap": material_gap,
            "adequate": adequate,
            "justified_narrow": justified_narrow,
        },
        "detected_material_gap": detected,
        "ordering_invariant": True,
        "provider_invariant": True,
    }


def _source(index: int) -> dict[str, object]:
    return {
        "source_id": f"source-{index}",
        "title": f"Work {index}",
        "url": f"https://example.org/work-{index}",
        "provider": f"provider-{index}",
        "doi": f"10.1000/work-{index}",
        "publisher": f"Publisher {index}",
        "venue": f"Venue {index}",
        "region": "AU",
        "language": "en",
        "period": "2020s",
        "methodology": "empirical",
        "source_type": "article",
        "access_mode": "open",
        "stance": "support",
        "metadata_status": {dimension: "observed" for dimension in DIMENSIONS},
    }


class SourceDiversityBenchmarkTests(unittest.TestCase):
    def test_production_result_invariance_ignores_run_timestamp(self) -> None:
        packet = {
            "packet_id": "balanced-1",
            "category": "balanced",
            "requirement": {
                "requirement_id": "requirement-1",
                "dimensions": ["publisher"],
                "min_family_count": 3,
                "max_hhi": 1.0,
                "max_share": 1.0,
                "min_composite": 0.5,
                "max_unknown_rate": 0.1,
            },
            "sources": [_source(index) for index in range(3)],
            "claims": [{"source_id": f"source-{index}"} for index in range(3)],
        }

        result = benchmark._result(packet)

        self.assertTrue(result["ordering_invariant"])
        self.assertTrue(result["provider_invariant"])

    def test_complete_benchmark_requires_and_reports_all_frozen_rates(self) -> None:
        packets = [_packet(f"seeded-{index}") for index in range(100)]
        packets += [_packet(f"adequate-{index}") for index in range(100)]
        results = [
            _result(
                packet_id=f"seeded-{index}",
                category="missing_strata",
                material_gap=True,
            )
            for index in range(100)
        ]
        results += [
            _result(
                packet_id=f"adequate-{index}",
                category="balanced",
                adequate=True,
            )
            for index in range(100)
        ]

        with patch.object(benchmark, "_load_packets", return_value=packets):
            with patch.object(benchmark, "_result", side_effect=results):
                report = benchmark.run_benchmark("unused.json")

        self.assertEqual("pass", report["gate_result"])
        self.assertEqual("frozen", report["status"])
        metrics = report["metrics"]
        self.assertEqual(100, metrics["fake_and_missing_strata_detection_denominator"])
        self.assertEqual(100, metrics["material_gap_recall_denominator"])
        self.assertGreaterEqual(metrics["material_gap_recall_lower_95"], 0.90)
        self.assertEqual(100, metrics["adequate_or_narrow_false_block_rate_denominator"])
        self.assertLessEqual(metrics["adequate_or_narrow_false_block_rate_upper_95"], 0.10)

    def test_thresholds_use_confidence_bounds_and_seeded_denominators(self) -> None:
        packets = [_packet(f"seeded-{index}") for index in range(10)]
        packets += [_packet(f"gap-{index}") for index in range(10)]
        results = [
            _result(
                packet_id=f"seeded-{index}",
                category="fake_diversity",
                material_gap=True,
            )
            for index in range(10)
        ]
        results += [
            _result(
                packet_id=f"gap-{index}",
                material_gap=True,
                detected=index < 9,
            )
            for index in range(10)
        ]

        with patch.object(benchmark, "_load_packets", return_value=packets):
            with patch.object(benchmark, "_result", side_effect=results):
                report = benchmark.run_benchmark("unused.json")

        self.assertEqual("fail", report["gate_result"])
        self.assertEqual("blocked", report["status"])
        metrics = report["metrics"]
        self.assertEqual(10, metrics["fake_and_missing_strata_detection_numerator"])
        self.assertEqual(10, metrics["fake_and_missing_strata_detection_denominator"])
        self.assertEqual(19, metrics["material_gap_recall_numerator"])
        self.assertEqual(20, metrics["material_gap_recall_denominator"])
        self.assertLess(metrics["material_gap_recall_lower_95"], 0.90)
        self.assertIn("material-gap recall", report["reason"])

    def test_false_block_gate_uses_upper_confidence_bound(self) -> None:
        packets = [_packet(f"adequate-{index}") for index in range(20)]
        results = [
            _result(
                packet_id=f"adequate-{index}",
                category="balanced",
                adequate=True,
                detected=index >= 4,
            )
            for index in range(20)
        ]

        with patch.object(benchmark, "_load_packets", return_value=packets):
            with patch.object(benchmark, "_result", side_effect=results):
                report = benchmark.run_benchmark("unused.json")

        self.assertEqual("fail", report["gate_result"])
        metrics = report["metrics"]
        self.assertEqual(4, metrics["adequate_or_narrow_false_block_rate_numerator"])
        self.assertEqual(20, metrics["adequate_or_narrow_false_block_rate_denominator"])
        self.assertGreater(metrics["adequate_or_narrow_false_block_rate_upper_95"], 0.10)
        self.assertIn("false-block", report["reason"])


if __name__ == "__main__":
    unittest.main()
