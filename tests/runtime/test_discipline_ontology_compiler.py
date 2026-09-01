"""Deterministic offline ontology compiler contracts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.discipline_ontology import OntologyVersionError
from tools.compile_discipline_ontologies import compile_release

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "discipline-packs" / "manifest-v2.json"
SHAPES = ROOT / "discipline-packs" / "ontology" / "swos-discipline-shapes.ttl"


class DisciplineOntologyCompilerTests(unittest.TestCase):
    def test_repeated_compilation_is_byte_stable_and_records_digests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "one"
            second = Path(directory) / "two"
            report_one = compile_release(MANIFEST, SHAPES, first)
            report_two = compile_release(MANIFEST, SHAPES, second)
            self.assertEqual(report_one["compiled_digest"], report_two["compiled_digest"])
            self.assertEqual(
                (first / "engineering.json").read_bytes(),
                (second / "engineering.json").read_bytes(),
            )
            self.assertTrue(report_one["source_digest"])
            self.assertTrue(report_one["shape_digest"])
            self.assertTrue(report_one["tool_digest"])

    def test_unknown_version_and_deprecated_release_fail_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = json.loads(MANIFEST.read_text(encoding="utf-8"))
            source["version"] = "9.0.0"
            unknown = Path(directory) / "unknown.json"
            unknown.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaises(OntologyVersionError):
                compile_release(unknown, SHAPES, Path(directory) / "out")


if __name__ == "__main__":
    unittest.main()
