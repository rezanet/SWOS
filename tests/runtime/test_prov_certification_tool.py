"""Tests for the PROV certification command boundary."""

from __future__ import annotations

import hashlib
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from swos_runtime.prov_model import ResourceLimits
from tests.runtime.test_epg_v2 import sample_epg
from tools.certify_prov_roundtrip import _limits, _load, certify, main


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

    def test_limits_reject_boolean_or_coerced_bounds(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "limits.json"
            path.write_text(
                json.dumps(
                    {
                        "limits": {
                            "max_bytes": True,
                            "max_statements": 100_000,
                            "max_literal_length": 1_000_000,
                            "max_depth": 64,
                            "timeout_seconds": 60.0,
                        }
                    }
                ),
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

    def test_json_input_size_is_checked_before_loading(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            path = directory / "payload.json"
            path.write_text(json.dumps(sample_epg()), encoding="utf-8")

            with self.assertRaises(ValueError):
                _load(path, ResourceLimits(max_bytes=1))

    def test_corpus_manifest_rejects_malformed_case(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            manifest = directory / "manifest.json"
            manifest.write_text(json.dumps({"cases": [{"id": "missing-epg"}]}), encoding="utf-8")

            with self.assertRaises(ValueError):
                certify(**self._certification_kwargs(directory, manifest))

            manifest.write_text(
                json.dumps(
                    {
                        "checksum_algorithm": "sha256",
                        "cases": [{"id": "sample", "epg": "case.json", "sha256": "0" * 64}],
                    }
                ),
                encoding="utf-8",
            )
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

    def test_corpus_manifest_requires_a_matching_case_checksum(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            case_path = directory / "case.json"
            case_path.write_text(json.dumps(sample_epg()), encoding="utf-8")
            manifest = directory / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "checksum_algorithm": "sha256",
                        "cases": [{"id": "sample", "epg": "case.json"}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                certify(**self._certification_kwargs(directory, manifest))

    def test_corpus_certificate_binds_manifest_and_case_digests(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            cases = []
            for category in (
                "valid",
                "invalid",
                "large",
                "adversarial",
                "hostile_blank_node",
            ):
                epg = sample_epg()
                epg["scope"]["fixture_category"] = category
                case_path = directory / f"{category}.json"
                case_path.write_text(json.dumps(epg), encoding="utf-8")
                cases.append(
                    {
                        "id": category,
                        "epg": case_path.name,
                        "sha256": hashlib.sha256(case_path.read_bytes()).hexdigest(),
                        "category": category,
                    }
                )
            manifest = directory / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "status": "frozen",
                        "checksum_algorithm": "sha256",
                        "required_categories": [
                            "valid",
                            "invalid",
                            "large",
                            "adversarial",
                            "hostile_blank_node",
                        ],
                        "cases": cases,
                    }
                ),
                encoding="utf-8",
            )

            report = certify(**self._certification_kwargs(directory, manifest))

            self.assertEqual("not_run", report["status"])
            self.assertNotEqual("0" * 64, report["source_sha"])
            self.assertNotEqual("0" * 64, report["input_digest"])

    def test_corpus_manifest_rejects_reused_case_path_or_digest(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            case_path = directory / "case.json"
            case_path.write_text(json.dumps(sample_epg()), encoding="utf-8")
            case_sha256 = hashlib.sha256(case_path.read_bytes()).hexdigest()
            categories = (
                "valid",
                "invalid",
                "large",
                "adversarial",
                "hostile_blank_node",
            )
            manifest = directory / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "status": "frozen",
                        "checksum_algorithm": "sha256",
                        "required_categories": list(categories),
                        "cases": [
                            {
                                "id": category,
                                "epg": "case.json",
                                "sha256": case_sha256,
                                "category": category,
                            }
                            for category in categories
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "reus|duplicate"):
                certify(**self._certification_kwargs(directory, manifest))

    def test_corpus_manifest_rejects_duplicate_payload_digests_on_distinct_paths(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            payload = json.dumps(sample_epg())
            for name in ("case-a.json", "case-b.json"):
                (directory / name).write_text(payload, encoding="utf-8")
            case_sha256 = hashlib.sha256((directory / "case-a.json").read_bytes()).hexdigest()
            manifest = directory / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "status": "frozen",
                        "checksum_algorithm": "sha256",
                        "required_categories": [
                            "valid",
                            "invalid",
                            "large",
                            "adversarial",
                            "hostile_blank_node",
                        ],
                        "cases": [
                            {
                                "id": "case-a",
                                "epg": "case-a.json",
                                "sha256": case_sha256,
                                "category": "valid",
                            },
                            {
                                "id": "case-b",
                                "epg": "case-b.json",
                                "sha256": case_sha256,
                                "category": "invalid",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate case payload digest"):
                certify(**self._certification_kwargs(directory, manifest))

    def test_nonempty_corpus_requires_frozen_manifest_metadata(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            case_path = directory / "case.json"
            case_path.write_text(json.dumps(sample_epg()), encoding="utf-8")
            case_sha256 = hashlib.sha256(case_path.read_bytes()).hexdigest()
            manifest = directory / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "status": "not_run",
                        "checksum_algorithm": "sha256",
                        "required_categories": [
                            "valid",
                            "invalid",
                            "large",
                            "adversarial",
                            "hostile_blank_node",
                        ],
                        "cases": [
                            {
                                "id": "sample",
                                "epg": "case.json",
                                "sha256": case_sha256,
                                "category": "valid",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "status"):
                certify(**self._certification_kwargs(directory, manifest))

    def test_nonempty_corpus_requires_frozen_case_categories(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            case_path = directory / "case.json"
            case_path.write_text(json.dumps(sample_epg()), encoding="utf-8")
            case_sha256 = hashlib.sha256(case_path.read_bytes()).hexdigest()
            manifest = directory / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "checksum_algorithm": "sha256",
                        "required_categories": [
                            "valid",
                            "invalid",
                            "large",
                            "adversarial",
                            "hostile_blank_node",
                        ],
                        "cases": [{"id": "sample", "epg": "case.json", "sha256": case_sha256}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                certify(**self._certification_kwargs(directory, manifest))

    def test_malformed_epg_is_reported_as_machine_readable_not_run(self) -> None:
        with TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            epg_path = directory / "epg.json"
            epg_path.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "profile": "swos.prov-dm-round-trip.v2",
                        "base_iri": "https://example.org/prov/",
                        "entities": [1],
                    }
                ),
                encoding="utf-8",
            )
            kwargs = self._certification_kwargs(directory, directory / "unused.json")
            output = io.StringIO()

            with redirect_stdout(output):
                result = main(
                    [
                        "--epg",
                        str(epg_path),
                        "--profile",
                        str(kwargs["profile_path"]),
                        "--formats",
                        "prov-json",
                        "--oracle-manifest",
                        str(kwargs["oracle_path"]),
                        "--limits",
                        str(kwargs["limits_path"]),
                        "--artifact-dir",
                        str(kwargs["artifact_dir"]),
                        "--certificate-out",
                        str(kwargs["certificate_out"]),
                    ]
                )

            self.assertEqual(2, result)
            self.assertEqual("not_run", json.loads(output.getvalue())["status"])


if __name__ == "__main__":
    unittest.main()
