"""Regression tests for deterministic external-evidence preparation tooling."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
T079_SCRIPT = (
    REPOSITORY_ROOT
    / "research"
    / "research-grade-external-evidence"
    / "T079-BUILD-REVIEWER-PACKETS.py"
)
T070_IMPORT_SCRIPT = (
    REPOSITORY_ROOT
    / "research"
    / "research-grade-external-evidence"
    / "T070-IMPORT-COMPLETED-REVIEWS.py"
)
T080_IMPORT_SCRIPT = (
    REPOSITORY_ROOT
    / "research"
    / "research-grade-external-evidence"
    / "T080-BUILD-LOCKED-BENCHMARK-INPUT.py"
)

T070_LABELS = [
    "directly_supports",
    "partially_supports",
    "context_only",
    "contradicts",
    "not_supported",
]


def _canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _digest(value) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_digest(record: dict, field: str = "record_sha256") -> str:
    value = copy.deepcopy(record)
    value["integrity"][field] = None
    return _digest(value)


def _load_t070_import_module():
    spec = importlib.util.spec_from_file_location(
        "t070_import_completed_reviews", T070_IMPORT_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {T070_IMPORT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_t080_import_module():
    spec = importlib.util.spec_from_file_location(
        "t080_build_locked_benchmark_input", T080_IMPORT_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {T080_IMPORT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _t080_packet_and_review() -> tuple[dict, dict]:
    packet = {
        "schema_version": "2.0.0-candidate",
        "status": "READY_FOR_HUMAN_REVIEW",
        "packet_id": "DIV-ART-HISTORY-03",
        "discipline": "art_history",
        "partition": "locked_candidate",
        "stress_category": "balanced",
        "construction": {"source_metadata_snapshot_digest": _digest([])},
        "pre_retrieval_requirement": {"requirement_id": "REQ-1"},
        "source_records": [],
        "canonical_families": [],
        "claim_exposure_records": [],
        "machine_result": {
            "family_digest": _digest([]),
            "requirement_digest": _digest({"requirement_id": "REQ-1"}),
        },
        "packet_digest": "d" * 64,
        "review": None,
    }
    packet["packet_digest"] = _digest(
        {key: value for key, value in packet.items() if key not in {"packet_digest", "review"}}
    )
    packet_digest = packet["packet_digest"]
    review = {
        "schema_version": "research-handoff.t079.independent-review.v1",
        "status": "human_reviewed",
        "packet_binding": {
            "packet_id": packet["packet_id"],
            "packet_sha256": packet_digest,
            "discipline": packet["discipline"],
            "partition": packet["partition"],
            "construction_stress_category": packet["stress_category"],
            "source_metadata_snapshot_sha256": _digest([]),
            "canonical_family_digest": _digest([]),
            "requirement_digest": _digest({"requirement_id": "REQ-1"}),
            "machine_result_digest": _digest(packet["machine_result"]),
        },
        "reviewer": {
            "reviewer_id": "reviewer-1",
            "role": "art-history-reviewer",
            "discipline_competence_basis": "documented discipline training",
            "independence_attestation": "I reviewed independently.",
            "conflict_declaration": {"has_conflict": False, "details": "none declared"},
            "reviewed_at": "2026-09-03T00:00:00Z",
        },
        "review": {
            "disposition": "lock",
            "rationale": "The packet is ready for locked evaluation.",
            "allowed_dispositions": ["lock", "reject", "repair_required"],
            "decision_origin": "human",
            "benchmark_truth": {
                "material_gap": False,
                "adequate": True,
                "justified_narrow": False,
                "seeded_fake_or_missing_strata": False,
            },
        },
        "integrity": {
            "review_record_sha256": None,
            "immutable_external_record_uri": "https://review.invalid/t080/1",
        },
        "release_evidence": False,
    }
    review["integrity"]["review_record_sha256"] = _record_digest(review, "review_record_sha256")
    return packet, review


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _completed_t070_fixture(root: Path) -> dict[str, Path]:
    source_bytes_digest = "a" * 64
    source_uri = "https://source.invalid/work-1"
    source = {
        "source_id": "source-1",
        "stable_uri": source_uri,
        "exact_acquired_copy_uri": "file:///review-cache/source-1.source",
        "sha256": source_bytes_digest,
        "title": "A reviewed work",
        "authors": ["A. Author"],
        "publisher": "Test Press",
        "publication_date": "2024-01-01",
        "doi": "10.5555/example.1",
        "attribution": "A. Author, A reviewed work, Test Press",
        "allowed_uses": ["candidate_generation", "human_annotation", "provenance_audit"],
        "licence": {
            "spdx": "CC-BY-4.0",
            "uri": "https://creativecommons.org/licenses/by/4.0/",
            "evidence_uri": "https://source.invalid/licence-1",
        },
        "third_party": {"status": "clear"},
        "approval": {"status": "not_requested", "reviewer_id": None},
        "state": "READY_FOR_HUMAN_ANNOTATION",
    }
    source_manifest = {
        "schema_version": "2.0.0",
        "status": "READY_FOR_HUMAN_ANNOTATION",
        "manifest_type": "source_candidate_manifest",
        "semantic_split_policy": {
            "criteria_id": "T070-TEMPORAL-LATER-YEAR-V1",
            "policy_version": "2.0.0",
        },
        "sources": [source],
    }
    source_manifest_path = root / "source-candidate-manifest.json"
    _write_json(source_manifest_path, source_manifest)
    source_manifest_digest = _file_digest(source_manifest_path)

    candidate = {
        "schema_version": "2.0.0",
        "packet_type": "citation_support_unlabelled_annotation",
        "pair_id": "pair-1",
        "packet_id": "packet-1",
        "source_id": "source-1",
        "source_digest": source_bytes_digest,
        "source_uri": source_uri,
        "acquired_copy_uri": source["exact_acquired_copy_uri"],
        "licence": "CC-BY-4.0",
        "attribution": source["attribution"],
        "discipline": "history",
        "candidate_claim": "The work records a documented event.",
        "exact_quote": "The work records a documented event.",
        "context": "A reviewed source context.",
        "claim_family_id": "claim-family-1",
        "group_id": "claim-family-1",
        "annotations": [
            {"annotator_id": None, "label": None, "rationale": None},
            {"annotator_id": None, "label": None, "rationale": None},
        ],
        "adjudication": {
            "adjudicator_id": None,
            "label": None,
            "rationale": None,
            "status": "pending",
        },
        "semantic_split": {
            "partition": "in_domain",
            "criteria_id": "T070-TEMPORAL-LATER-YEAR-V1",
            "publication_year": 2024,
        },
    }
    candidate_path = root / "unlabelled-candidate-pairs.jsonl"
    _write_jsonl(candidate_path, [candidate])
    packet_digest = _digest(candidate)

    rights_record = {
        "schema_version": "research-handoff.t070.source-rights-review.v1",
        "status": "human_reviewed",
        "source_binding": {
            "source_manifest_sha256": source_manifest_digest,
            "source_id": source["source_id"],
            "stable_uri": source["stable_uri"],
            "source_uri": source["stable_uri"],
            "acquired_copy_uri": source["exact_acquired_copy_uri"],
            "manifest_expected_sha256": source_bytes_digest,
            "title": source["title"],
            "authors": source["authors"],
            "publisher": source["publisher"],
            "publication_date": source["publication_date"],
            "doi": source["doi"],
            "attribution": source["attribution"],
            "allowed_uses_claimed_by_manifest": source["allowed_uses"],
            "licence_metadata": source["licence"],
            "third_party_warning": source["third_party"],
        },
        "reviewer": {
            "reviewer_id": "rights-reviewer-1",
            "role": "scholarly-rights-reviewer",
            "competence_basis": "documented copyright and scholarly-source review training",
            "conflict_declaration": {"has_conflict": False, "details": "none declared"},
            "reviewed_at": "2026-09-03T00:00:00Z",
        },
        "review": {
            "exact_acquired_copy_sha256_observed": source_bytes_digest,
            "source_work_identity_confirmed": True,
            "acquired_copy_identity_confirmed": True,
            "article_or_work_level_licence_confirmed": True,
            "licence_identifier_confirmed": True,
            "licence_evidence_uri_confirmed": True,
            "human_annotation_permitted": True,
            "derived_annotation_storage_permitted": True,
            "evaluation_use_permitted": True,
            "redistribution_of_source_bytes_permitted": False,
            "attribution_complete_and_correct": True,
            "named_authors_complete_and_correct": True,
            "third_party_material_inside_candidate_passages": False,
            "excluded_passage_locators": [],
            "limitations_and_obligations": [],
            "disposition": "approved_for_candidate_annotation",
            "allowed_dispositions": [
                "approved_for_candidate_annotation",
                "approved_with_exclusions",
                "rejected_rights",
                "rejected_identity",
                "needs_more_evidence",
            ],
            "rationale": "Article-level licence and exact copy identity verified.",
        },
        "integrity": {
            "review_record_sha256": None,
            "immutable_external_record_uri": "https://review.invalid/rights/source-1",
        },
    }
    rights_record["integrity"]["review_record_sha256"] = _record_digest(
        rights_record, "review_record_sha256"
    )
    rights_path = root / "source-rights-review-workset.json"
    rights_payload = {
        "schema_version": "research-handoff.t070.source-rights-workset.v1",
        "status": "READY_FOR_GENUINE_HUMAN_REVIEW_NOT_T070_EVIDENCE",
        "source_manifest_path": str(source_manifest_path),
        "source_manifest_sha256": source_manifest_digest,
        "source_count": 1,
        "records": [rights_record],
        "release_evidence": False,
    }
    _write_json(rights_path, rights_payload)

    def annotation(annotator_id: str, role: str, rationale: str) -> dict:
        record = {
            "schema_version": "research-handoff.t070.blind-annotation-item.v1",
            "status": "human_reviewed",
            "pair_binding": {
                "pair_id": candidate["pair_id"],
                "packet_id": candidate["packet_id"],
                "packet_sha256": packet_digest,
                "source_id": candidate["source_id"],
                "source_sha256": candidate["source_digest"],
                "claim_family_id": candidate["claim_family_id"],
                "discipline": candidate["discipline"],
                "candidate_claim": candidate["candidate_claim"],
                "exact_quote": candidate["exact_quote"],
                "context": candidate["context"],
                "source_uri": candidate["source_uri"],
                "acquired_copy_uri": candidate["acquired_copy_uri"],
                "licence": candidate["licence"],
                "attribution": candidate["attribution"],
            },
            "source_rights_review_binding": {
                "review_record_id": "rights:source-1",
                "review_record_sha256": rights_record["integrity"]["review_record_sha256"],
                "status_required": "approved_for_candidate_annotation",
            },
            "annotation": {
                "annotator_id": annotator_id,
                "annotator_role": role,
                "competence_basis": "discipline-specific source evaluation training",
                "independence_attestation": "I reviewed this pair independently.",
                "conflict_declaration": {"has_conflict": False, "details": "none declared"},
                "reviewed_at": "2026-09-03T00:00:00Z",
                "decision_origin": "human",
                "label": "directly_supports",
                "allowed_labels": T070_LABELS,
                "rationale": rationale,
                "quote_support_locator": "source-1:paragraph-1",
                "ambiguity_or_limitations": [],
                "disposition": "submitted_for_adjudication",
            },
            "integrity": {
                "record_sha256": None,
                "signed_or_immutable_external_record_uri": (
                    f"https://review.invalid/annotation/{annotator_id}/pair-1"
                ),
            },
        }
        record["integrity"]["record_sha256"] = _record_digest(record)
        return record

    annotator_a = annotation(
        "annotator-a", "history-annotator", "The quote states the claim directly."
    )
    annotator_b = annotation(
        "annotator-b", "history-annotator", "The quote states the claim directly."
    )
    annotator_a_path = root / "annotator-A.jsonl"
    annotator_b_path = root / "annotator-B.jsonl"
    _write_jsonl(annotator_a_path, [annotator_a])
    _write_jsonl(annotator_b_path, [annotator_b])

    adjudication = {
        "schema_version": "research-handoff.t070.adjudication-binding.v1",
        "status": "human_reviewed",
        "pair_binding": {
            "pair_id": candidate["pair_id"],
            "packet_sha256": packet_digest,
            "source_sha256": candidate["source_digest"],
            "claim_family_id": candidate["claim_family_id"],
        },
        "annotation_bindings": [
            {
                "slot": "A",
                "annotation_record_id": "annotation:annotator-a:pair-1",
                "annotation_record_sha256": annotator_a["integrity"]["record_sha256"],
                "annotator_id": "annotator-a",
            },
            {
                "slot": "B",
                "annotation_record_id": "annotation:annotator-b:pair-1",
                "annotation_record_sha256": annotator_b["integrity"]["record_sha256"],
                "annotator_id": "annotator-b",
            },
        ],
        "adjudication": {
            "adjudicator_id": "adjudicator-1",
            "adjudicator_role": "senior-history-adjudicator",
            "competence_basis": "senior scholarly evidence adjudication training",
            "independence_attestation": "I did not author the pair or either annotation.",
            "conflict_declaration": {"has_conflict": False, "details": "none declared"},
            "reviewed_at": "2026-09-03T00:00:00Z",
            "annotation_agreement_before_adjudication": True,
            "final_label": "directly_supports",
            "allowed_labels": T070_LABELS,
            "rationale": "Both independent annotations agree and the quote is direct support.",
            "resolved_disagreement": None,
            "limitations": [],
            "disposition": "adjudicated_for_dataset_review",
            "decision_origin": "human",
        },
        "integrity": {
            "record_sha256": None,
            "signed_or_immutable_external_record_uri": "https://review.invalid/adjudication/pair-1",
        },
    }
    adjudication["integrity"]["record_sha256"] = _record_digest(adjudication)
    adjudication_path = root / "adjudication-bindings.jsonl"
    _write_jsonl(adjudication_path, [adjudication])

    workset_manifest = {
        "schema_version": "research-handoff.t070.blind-workset-manifest.v1",
        "status": "READY_FOR_RIGHTS_BINDING_THEN_HUMAN_ANNOTATION",
        "source_pairs_path": str(candidate_path),
        "source_pairs_sha256": _file_digest(candidate_path),
        "pair_count": 1,
        "unique_pair_ids": 1,
        "unique_source_claim_quote_tuples": 1,
        "required_human_annotations_per_pair": 2,
        "required_independent_adjudications_per_pair": 1,
        "worksets": {
            "A": {"path": annotator_a_path.name, "sha256": _file_digest(annotator_a_path)},
            "B": {"path": annotator_b_path.name, "sha256": _file_digest(annotator_b_path)},
            "adjudication": {
                "path": adjudication_path.name,
                "sha256": _file_digest(adjudication_path),
            },
        },
        "source_rights_review": {
            "path": rights_path.name,
            "sha256": _file_digest(rights_path),
        },
        "release_evidence": False,
    }
    workset_manifest_path = root / "workset-manifest.json"
    _write_json(workset_manifest_path, workset_manifest)

    package_manifest = {
        "schema_version": "research-handoff.t070.human-review-package.v1",
        "status": "READY_FOR_GENUINE_HUMAN_REVIEW_NOT_T070_EVIDENCE",
        "pr_number": 66,
        "exact_candidate_head": "b" * 40,
        "source_workflow_head": "c" * 40,
        "source_count": 1,
        "pair_count": 1,
        "unique_source_claim_quote_tuples": 1,
        "inputs": {
            "source_manifest_sha256": source_manifest_digest,
            "candidate_pairs_sha256": _file_digest(candidate_path),
            "acquisition_report_sha256": "d" * 64,
        },
        "review_payloads": {
            "source_rights": {"path": rights_path.name, "sha256": _file_digest(rights_path)},
            "annotator_A": {
                "path": annotator_a_path.name,
                "sha256": _file_digest(annotator_a_path),
            },
            "annotator_B": {
                "path": annotator_b_path.name,
                "sha256": _file_digest(annotator_b_path),
            },
            "adjudication": {
                "path": adjudication_path.name,
                "sha256": _file_digest(adjudication_path),
            },
        },
        "human_requirements": {
            "source_rights_reviewer": "genuine competent human per exact source copy",
            "annotations_per_pair": 2,
            "annotators_independent": True,
            "adjudicator_distinct_from_both_annotators": True,
        },
        "release_evidence": False,
    }
    package_manifest_path = root / "package-manifest.json"
    _write_json(package_manifest_path, package_manifest)
    return {
        "candidate": candidate_path,
        "source_manifest": source_manifest_path,
        "rights": rights_path,
        "annotator_a": annotator_a_path,
        "annotator_b": annotator_b_path,
        "adjudication": adjudication_path,
        "workset_manifest": workset_manifest_path,
        "package_manifest": package_manifest_path,
    }


def _load_t079_module():
    spec = importlib.util.spec_from_file_location("t079_builder_regression", T079_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {T079_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class T079PreparationRegressionTests(unittest.TestCase):
    def test_category_selection_does_not_mutate_shared_source_pool(self) -> None:
        module = _load_t079_module()
        pool = [
            {
                "source_id": f"source-{index}",
                "metadata_status": {},
                "publisher": "publisher",
            }
            for index in range(8)
        ]
        original_pool = copy.deepcopy(pool)

        selected = module.select_for_category(
            pool,
            "method_monoculture",
            1,
            mailto="review@example.invalid",
            cache_dir=Path("cache"),
        )

        self.assertEqual(pool, original_pool)
        self.assertEqual(
            [source["methodology"] for source in selected],
            ["candidate_method_family_requires_human_verification"] * 7,
        )
        self.assertIsNot(selected[0], pool[0])

    def test_generator_writes_preparation_manifest_after_building_packets(self) -> None:
        module = _load_t079_module()

        def fake_packet(discipline: str, ordinal: int, pool, **_kwargs):
            partition, category = module.ALLOCATION[ordinal]
            return {
                "packet_id": f"TEST-{discipline}-{ordinal:02d}",
                "discipline": discipline,
                "partition": partition,
                "stress_category": category,
                "packet_digest": f"{ordinal:064d}",
            }

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_dir = root / "output"
            cache_dir = root / "cache"
            argv = [
                str(T079_SCRIPT),
                "--output-dir",
                str(output_dir),
                "--cache-dir",
                str(cache_dir),
                "--mailto",
                "review@example.invalid",
                "--pool-size",
                "12",
            ]
            with patch.object(module, "acquire_pool", return_value=[{}] * 12):
                with patch.object(module, "build_packet", side_effect=fake_packet):
                    with patch.object(sys, "argv", argv):
                        result = module.main()

            self.assertEqual(result, 0)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "READY_FOR_HUMAN_REVIEW")
            self.assertEqual(manifest["packet_count"], 108)
            self.assertFalse(manifest["release_evidence"])


class T070ReviewImportTests(unittest.TestCase):
    def _import(self, module, paths: dict[str, Path], output: Path) -> dict:
        return module.import_completed_reviews(
            candidate_pairs=paths["candidate"],
            source_manifest=paths["source_manifest"],
            rights_review=paths["rights"],
            workset_manifest=paths["workset_manifest"],
            annotator_a=paths["annotator_a"],
            annotator_b=paths["annotator_b"],
            adjudication=paths["adjudication"],
            package_manifest=paths["package_manifest"],
            output_dir=output,
        )

    def test_import_accepts_complete_human_reviews_as_staged_input(self) -> None:
        module = _load_t070_import_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = _completed_t070_fixture(root)
            result = self._import(module, paths, root / "imported")

            self.assertEqual(result["status"], "READY_FOR_DATASET_APPROVAL_NOT_RELEASE_EVIDENCE")
            self.assertEqual(result["pair_count"], 1)
            self.assertFalse(result["release_evidence"])
            self.assertEqual(result["exact_candidate_head"], "b" * 40)
            self.assertTrue((root / "imported" / "pairs.jsonl").is_file())
            self.assertTrue((root / "imported" / "source-licence-manifest.json").is_file())
            self.assertTrue((root / "imported" / "manifest.json").is_file())

    def test_import_rejects_candidate_bytes_that_do_not_match_package_binding(self) -> None:
        module = _load_t070_import_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = _completed_t070_fixture(root)
            paths["candidate"].write_text(
                paths["candidate"].read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "candidate[_ ]pairs"):
                self._import(module, paths, root / "imported")

    def test_import_rejects_machine_origin_and_non_distinct_adjudicator(self) -> None:
        module = _load_t070_import_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = _completed_t070_fixture(root)
            annotation = json.loads(
                paths["annotator_a"].read_text(encoding="utf-8").splitlines()[0]
            )
            annotation["annotation"]["decision_origin"] = "model"
            annotation["integrity"]["record_sha256"] = _record_digest(annotation)
            paths["annotator_a"].write_text(
                json.dumps(annotation, sort_keys=True) + "\n", encoding="utf-8"
            )
            workset_manifest = json.loads(paths["workset_manifest"].read_text(encoding="utf-8"))
            workset_manifest["worksets"]["A"]["sha256"] = _file_digest(paths["annotator_a"])
            paths["workset_manifest"].write_text(
                json.dumps(workset_manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "human decision origin"):
                self._import(module, paths, root / "imported")


class T080ReviewImportTests(unittest.TestCase):
    def test_build_rejects_reviews_not_bound_to_a_candidate(self) -> None:
        module = _load_t080_import_module()
        candidates = {
            "KNOWN": (
                Path("candidate.json"),
                {
                    "packet_id": "KNOWN",
                    "partition": "locked_candidate",
                    "discipline": "art_history",
                },
            )
        }
        reviews = {"UNKNOWN": (Path("review.json"), {})}

        with patch.object(module, "load_candidates", return_value=candidates):
            with patch.object(module, "load_reviews", return_value=reviews):
                with self.assertRaisesRegex(ValueError, "not bound"):
                    module.build(Path("candidates"), Path("reviews"))

    def test_build_marks_frozen_input_as_non_release_evidence(self) -> None:
        module = _load_t080_import_module()
        candidates = {}
        reviews = {}
        expected_items = {}
        for discipline in module.SUPPORTED_DISCIPLINES:
            for ordinal in range(1, 11):
                packet_id = f"{discipline}-{ordinal:02d}"
                candidates[packet_id] = (
                    Path(f"{packet_id}.json"),
                    {
                        "packet_id": packet_id,
                        "partition": "locked_candidate",
                        "discipline": discipline,
                    },
                )
                reviews[packet_id] = (Path(f"{packet_id}-review.json"), {})
                expected_items[packet_id] = {
                    "packet_id": packet_id,
                    "discipline": discipline,
                }

        with patch.object(module, "load_candidates", return_value=candidates):
            with patch.object(module, "load_reviews", return_value=reviews):
                with patch.object(
                    module,
                    "validate_lock",
                    side_effect=lambda packet, _review, _path: expected_items[packet["packet_id"]],
                ):
                    manifest = module.build(Path("candidates"), Path("reviews"))

        self.assertFalse(manifest["release_evidence"])

    def test_validate_lock_requires_explicit_human_conflict_and_truth_provenance(self) -> None:
        module = _load_t080_import_module()
        packet, review = _t080_packet_and_review()
        review["reviewer"]["conflict_declaration"] = None
        review["review"]["decision_origin"] = "model"

        with tempfile.TemporaryDirectory() as temporary_directory:
            review_path = Path(temporary_directory) / "review.json"
            _write_json(review_path, review)
            with self.assertRaisesRegex(ValueError, "conflict"):
                module.validate_lock(packet, review, review_path)

    def test_validate_lock_requires_all_digest_bindings(self) -> None:
        module = _load_t080_import_module()
        packet, review = _t080_packet_and_review()
        del review["packet_binding"]["source_metadata_snapshot_sha256"]

        with tempfile.TemporaryDirectory() as temporary_directory:
            review_path = Path(temporary_directory) / "review.json"
            _write_json(review_path, review)
            with self.assertRaisesRegex(ValueError, "source_metadata_snapshot"):
                module.validate_lock(packet, review, review_path)

    def test_load_candidates_requires_the_complete_candidate_manifest(self) -> None:
        module = _load_t080_import_module()
        packet, _ = _t080_packet_and_review()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            packet_path = root / "packet.json"
            _write_json(packet_path, packet)

            with self.assertRaisesRegex(ValueError, "manifest"):
                module.load_candidates(root)


if __name__ == "__main__":
    unittest.main()
