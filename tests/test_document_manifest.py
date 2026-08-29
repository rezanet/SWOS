"""Focused and negative-path tests for the documentation authority manifest."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.validate_document_manifest import validate_manifest_data

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "docs" / "document-manifest.json"


class DocumentManifestValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_repository_manifest_has_no_validation_errors(self) -> None:
        errors = validate_manifest_data(self.manifest, REPOSITORY_ROOT)

        self.assertEqual(errors, [])

    def test_missing_corpus_entry_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["documents"].pop()

        errors = validate_manifest_data(manifest, REPOSITORY_ROOT)

        self.assertTrue(any("missing corpus entry" in error for error in errors))

    def test_duplicate_id_and_path_are_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        duplicate = copy.deepcopy(manifest["documents"][0])
        manifest["documents"].append(duplicate)

        errors = validate_manifest_data(manifest, REPOSITORY_ROOT)

        self.assertTrue(any("duplicate document id" in error for error in errors))
        self.assertTrue(any("duplicate document path" in error for error in errors))

    def test_nonexistent_path_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["documents"][0]["path"] = "docs/does-not-exist.md"

        errors = validate_manifest_data(manifest, REPOSITORY_ROOT)

        self.assertTrue(any("document path does not exist" in error for error in errors))

    def test_invalid_metadata_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["documents"][0]["authority"] = "unbounded"
        manifest["documents"][0]["status"] = "released"
        manifest["documents"][0]["version_scheme"] = "guess"

        errors = validate_manifest_data(manifest, REPOSITORY_ROOT)

        self.assertTrue(any("schema validation failed" in error for error in errors))

    def test_supersession_must_be_reciprocal_and_not_active(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        current = next(
            document for document in manifest["documents"] if document["id"] == "docs-roadmap"
        )
        historical = next(
            document
            for document in manifest["documents"]
            if document["id"] == "tasks-plan-g-prose95"
        )
        current["supersedes"] = [historical["id"]]
        historical["superseded_by"] = []
        historical["status"] = "active"

        errors = validate_manifest_data(manifest, REPOSITORY_ROOT)

        self.assertTrue(any("non-reciprocal supersession" in error for error in errors))
        self.assertTrue(any("active document is superseded" in error for error in errors))

    def test_unknown_supersession_target_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["documents"][0]["supersedes"] = ["missing-document"]

        errors = validate_manifest_data(manifest, REPOSITORY_ROOT)

        self.assertTrue(any("supersession target does not exist" in error for error in errors))

    def test_one_canonical_document_is_allowed_per_authority_domain(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        first = manifest["documents"][0]
        second = manifest["documents"][1]
        second["canonical_for"] = first["canonical_for"]

        errors = validate_manifest_data(manifest, REPOSITORY_ROOT)

        self.assertTrue(any("multiple canonical documents" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
