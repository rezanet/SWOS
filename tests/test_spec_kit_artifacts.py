"""Focused tests for the deterministic Spec Kit artifact consistency check."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.check_spec_kit_artifacts import (
    validate_feature_directory,
    validate_spec_kit_features,
)

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

    def test_all_feature_directories_are_validated_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first_feature = root / "specs" / "001-foundation"
            second_feature = root / "specs" / "002-runtime-reconciliation"
            shutil.copytree(FEATURE_DIRECTORY, first_feature)
            shutil.copytree(FEATURE_DIRECTORY, second_feature)
            spec = second_feature / "spec.md"
            spec.write_text(
                spec.read_text(encoding="utf-8") + "\n[FEATURE NAME]\n",
                encoding="utf-8",
            )

            errors = validate_spec_kit_features(root)

        self.assertTrue(
            any(
                error.startswith("specs/002-runtime-reconciliation:")
                and "unresolved template placeholder" in error
                for error in errors
            )
        )

    def test_multiple_consistent_feature_directories_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(FEATURE_DIRECTORY, root / "specs" / "001-foundation")
            shutil.copytree(FEATURE_DIRECTORY, root / "specs" / "002-runtime-reconciliation")

            errors = validate_spec_kit_features(root)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
