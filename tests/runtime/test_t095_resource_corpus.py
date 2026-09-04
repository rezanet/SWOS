"""Regression tests for deterministic T095 corpus and resource-bound preparation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SCRIPT = (
    REPOSITORY_ROOT
    / "research"
    / "research-grade-external-evidence"
    / "T095-GENERATE-RESOURCE-CORPORA.py"
)
MEASURE_SCRIPT = (
    REPOSITORY_ROOT
    / "research"
    / "research-grade-external-evidence"
    / "T095-MEASURE-RESOURCE-CORPORA.py"
)


def _file_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class T095ResourceCorpusTests(unittest.TestCase):
    def test_text_digests_are_stable_across_checkout_line_endings(self) -> None:
        module = _load(GENERATOR_SCRIPT, "t095_generator_line_endings")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = (
                REPOSITORY_ROOT / "benchmark" / "provenance" / "resource-limits.json"
            ).read_bytes()
            lf_path = root / "limits-lf.json"
            crlf_path = root / "limits-crlf.json"
            lf_bytes = source.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            lf_path.write_bytes(lf_bytes)
            crlf_path.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))

            self.assertEqual(module.sha256_file(lf_path), module.sha256_file(crlf_path))

    def test_committed_corpus_manifest_binds_all_generated_files(self) -> None:
        manifest_path = REPOSITORY_ROOT / "benchmark" / "provenance" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual("generated_not_measured", manifest["status"])
        self.assertFalse(manifest.get("release_evidence", False))
        generator_path = (
            REPOSITORY_ROOT
            / "research"
            / "research-grade-external-evidence"
            / "T095-GENERATE-RESOURCE-CORPORA.py"
        )
        self.assertEqual(manifest["generator"]["source_sha256"], _file_sha256(generator_path))
        self.assertEqual(
            manifest["resource_limits"]["sha256"],
            _file_sha256(REPOSITORY_ROOT / "benchmark" / "provenance" / "resource-limits.json"),
        )
        self.assertEqual(6, len(manifest["corpora"]))
        self.assertEqual(
            {1000, 10000, 100000},
            {
                corpus["statement_count"]
                for corpus in manifest["corpora"]
                if corpus["format"] == "provn"
            },
        )
        for corpus in manifest["corpora"]:
            path = manifest_path.parent / corpus["path"]
            self.assertTrue(path.is_file(), corpus["path"])
            self.assertEqual(corpus["sha256"], _file_sha256(path))
            self.assertEqual(manifest["profile_id"], corpus["profile_id"])

    def test_generator_binds_source_identity_and_input_parameters(self) -> None:
        module = _load(GENERATOR_SCRIPT, "t095_generator")
        with tempfile.TemporaryDirectory() as directory:
            manifest = module.generate(Path(directory))

            self.assertRegex(manifest["generator"]["source_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual("1.0.0", manifest["generator"]["version"])
            self.assertEqual("swos.prov-dm-round-trip.v2", manifest["profile_id"])
            self.assertEqual(6, len(manifest["corpora"]))
            for corpus in manifest["corpora"]:
                self.assertRegex(corpus["sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(0, corpus["generator"]["seed"])
                self.assertIn("input_parameters", corpus["generator"])
                self.assertIn("expected_status", corpus)

    def test_measurement_policy_requires_cpu_memory_and_wall_limits(self) -> None:
        limits = json.loads(
            (REPOSITORY_ROOT / "benchmark" / "provenance" / "resource-limits.json").read_text(
                encoding="utf-8"
            )
        )
        values = limits["limits"]
        self.assertIn("cpu_seconds", values)
        self.assertIn("max_rss_kb", values)
        self.assertIn("timeout_seconds", values)
        self.assertIsInstance(values["cpu_seconds"], (int, float))
        self.assertIsInstance(values["max_rss_kb"], int)
        self.assertGreater(values["cpu_seconds"], 0)
        self.assertGreater(values["max_rss_kb"], 0)

    def test_measurement_module_exposes_fail_closed_resource_evaluator(self) -> None:
        module = _load(MEASURE_SCRIPT, "t095_measure")
        self.assertTrue(hasattr(module, "resource_disposition"))
        self.assertEqual(
            "MEASURED",
            module.resource_disposition(
                {"total_cpu_seconds": 1.0, "max_rss_kb": 10},
                cpu_limit=2.0,
                memory_limit_kb=20,
            ),
        )
        self.assertEqual(
            "FAIL_CLOSED_CPU_LIMIT",
            module.resource_disposition(
                {"total_cpu_seconds": 3.0, "max_rss_kb": 10},
                cpu_limit=2.0,
                memory_limit_kb=20,
            ),
        )
        self.assertEqual(
            "FAIL_CLOSED_MEMORY_LIMIT",
            module.resource_disposition(
                {"total_cpu_seconds": 1.0, "max_rss_kb": 30},
                cpu_limit=2.0,
                memory_limit_kb=20,
            ),
        )
        with self.assertRaises(ValueError):
            module.resource_disposition(
                {"total_cpu_seconds": "1.0", "max_rss_kb": 10},
                cpu_limit=2.0,
                memory_limit_kb=20,
            )


if __name__ == "__main__":
    unittest.main()
