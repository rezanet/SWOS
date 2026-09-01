"""US1 fixture and benchmark artifact contracts."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ResearchMemoryFixtureTests(unittest.TestCase):
    def test_three_project_fixture_manifest_covers_all_required_scenarios(self) -> None:
        path = ROOT / "evals/fixtures/research-memory/manifest.json"
        self.assertTrue(path.is_file())
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("2.0.0", manifest["schema_version"])
        self.assertEqual(3, len(manifest["projects"]))
        required = {
            "snapshot",
            "delta",
            "duplicate",
            "fork",
            "collision",
            "contradiction",
            "expiry",
            "correction",
            "retirement",
            "replay",
        }
        self.assertTrue(required <= set(manifest["scenarios"]))

    def test_rpm_benchmark_manifest_and_limitations_are_recorded(self) -> None:
        path = ROOT / "benchmark/rpm/manifest.json"
        self.assertTrue(path.is_file())
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("2.0.0", manifest["schema_version"])
        self.assertGreaterEqual(manifest["item_count"], 100000)
        self.assertIn("limitations", manifest)
        self.assertTrue((ROOT / "docs/architecture/research-grade-memory.md").is_file())


if __name__ == "__main__":
    unittest.main()
