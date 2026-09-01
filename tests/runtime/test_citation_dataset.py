"""Corpus provenance, licence, agreement and leakage-boundary tests."""

from __future__ import annotations

import unittest

from swos_runtime.citation_dataset import (
    DatasetValidationError,
    check_group_leakage,
    grouped_split,
    krippendorff_alpha_nominal,
    validate_pair_record,
    validate_pair_source_binding,
    validate_source_licence_manifest,
)


class CitationDatasetTests(unittest.TestCase):
    def _pair(self, pair_id: str, group: str = "g-1") -> dict:
        return {
            "pair_id": pair_id,
            "claim": "claim",
            "exact_quote": "quote",
            "context": "context",
            "label": "directly_supports",
            "discipline": "engineering",
            "source_uri": "https://example.org/source",
            "source_digest": "a" * 64,
            "licence": "CC-BY-4.0",
            "group_id": group,
            "annotations": [
                {"annotator_id": "a", "label": "directly_supports"},
                {"annotator_id": "b", "label": "directly_supports"},
            ],
            "adjudication": {"status": "adjudicated", "label": "directly_supports"},
        }

    def test_pair_requires_licence_provenance_and_two_annotations(self) -> None:
        validate_pair_record(self._pair("p"))
        invalid = self._pair("bad")
        invalid["licence"] = "unknown"
        with self.assertRaises(DatasetValidationError):
            validate_pair_record(invalid)

        malformed = self._pair("malformed")
        malformed["adjudication"] = "adjudicated"
        with self.assertRaises(DatasetValidationError):
            validate_pair_record(malformed)

    def test_grouped_split_is_deterministic_and_has_no_group_leakage(self) -> None:
        rows = [self._pair(f"p-{i}", f"g-{i // 2}") for i in range(12)]
        first = grouped_split(rows, seed=7)
        second = grouped_split(rows, seed=7)
        self.assertEqual(first, second)
        self.assertFalse(check_group_leakage(first))
        self.assertGreaterEqual(krippendorff_alpha_nominal(rows), 0.99)

    def test_source_licence_manifest_binds_permitted_use_and_approval(self) -> None:
        manifest = {
            "schema_version": "2.0.0",
            "status": "frozen",
            "approval": {"status": "approved", "reviewer_id": "dataset-reviewer-1"},
            "sources": [
                {
                    "source_id": "source-1",
                    "uri": "https://example.org/source",
                    "digest": "b" * 64,
                    "licence": "CC-BY-4.0",
                    "attribution": "Example archive",
                    "allowed_use": ["train", "calibration", "locked_test", "ood", "temporal"],
                    "approval": {"status": "approved", "reviewer_id": "reviewer-1"},
                }
            ],
        }
        bound = validate_source_licence_manifest(manifest)
        self.assertEqual(bound["source-1"]["digest"], "b" * 64)

        pair = self._pair("bound")
        pair.update({"source_id": "source-1", "source_digest": "b" * 64})
        validate_pair_source_binding(pair, bound)
        pair["source_uri"] = "https://example.org/other"
        with self.assertRaises(DatasetValidationError):
            validate_pair_source_binding(pair, bound)

        missing_attribution = {
            **manifest,
            "sources": [{**manifest["sources"][0], "attribution": ""}],
        }
        with self.assertRaises(DatasetValidationError):
            validate_source_licence_manifest(missing_attribution)

        unknown_use = {
            **manifest,
            "sources": [{**manifest["sources"][0], "allowed_use": ["publish"]}],
        }
        with self.assertRaises(DatasetValidationError):
            validate_source_licence_manifest(unknown_use)

        missing_approval = {**manifest, "approval": {"status": "pending"}}
        with self.assertRaises(DatasetValidationError):
            validate_source_licence_manifest(missing_approval)

    def test_not_run_source_manifest_is_explicitly_empty(self) -> None:
        self.assertEqual(
            validate_source_licence_manifest(
                {"schema_version": "2.0.0", "status": "not_run", "sources": []}
            ),
            {},
        )


if __name__ == "__main__":
    unittest.main()
