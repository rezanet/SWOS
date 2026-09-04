"""Regression tests for fail-closed T127/T128 evidence preflight."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = (
    ROOT / "research" / "research-grade-external-evidence" / "T127-T128-CLOSURE-PREFLIGHT.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("t127_t128_preflight", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class T127T128PreflightTests(unittest.TestCase):
    def test_external_record_requires_schema_and_exact_head(self) -> None:
        module = _load()
        head = "a" * 40
        valid = {
            "schema_version": "swos.external-evidence-record.v1",
            "record_type": "independent_review",
            "exact_head": head,
            "status": "APPROVED",
            "immutable_uri": "https://github.com/rezanet/SWOS/pull/999#discussion_r1",
        }
        self.assertEqual([], module.validate_external_record(valid, "review", head))
        self.assertTrue(module.validate_external_record({}, "review", head))
        self.assertTrue(
            module.validate_external_record({**valid, "exact_head": "b" * 40}, "review", head)
        )

    def test_external_record_file_is_invalid_when_json_or_binding_is_bad(self) -> None:
        module = _load()
        head = "a" * 40
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "swos.external-evidence-record.v1",
                        "record_type": "independent_review",
                        "exact_head": "b" * 40,
                        "status": "APPROVED",
                    }
                ),
                encoding="utf-8",
            )
            result = module.external_record(path, "review", head)
        self.assertEqual("INVALID", result["status"])
        self.assertTrue(result["validation_failures"])

    def test_coverage_record_rejects_placeholder_and_accepts_real_shape(self) -> None:
        module = _load()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            path.write_text(json.dumps({"status": "placeholder"}), encoding="utf-8")
            invalid = module.coverage_record(path)
            path.write_text(
                json.dumps(
                    {
                        "meta": {"version": "7.0.0"},
                        "files": {"swos_runtime/example.py": {"summary": {"covered_lines": 1}}},
                        "totals": {
                            "covered_lines": 1,
                            "num_statements": 1,
                            "percent_covered": 100.0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            valid = module.coverage_record(path)
        self.assertEqual("INVALID", invalid["status"])
        self.assertEqual("PRESENT", valid["status"])
        self.assertTrue(valid["validated"])


if __name__ == "__main__":
    unittest.main()
