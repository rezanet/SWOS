"""Red/green compatibility contracts for the Research Grade version shell."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from swos_runtime.models import VersionDispatchError, dispatch_version

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "tests" / "fixtures" / "research-grade" / "v1-compatibility-manifest.json"


class ResearchGradeCompatibilityTests(unittest.TestCase):
    def test_frozen_v1_files_and_schema_ids_are_unchanged(self) -> None:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        for group in baseline["groups"]:
            for entry in group["files"]:
                path = ROOT / entry["path"]
                self.assertTrue(path.is_file(), entry["path"])
                digest = hashlib.sha256(self._canonical_bytes(path)).hexdigest()
                self.assertEqual(entry["sha256"], digest, entry["path"])
        for relative, expected_id in baseline["baseline"]["v1_schema_ids"].items():
            document = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(expected_id, document["$id"], relative)

    def test_v1_document_cannot_be_routed_as_v2(self) -> None:
        with self.assertRaises(VersionDispatchError):
            dispatch_version({"$schema": "https://swos.dev/schemas/1.0.0/example.json"}, "2.0.0")

    def test_v2_document_cannot_silently_downgrade_to_v1(self) -> None:
        with self.assertRaises(VersionDispatchError):
            dispatch_version({"$schema": "https://swos.dev/schemas/2.0.0/example.json"}, "1.0.0")

    def test_v2_contracts_are_parallel_without_mutating_the_v1_contracts(self) -> None:
        v1_capability = ROOT / "contracts" / "capability-contract" / "capabilities-v1.json"
        v1_stage = ROOT / "contracts" / "stage-instruction" / "stage-instructions-v1.json"
        v2_capability = ROOT / "contracts" / "capability-contract" / "capabilities-v2.json"
        v2_stage = ROOT / "contracts" / "stage-instruction" / "stage-instructions-v2.json"
        self.assertTrue(v2_capability.is_file())
        self.assertTrue(v2_stage.is_file())
        self.assertEqual(
            self._digest(v1_capability),
            self._manifest_digest("contracts/capability-contract/capabilities-v1.json"),
        )
        self.assertEqual(
            self._digest(v1_stage),
            self._manifest_digest("contracts/stage-instruction/stage-instructions-v1.json"),
        )
        capability = json.loads(v2_capability.read_text(encoding="utf-8"))
        stage = json.loads(v2_stage.read_text(encoding="utf-8"))
        self.assertEqual("swos.capabilities.v2", capability["contract_set"])
        self.assertEqual("swos.stage-instructions.v2", stage["instruction_set"])
        self.assertEqual("research-grade", capability["profile"])
        self.assertEqual("research-grade", stage["profile"])
        self.assertTrue(all(item["contract"].endswith(".v2") for item in capability["capabilities"].values()))
        self.assertTrue(all(item["instruction_id"].endswith(".v2") for item in stage["instructions"].values()))
        self.assertIn("programme_memory", capability["capabilities"])
        self.assertIn("research_grade_verification", capability["capabilities"])
        self.assertIn("programme_memory", stage["instructions"])
        self.assertIn("research_grade_verification", stage["instructions"])

    @staticmethod
    def _digest(path: Path) -> str:
        return hashlib.sha256(ResearchGradeCompatibilityTests._canonical_bytes(path)).hexdigest()

    @staticmethod
    def _canonical_bytes(path: Path) -> bytes:
        """Hash repository-canonical text bytes across Windows and POSIX checkouts."""
        return path.read_bytes().replace(b"\r\n", b"\n")

    @staticmethod
    def _manifest_digest(relative: str) -> str:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        for group in baseline["groups"]:
            for entry in group["files"]:
                if entry["path"] == relative:
                    return entry["sha256"]
        raise AssertionError(f"missing baseline digest for {relative}")


if __name__ == "__main__":
    unittest.main()
