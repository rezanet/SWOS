"""Versioned schema and dispatcher contracts for Research Grade."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from swos_runtime.models import VersionDispatchError, dispatch_version

ROOT = Path(__file__).resolve().parents[2]
V2_SCHEMA_DIR = ROOT / "schemas" / "research-grade"


class ResearchGradeSchemaTests(unittest.TestCase):
    def test_v2_schema_ids_are_distinct_and_explicitly_versioned(self) -> None:
        schemas = sorted(V2_SCHEMA_DIR.glob("*.schema.json"))
        self.assertTrue(schemas)
        for path in schemas:
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("https://json-schema.org/draft/2020-12/schema", document["$schema"])
            self.assertIn("2.0.0", document["$id"], path.name)
            self.assertEqual("2.0.0", document["x-swos-version"], path.name)

    def test_dispatch_accepts_only_explicit_v1_or_v2_versions(self) -> None:
        self.assertEqual("v1", dispatch_version({"schema_version": "1.0.0"}))
        self.assertEqual("v2", dispatch_version({"schema_version": "2.0.0"}))
        for document in ({}, {"schema_version": "1.1"}, {"schema_version": "3.0.0"}):
            with self.subTest(document=document), self.assertRaises(VersionDispatchError):
                dispatch_version(document)

    def test_v2_capability_and_stage_contracts_are_self_describing(self) -> None:
        capability = json.loads(
            (ROOT / "contracts/capability-contract/capabilities-v2.json").read_text(
                encoding="utf-8"
            )
        )
        stage = json.loads(
            (ROOT / "contracts/stage-instruction/stage-instructions-v2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("2.0.0", capability["version"])
        self.assertEqual("2.0.0", stage["version"])
        self.assertEqual("2.0.0", capability["schema_version"])
        self.assertEqual("2.0.0", stage["schema_version"])
        self.assertTrue(capability["capabilities"]["programme_memory"]["assurance"])
        self.assertIn(
            "final_verification",
            capability["capabilities"]["research_grade_verification"]["assurance"],
        )
        self.assertIn("scope", stage["instructions"]["programme_memory"]["text"])


if __name__ == "__main__":
    unittest.main()
