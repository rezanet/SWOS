"""Corpus provenance, licence, agreement and leakage-boundary tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools.build_citation_dataset as citation_builder
from swos_runtime.citation_dataset import (
    DatasetValidationError,
    check_group_leakage,
    grouped_split,
    krippendorff_alpha_nominal,
    validate_pair_record,
    validate_pair_source_binding,
    validate_source_licence_manifest,
)
from tools.build_citation_dataset import (
    _read_rows,
    _read_split_proportions,
    release_floor_gaps,
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
            "adjudication": {
                "status": "adjudicated",
                "adjudicator_id": "c",
                "label": "directly_supports",
                "rationale": "Both independent annotations agree.",
            },
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

    def test_pair_rejects_incomplete_or_conflicting_human_records(self) -> None:
        missing_annotation_label = self._pair("missing-annotation-label")
        missing_annotation_label["annotations"][0].pop("label")
        with self.assertRaises(DatasetValidationError):
            validate_pair_record(missing_annotation_label)

        missing_adjudication_record = self._pair("missing-adjudication-record")
        missing_adjudication_record["adjudication"].pop("rationale")
        with self.assertRaises(DatasetValidationError):
            validate_pair_record(missing_adjudication_record)

        conflicting_adjudication = self._pair("conflicting-adjudication")
        conflicting_adjudication["adjudication"]["label"] = "context_only"
        with self.assertRaises(DatasetValidationError):
            validate_pair_record(conflicting_adjudication)

        non_independent_adjudicator = self._pair("non-independent-adjudicator")
        non_independent_adjudicator["adjudication"]["adjudicator_id"] = "a"
        with self.assertRaises(DatasetValidationError):
            validate_pair_record(non_independent_adjudicator)

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

    def test_release_floor_gaps_cover_every_frozen_dimension(self) -> None:
        direct = self._pair("direct", "g-direct")
        context = self._pair("context", "g-context")
        context.update({"label": "context_only", "adversarial": True})
        rows = [direct, context]
        floors = {
            "total_pairs": 3,
            "per_label": 2,
            "per_discipline": 2,
            "locked_test": 2,
            "locked_per_label": 1,
            "locked_per_discipline": 1,
            "locked_adversarial_non_direct": 1,
        }

        gaps = release_floor_gaps(
            rows,
            {"train": [direct], "locked_test": [context]},
            supported_disciplines=("engineering", "art_history"),
            floors=floors,
        )
        gap_map = {item["metric"]: item for item in gaps}

        self.assertEqual(
            gap_map["total_pairs"], {"metric": "total_pairs", "required": 3, "observed": 2}
        )
        self.assertEqual(
            gap_map["label:directly_supports"]["observed"],
            1,
        )
        self.assertEqual(
            gap_map["label:partially_supports"]["observed"],
            0,
        )
        self.assertEqual(
            gap_map["discipline:art_history"]["observed"],
            0,
        )
        self.assertEqual(gap_map["locked_test"]["observed"], 1)
        self.assertEqual(gap_map["locked_label:directly_supports"]["observed"], 0)
        self.assertEqual(gap_map["locked_discipline:art_history"]["observed"], 0)
        self.assertNotIn("discipline:engineering", gap_map)
        self.assertNotIn("locked_adversarial_non_direct", gap_map)

    def test_build_dataset_cannot_report_frozen_with_missing_floor_dimensions(self) -> None:
        floors = {
            "total_pairs": 1,
            "per_label": 1,
            "per_discipline": 2,
            "locked_test": 0,
            "locked_per_label": 0,
            "locked_per_discipline": 0,
            "locked_adversarial_non_direct": 0,
        }
        row = self._pair("one")
        row.update({"source_id": "source-1", "source_digest": "b" * 64})
        source_licence = {
            "schema_version": "2.0.0",
            "status": "frozen",
            "approval": {"status": "approved", "reviewer_id": "dataset-reviewer"},
            "sources": [
                {
                    "source_id": "source-1",
                    "uri": row["source_uri"],
                    "digest": "b" * 64,
                    "licence": row["licence"],
                    "attribution": "Example archive",
                    "allowed_use": ["train"],
                    "approval": {"status": "approved", "reviewer_id": "reviewer"},
                }
            ],
        }
        manifest = {
            "schema_version": "2.0.0",
            "required_floors": floors,
            "supported_disciplines": ["engineering"],
            "split_proportions": {
                "train": 0.2,
                "calibration": 0.2,
                "locked_test": 0.2,
                "temporal": 0.2,
                "ood": 0.2,
            },
            "source_licence_manifest": "licence.json",
            "pairs": [row],
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "licence.json").write_text(json.dumps(source_licence), encoding="utf-8")
            with (
                patch.object(citation_builder, "RELEASE_FLOORS", floors),
                patch.object(citation_builder, "SUPPORTED_DISCIPLINES", ("engineering",)),
            ):
                report = citation_builder.build_dataset(manifest_path, root / "output", seed=0)

        self.assertEqual(report["status"], "blocked_below_release_floor")
        metrics = {item["metric"] for item in report["release_floor_gaps"]}
        self.assertIn("label:context_only", metrics)
        self.assertIn("discipline:engineering", metrics)
        self.assertNotIn("locked_test", metrics)

    def test_build_dataset_rejects_manifest_floor_drift_before_acquisition(self) -> None:
        manifest = {
            "schema_version": "2.0.0",
            "required_floors": {**citation_builder.RELEASE_FLOORS, "total_pairs": 1},
            "supported_disciplines": list(citation_builder.SUPPORTED_DISCIPLINES),
            "source_licence_manifest": "licence.json",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(citation_builder.DatasetBuildBlocked):
                citation_builder.build_dataset(manifest_path, root / "output")

    def test_build_dataset_freezes_all_declared_split_partitions(self) -> None:
        floors = {
            "total_pairs": 1,
            "per_label": 0,
            "per_discipline": 0,
            "locked_test": 0,
            "locked_per_label": 0,
            "locked_per_discipline": 0,
            "locked_adversarial_non_direct": 0,
        }
        proportions = {
            "train": 0.2,
            "calibration": 0.2,
            "locked_test": 0.2,
            "temporal": 0.2,
            "ood": 0.2,
        }
        source_licence = {
            "schema_version": "2.0.0",
            "status": "frozen",
            "approval": {"status": "approved", "reviewer_id": "dataset-reviewer"},
            "sources": [
                {
                    "source_id": "source-1",
                    "uri": "https://example.org/source",
                    "digest": "b" * 64,
                    "licence": "CC-BY-4.0",
                    "attribution": "Example archive",
                    "allowed_use": list(proportions),
                    "approval": {"status": "approved", "reviewer_id": "reviewer"},
                }
            ],
        }
        rows = []
        for index in range(5):
            row = self._pair(f"partition-{index}", f"g-{index}")
            row.update({"source_id": "source-1", "source_digest": "b" * 64})
            rows.append(row)
        manifest = {
            "schema_version": "2.0.0",
            "required_floors": floors,
            "supported_disciplines": ["engineering"],
            "split_proportions": proportions,
            "source_licence_manifest": "licence.json",
            "pairs": rows,
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "licence.json").write_text(json.dumps(source_licence), encoding="utf-8")
            with (
                patch.object(citation_builder, "RELEASE_FLOORS", floors),
                patch.object(citation_builder, "SUPPORTED_DISCIPLINES", ("engineering",)),
            ):
                report = citation_builder.build_dataset(manifest_path, root / "output", seed=0)
            licence_text = (root / "output" / "DATA-LICENCE.md").read_text(encoding="utf-8")

        self.assertEqual(set(report["splits"]), set(proportions))
        self.assertGreater(report["splits"]["temporal"]["count"], 0)
        self.assertGreater(report["splits"]["ood"]["count"], 0)
        self.assertIn("source-1", licence_text)
        self.assertIn("https://example.org/source", licence_text)
        self.assertIn("b" * 64, licence_text)
        self.assertIn("CC-BY-4.0", licence_text)
        self.assertIn("Example archive", licence_text)

    def test_citation_ingestion_rejects_non_objects_and_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")

            with self.assertRaises(citation_builder.DatasetBuildBlocked):
                _read_rows({"pairs": [None]}, manifest_path)

            pairs_path = root / "pairs.jsonl"
            pairs_path.write_text("[]\n", encoding="utf-8")
            with self.assertRaises(citation_builder.DatasetBuildBlocked):
                _read_rows({"pairs_path": "pairs.jsonl"}, manifest_path)

            outside = root.parent / "outside-pairs.json"
            outside.write_text("[]", encoding="utf-8")
            try:
                with self.assertRaises(citation_builder.DatasetBuildBlocked):
                    _read_rows({"pairs_path": "../outside-pairs.json"}, manifest_path)
            finally:
                outside.unlink()

    def test_split_proportions_reject_coercible_non_numeric_values(self) -> None:
        raw = {
            "train": "0.2",
            "calibration": 0.2,
            "locked_test": 0.2,
            "temporal": 0.2,
            "ood": 0.2,
        }
        with self.assertRaises(citation_builder.DatasetBuildBlocked):
            _read_split_proportions({"split_proportions": raw})


if __name__ == "__main__":
    unittest.main()
