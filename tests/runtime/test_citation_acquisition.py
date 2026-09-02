"""Test-first contracts for the pre-annotation citation corpus workflow."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.citation_acquisition import (
    AcquisitionValidationError,
    acquire_candidates,
    semantic_grouped_split,
    validate_candidate_source_binding,
    validate_source_candidate_manifest,
    validate_unlabelled_candidate_pair,
)
from swos_runtime.citation_dataset import DatasetValidationError, validate_pair_record


class CitationAcquisitionTests(unittest.TestCase):
    def _source(self, *, state: str = "ADMISSIBLE_PENDING_REVIEW") -> dict:
        return {
            "source_id": "source-1",
            "doi": "10.1234/example.1",
            "stable_uri": "https://doi.org/10.1234/example.1",
            "exact_acquired_copy_uri": "file:///cache/source-1.json",
            "canonical_source_family": "doi:10.1234/example.1",
            "title": "A licensed example",
            "authors": ["Example Author"],
            "publisher": "Example Press",
            "publication_date": "2020-01-02",
            "disciplines": ["engineering"],
            "licence": {
                "spdx": "CC-BY-4.0",
                "uri": "https://creativecommons.org/licenses/by/4.0/",
                "version": "4.0",
                "article_rights_uri": "https://example.org/article-rights",
                "verification": "article_level_verified",
            },
            "attribution": "Example Author, A licensed example, Example Press",
            "acquired_at": "2026-09-03T00:00:00Z",
            "sha256": "a" * 64,
            "allowed_uses": ["candidate_generation", "human_annotation"],
            "third_party": {
                "status": "warning",
                "warning": "The source licence warns that third-party content may require permission.",
            },
            "state": state,
            "approval": {"status": "pending", "reviewer_id": None},
            "rejection_reason": None,
        }

    def _manifest(self) -> dict:
        return {
            "schema_version": "2.0.0",
            "manifest_type": "citation_support_source_candidates",
            "status": "READY_FOR_HUMAN_ANNOTATION",
            "generated_at": "2026-09-03T00:00:00Z",
            "sources": [self._source()],
            "semantic_split_policy": {
                "version": "1.0.0",
                "temporal": {
                    "criteria_id": "T070-TEMPORAL-YEAR-V1",
                    "definition": "publication_year <= 2015",
                    "cutoff_year": 2015,
                },
                "ood": {
                    "criteria_id": "T070-OOD-DOMAIN-V1",
                    "definition": "catalog_declared_held_out_domain is true",
                },
            },
        }

    def _pair(self, pair_id: str, group_id: str, partition: str = "in_domain") -> dict:
        return {
            "schema_version": "2.0.0",
            "packet_type": "citation_support_unlabelled_annotation",
            "packet_id": f"packet-{pair_id}",
            "pair_id": pair_id,
            "claim_family_id": f"family-{group_id}",
            "group_id": group_id,
            "discipline": "engineering",
            "claim_origin": "source-authored-sentence",
            "candidate_claim": "A source-authored atomic claim.",
            "exact_quote": "A bounded source passage.",
            "context": "The surrounding source context.",
            "source_id": "source-1",
            "source_uri": "https://doi.org/10.1234/example.1",
            "acquired_copy_uri": "file:///cache/source-1.json",
            "source_digest": "a" * 64,
            "licence": "CC-BY-4.0",
            "attribution": "Example Author, A licensed example, Example Press",
            "acquisition_stratum": "S1",
            "candidate_pattern_id": "A01",
            "pattern_basis": "stratum_defined",
            "semantic_split": {
                "partition": partition,
                "criteria_id": (
                    "T070-TEMPORAL-YEAR-V1"
                    if partition == "temporal"
                    else "T070-OOD-DOMAIN-V1"
                    if partition == "ood"
                    else "T070-IN-DOMAIN-V1"
                ),
                "publication_year": 2010 if partition == "temporal" else 2020,
                "cutoff_year": 2015,
                "catalog_declared_held_out_domain": partition == "ood",
                **({"domain_id": "held-out-domain"} if partition == "ood" else {}),
            },
            "annotations": [
                {"annotator_id": None, "label": None, "rationale": None},
                {"annotator_id": None, "label": None, "rationale": None},
            ],
            "adjudication": {
                "status": "pending",
                "adjudicator_id": None,
                "label": None,
                "rationale": None,
            },
        }

    def test_source_candidates_are_pending_until_independent_review(self) -> None:
        indexed = validate_source_candidate_manifest(self._manifest())
        self.assertEqual(indexed["source-1"]["state"], "ADMISSIBLE_PENDING_REVIEW")

        approved = self._manifest()
        approved["sources"][0]["state"] = "APPROVED"
        approved["sources"][0]["approval"] = {
            "status": "approved",
            "reviewer_id": "reviewer-1",
        }
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(approved)

        unknown = self._manifest()
        unknown["sources"][0]["licence"]["spdx"] = "UNKNOWN"
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(unknown)

    def test_unlabelled_packet_has_blank_human_fields_and_hides_intent(self) -> None:
        packet = self._pair("p-1", "g-1")
        validate_unlabelled_candidate_pair(packet)

        labelled = self._pair("p-2", "g-2")
        labelled["label"] = "directly_supports"
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(labelled)

        retrieval_intent = self._pair("p-3", "g-3")
        retrieval_intent["retrieval_intent"] = "direct"
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(retrieval_intent)

        filled = self._pair("p-4", "g-4")
        filled["annotations"][0]["label"] = "directly_supports"
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(filled)

    def test_candidate_source_binding_includes_exact_copy_and_pending_state(self) -> None:
        packet = self._pair("p-bound", "g-bound")
        indexed = validate_source_candidate_manifest(self._manifest())
        validate_candidate_source_binding(packet, indexed)

        wrong_copy = dict(packet)
        wrong_copy["acquired_copy_uri"] = "file:///cache/other.json"
        with self.assertRaises(AcquisitionValidationError):
            validate_candidate_source_binding(wrong_copy, indexed)

    def test_final_adjudicated_validator_still_rejects_candidate_packets(self) -> None:
        with self.assertRaises(DatasetValidationError):
            validate_pair_record(self._pair("still-unlabelled", "g-final-boundary"))

    def test_semantic_split_rejects_hash_only_assignment_and_keeps_groups_isolated(self) -> None:
        rows = [
            self._pair("p-in-1", "g-in", "in_domain"),
            self._pair("p-in-2", "g-in", "in_domain"),
            self._pair("p-temporal", "g-temporal", "temporal"),
            self._pair("p-ood", "g-ood", "ood"),
        ]
        policy = self._manifest()["semantic_split_policy"]
        splits = semantic_grouped_split(rows, policy=policy, seed=7)
        self.assertEqual({row["semantic_split"]["partition"] for row in splits["temporal"]}, {"temporal"})
        self.assertEqual({row["semantic_split"]["partition"] for row in splits["ood"]}, {"ood"})
        locations = {
            row["group_id"]: split for split, values in splits.items() for row in values
        }
        self.assertEqual(locations["g-in"], "train")
        self.assertNotIn("g-in", {row["group_id"] for row in splits["locked_test"]})

        hash_only = self._pair("p-hash", "g-hash", "in_domain")
        hash_only["semantic_split"] = {
            "partition": "temporal",
            "criteria_id": "HASH_BUCKET",
            "bucket": 3,
        }
        with self.assertRaises(AcquisitionValidationError):
            semantic_grouped_split([hash_only], policy=policy, seed=7)

    def test_acquisition_reuses_an_immutable_copy_and_writes_a_reproducible_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "source.json"
            content.write_text(
                json.dumps(
                    {
                        "title": "A source",
                        "publication_date": "2020-01-02",
                        "text": "This is a direct statement with enough words. Another contextual statement with enough words.",
                    }
                ),
                encoding="utf-8",
            )
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "catalog_type": "citation_source_candidate_catalog",
                        "sources": [
                            {
                                "source_id": "source-1",
                                "doi": "10.1234/example.1",
                                "stable_uri": "https://doi.org/10.1234/example.1",
                                "content_uri": content.as_uri(),
                                "title": "A source",
                                "authors": ["Example Author"],
                                "publisher": "Example Press",
                                "publication_date": "2020-01-02",
                                "disciplines": ["engineering"],
                                "licence": {
                                    "spdx": "CC-BY-4.0",
                                    "uri": "https://creativecommons.org/licenses/by/4.0/",
                                    "version": "4.0",
                                    "article_rights_uri": "https://example.org/rights",
                                    "verification": "article_level_verified",
                                },
                                "attribution": "Example Author, A source, Example Press",
                                "allowed_uses": ["candidate_generation", "human_annotation"],
                                "third_party": {
                                    "status": "warning",
                                    "warning": "Review third-party content.",
                                },
                                "semantic_split": {
                                    "partition": "in_domain",
                                    "criteria_id": "T070-IN-DOMAIN-V1",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "output"
            first = acquire_candidates(catalog, output, max_pairs=5)
            second = acquire_candidates(catalog, output, max_pairs=5)

            self.assertEqual(first["status"], "READY_FOR_HUMAN_ANNOTATION")
            self.assertEqual(second["reused_sources"], 1)
            self.assertEqual(first["candidate_pairs"], second["candidate_pairs"])
            self.assertEqual(first["output_digests"], second["output_digests"])
            self.assertTrue((output / "source-candidate-manifest.json").is_file())
            self.assertTrue((output / "unlabelled-candidate-pairs.jsonl").is_file())
            self.assertTrue((output / "acquisition-report.json").is_file())


if __name__ == "__main__":
    unittest.main()
