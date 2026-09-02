"""Tests for the PROV certification command boundary."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.runtime.test_epg_v2 import sample_epg
from tools.certify_prov_roundtrip import _limits, _load, certify


class ProvCertificationToolTests(unittest.TestCase):
    def _write_limits(self, directory: Path) -> Path:
        path = directory / "limits.json"
        path.write_text(
            json.dumps(
                {
                    "limits": {
                        "max_bytes": 5_000_000,
                        "max_statements": 100_000,
                        "max_literal_length": 1_000_000,
                        "max_depth": 64,
                        "timeout_seconds": 60.0,
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def _certification_kwargs(self, directory: Path, manifest: Path) -> dict[str, object]:
        profile = directory / "profile.json"
        profile.write_text(
            json.dumps({"profile_id": "swos.prov-dm-round-trip.v2"}), encoding="utf-8"
        )
        oracle = directory / "oracle.json"
        oracle.write_text(json.dumps({"status": "not_run"}), encoding="utf-8")
        return {
            "epg_path": None,
            "corpus_manifest": manifest,
            "profile_path": profile,
            "formats": ("prov-json",),
            "oracle_path": oracle,
            "limits_path": self._write_limits(directory),
            "artifact_dir": directory / "artifacts",
            "certificate_out": directory / "certificate.json",
        }

    def test_limits_require_all_explicit_resource_bounds(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "limits.json"
            path.write_text(
                json.dumps({"limits": {"max_bytes": 100}}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                _limits(path)

    def test_json_inputs_must_be_objects(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text("[]", encoding="utf-8")

            with self.assertRaises(ValueError):
                _load(path)

    def test_corpus_manifest_rejects_malformed_case(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            manifest = directory / "manifest.json"
            manifest.write_text(json.dumps({"cases": [{"id": "missing-epg"}]}), encoding="utf-8")

            with self.assertRaises(ValueError):
                certify(**self._certification_kwargs(directory, manifest))

    def test_corpus_manifest_rejects_path_escape(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name) / "corpus"
            directory.mkdir()
            outside = directory.parent / "outside.json"
            outside.write_text(json.dumps(sample_epg()), encoding="utf-8")
            manifest = directory / "manifest.json"
            manifest.write_text(
                json.dumps({"cases": [{"id": "escape", "epg": "../outside.json"}]}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                certify(**self._certification_kwargs(directory, manifest))


if __name__ == "__main__":
    unittest.main()
