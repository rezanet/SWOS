"""Regression tests for the T094 offline oracle package boundary."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_SCRIPT = (
    REPOSITORY_ROOT / "research" / "research-grade-external-evidence" / "T094-ORACLE-ADAPTER.py"
)


def _load_adapter():
    spec = importlib.util.spec_from_file_location("t094_oracle_adapter", ADAPTER_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {ADAPTER_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class T094OraclePackageTests(unittest.TestCase):
    def _write_package(self, path: Path, members: dict[str, bytes]) -> None:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in members.items():
                archive.writestr(name, data)

    def test_runtime_rejects_unsafe_zip_member_paths(self) -> None:
        module = _load_adapter()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            artifact = root / "oracle.pyz"
            self._write_package(
                artifact,
                {
                    "package-manifest.json": json.dumps(
                        {
                            "implementation": "ProvToolbox",
                            "version": "2.2.3",
                            "files": [],
                        }
                    ).encode("utf-8"),
                    "../escaped.txt": b"must not be extracted",
                },
            )

            with self.assertRaisesRegex(ValueError, "unsafe"):
                module.extract_runtime(artifact, root / "runtime")

    def test_runtime_rejects_archive_members_missing_from_manifest(self) -> None:
        module = _load_adapter()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            artifact = root / "oracle.pyz"
            self._write_package(
                artifact,
                {
                    "package-manifest.json": json.dumps(
                        {
                            "implementation": "ProvToolbox",
                            "version": "2.2.3",
                            "files": [],
                        }
                    ).encode("utf-8"),
                    "lib/unlisted.jar": b"unlisted",
                },
            )

            with self.assertRaisesRegex(ValueError, "manifest"):
                module.extract_runtime(artifact, root / "runtime")

    def test_runtime_rejects_dot_and_empty_member_paths(self) -> None:
        module = _load_adapter()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaisesRegex(ValueError, "unsafe"):
                module._safe_member_path(root, ".")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                module._safe_member_path(root, "./")

    def test_adapter_rejects_duplicate_format_requests(self) -> None:
        module = _load_adapter()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with patch(
                "sys.argv",
                [
                    "T094-ORACLE-ADAPTER.py",
                    "--artifact",
                    str(root / "missing.pyz"),
                    "--input",
                    str(root / "input.json"),
                    "--profile",
                    str(root / "profile.json"),
                    "--formats",
                    "prov-json,prov-json",
                    "--output",
                    str(root / "result.json"),
                ],
            ):
                with patch("builtins.print") as mocked_print:
                    self.assertEqual(2, module.main())
                    self.assertIn("duplicate", mocked_print.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
