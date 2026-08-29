"""Focused tests for the deterministic Spec Kit artifact consistency check."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.check_spec_kit_artifacts import validate_feature_directory

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIRECTORY = REPOSITORY_ROOT / "specs" / "001-swos-v1-1-programme-foundation"


class SpecKitArtifactTests(unittest.TestCase):
    def test_feature_artifacts_are_consistent(self) -> None:
        self.assertEqual(validate_feature_directory(FEATURE_DIRECTORY), [])

    def test_unresolved_template_placeholder_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            feature_directory = Path(temporary_directory) / "feature"
            shutil.copytree(FEATURE_DIRECTORY, feature_directory)
            spec = feature_directory / "spec.md"
            spec.write_text(
                spec.read_text(encoding="utf-8") + "\n[FEATURE NAME]\n", encoding="utf-8"
            )

            errors = validate_feature_directory(feature_directory)

        self.assertTrue(any("unresolved template placeholder" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
