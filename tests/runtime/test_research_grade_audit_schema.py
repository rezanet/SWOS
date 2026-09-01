"""Schema and example contract for the exact-head audit pack."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]


class ResearchGradeAuditSchemaTests(unittest.TestCase):
    def test_audit_pack_schema_and_example_are_versioned_and_valid(self) -> None:
        schema_path = ROOT / "schemas/research-grade/research-grade-audit-pack.schema.json"
        example_path = ROOT / "examples/research-grade/audit-pack.json"
        self.assertTrue(schema_path.is_file())
        self.assertTrue(example_path.is_file())
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        example = json.loads(example_path.read_text(encoding="utf-8"))
        self.assertIn("2.0.0", schema["$id"])
        self.assertEqual("2.0.0", schema["x-swos-version"])
        jsonschema.Draft202012Validator(schema).validate(example)

    def test_audit_pack_requires_exact_head_and_content_manifest(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/research-grade/research-grade-audit-pack.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            {
                "artifact",
                "schema_version",
                "code_sha",
                "artifact_count",
                "artifacts",
            },
            set(schema["required"]),
        )
        self.assertIn("sha256", schema["$defs"]["artifact"]["required"])


if __name__ == "__main__":
    unittest.main()
