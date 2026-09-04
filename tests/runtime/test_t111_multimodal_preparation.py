"""Regression tests for the T111 multimodal candidate preparation boundary."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
T111_SCRIPT = (
    REPOSITORY_ROOT
    / "research"
    / "research-grade-external-evidence"
    / "T111-PREPARE-REVIEW-CORPUS.py"
)


def _load_t111_module():
    spec = importlib.util.spec_from_file_location("t111_prepare_review_corpus", T111_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {T111_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_digest(record: dict, field: str) -> str:
    value = json.loads(json.dumps(record))
    value["integrity"][field] = None
    return _digest(value)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _source_manifest(root: Path) -> tuple[Path, dict]:
    records = []
    for index in range(80):
        uuid = f"{index + 1:032x}"[-36:]
        records.append(
            {
                "uuid": uuid,
                "object_id": str(100_000 + index),
                "institution": "National Gallery of Art, Washington",
                "object_uri": f"https://www.nga.gov/artworks/{100_000 + index}",
                "rendition_uri": f"https://api.nga.gov/iiif/{uuid}/full/!1600,1600/0/default.jpg",
                "iiif_service_uri": f"https://api.nga.gov/iiif/{uuid}",
                "media_class": "painting" if index % 2 else "sculpture",
                "medium": "oil on canvas",
                "title": f"Work {index + 1}",
                "artist_attribution": f"Artist {index + 1}",
                "attribution_statement": f"National Gallery of Art — Work {index + 1}",
                "assistive_text_source": None,
                "rights": {
                    "rights_uri": "https://www.nga.gov/artworks/free-images-and-open-access",
                    "designation": "NGA Open Access / no usage restriction",
                    "image_openaccess_flag": 1,
                    "allowed_actions_candidate": ["view", "analyse", "transform"],
                },
                "asset": {
                    "byte_sha256": f"{index + 1:064x}"[-64:],
                    "byte_size": 1000 + index,
                },
                "human_review": None,
            }
        )
    payload = {
        "schema_version": "research-handoff.t111.nga-acquisition.v1",
        "status": "candidate_assets_prepared_human_review_required",
        "release_evidence": False,
        "records": records,
    }
    path = root / "source-manifest.json"
    _write_json(path, payload)
    return path, payload


def _alternate_manifest(root: Path, source_path: Path, *, duplicate_digest: bool = False) -> Path:
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    records = []
    for index in range(16):
        uuid = f"alternate-{index + 1:02d}"
        object_index = index if index < 10 else 80 + (index - 10)
        records.append(
            {
                "candidate_id": f"MM-NGA-ALT-{index + 1:03d}",
                "object_id": str(100_000 + object_index),
                "asset_id": f"NGA-{uuid}-ALTERNATE",
                "uuid": uuid,
                "institution": "National Gallery of Art, Washington",
                "object_source_uri": f"https://www.nga.gov/artworks/{100_000 + object_index}",
                "source_uri": f"https://api.nga.gov/iiif/{uuid}/full/!1600,1600/0/default.jpg",
                "iiif_service_uri": f"https://api.nga.gov/iiif/{uuid}",
                "viewtype": "alternate",
                "sequence": 1,
                "mediation_condition": "institutional_alternate_view",
                "rights_uri": "https://www.nga.gov/artworks/free-images-and-open-access",
                "rights_designation": "NGA Open Access / no usage restriction",
                "image_openaccess_flag": 1,
                "allowed_actions_candidate": ["view", "analyse", "transform"],
                "attribution_statement": f"National Gallery of Art — Work {index + 1}",
                "byte_sha256": (
                    f"{index + 1:064x}"[-64:] if duplicate_digest else f"{index + 81:064x}"[-64:]
                ),
                "byte_size": 2000 + index,
                "source_width": "1600",
                "source_height": "1200",
                "source_assistive_text": None,
                "human_rights_review": None,
                "human_identity_review": None,
            }
        )
    payload = {
        "schema_version": "research-handoff.t111.nga-alternate-views.v1",
        "status": "THIRD_MEDIATION_CANDIDATES_READY_FOR_HUMAN_REVIEW",
        "source_candidate_manifest_sha256": source_digest,
        "record_count": len(records),
        "mediation_condition": "institutional_alternate_view",
        "records": records,
        "human_review": None,
        "release_evidence": False,
    }
    path = root / "alternate-manifest.json"
    _write_json(path, payload)
    return path


def _completed_review_fixture(root: Path) -> tuple[Path, Path]:
    asset = {
        "asset_id": "NGA-test-PRIMARY",
        "object_id": "100001",
        "institution": "National Gallery of Art, Washington",
        "source_uri": "https://api.nga.gov/iiif/test/full/!1600,1600/0/default.jpg",
        "acquisition_uri": "https://api.nga.gov/iiif/test/full/!1600,1600/0/default.jpg",
        "mime_type": "image/jpeg",
        "width": 1600,
        "height": 1200,
        "object_source_uri": "https://www.nga.gov/artworks/100001",
        "rights_uri": "https://www.nga.gov/artworks/free-images-and-open-access",
        "rights_designation": "NGA Open Access / no usage restriction",
        "byte_digest": "a" * 64,
        "byte_size": 1234,
        "allowed_actions": [
            "view",
            "analyse",
            "transform",
            "create_derivative",
            "quote",
            "cache",
            "export",
            "redistribute",
        ],
        "attribution_statement": "National Gallery of Art — Test work",
        "required_licence_statement": "NGA Open Access; human review required.",
        "media_class": "painting",
        "medium": "oil on canvas",
        "mediation_condition": "primary_2d_collection_rendition",
        "derivative_lineage": None,
        "source_assistive_text": None,
        "human_rights_review": None,
        "human_identity_review": None,
    }
    asset["object_record_sha256"] = _digest(
        {
            "object_id": asset["object_id"],
            "institution": asset["institution"],
            "object_source_uri": asset["object_source_uri"],
        }
    )
    asset["asset_record_sha256"] = _digest(asset)
    candidate = {
        "schema_version": "research-handoff.t111.review-candidate-corpus.v1",
        "status": "READY_FOR_INDEPENDENT_HUMAN_REVIEW_NOT_T111_EVIDENCE",
        "release_evidence": False,
        "human_review": None,
        "counts": {
            "objects": 1,
            "renditions": 1,
            "region_grounding_candidates": 1,
            "region_assets": 1,
            "cross_modal_candidates": 1,
            "discipline_tasks": 1,
            "discipline_works": 1,
            "adversarial_candidates": 1,
            "media_material_classes": 1,
            "mediation_conditions": 1,
        },
        "assets": [asset],
        "region_grounding_candidates": [
            {
                "region_claim_id": "REG-1",
                "asset_id": asset["asset_id"],
                "asset_byte_digest": asset["byte_digest"],
                "selector": {
                    "coordinate_space": "normalized_1000",
                    "normalized": [0, 0, 1000, 1000],
                },
                "human_atomic_observation": None,
                "human_grounding_correct": None,
                "human_rationale": None,
            }
        ],
        "cross_modal_candidates": [
            {
                "pair_id": "XMOD-1",
                "asset_id": asset["asset_id"],
                "asset_byte_digest": asset["byte_digest"],
                "kind": "object_metadata",
                "claim_text": "The bound object has a recorded title.",
                "text_source_uri": asset["object_source_uri"],
                "human_expected_supported": None,
                "human_relation": None,
                "human_rationale": None,
            }
        ],
        "discipline_task_candidates": [
            {
                "task_id": "DISC-AH-001",
                "discipline": "art_history",
                "object_id": asset["object_id"],
                "asset_id": asset["asset_id"],
                "prompt": "Separate observation from historical inference.",
                "human_expected_answer": None,
                "human_appropriateness_review": None,
            }
        ],
        "adversarial_candidates": [
            {
                "case_id": "ADV-1",
                "asset_id": asset["asset_id"],
                "category_intent": "false_attribution_candidate",
                "candidate_claim": "This object has an unsupported attribution.",
                "comparison_source_uri": asset["object_source_uri"],
                "human_unsafe_or_false": None,
                "human_expected_disposition": None,
                "human_rationale": None,
            }
        ],
        "accessibility_candidates": [
            {
                "accessibility_id": f"ACC-{asset['asset_id']}",
                "asset_id": asset["asset_id"],
                "source_description": None,
                "candidate_short_alt": None,
                "candidate_long_description": None,
                "human_validated": None,
                "human_fit_for_purpose": None,
                "human_replacement_required": None,
            }
        ],
    }
    candidate_path = root / "candidate-manifest.json"
    _write_json(candidate_path, candidate)
    candidate_digest = _file_digest(candidate_path)
    review = {
        "schema_version": "research-handoff.t111.independent-review.v1",
        "status": "human_reviewed",
        "release_evidence": False,
        "review_id": "review-1",
        "candidate_manifest_sha256": candidate_digest,
        "object_binding": {
            "object_id": asset["object_id"],
            "object_record_sha256": asset["object_record_sha256"],
            "institution": asset["institution"],
            "object_source_uri": asset["object_source_uri"],
        },
        "asset_bindings": [
            {
                "asset_id": asset["asset_id"],
                "object_id": asset["object_id"],
                "object_record_sha256": asset["object_record_sha256"],
                "asset_record_sha256": asset["asset_record_sha256"],
                "source_uri": asset["source_uri"],
                "byte_sha256": asset["byte_digest"],
                "rights_uri": asset["rights_uri"],
                "derivative_parent_sha256": None,
            }
        ],
        "evaluation_expectations": {
            asset["asset_id"]: {
                "status": "complete",
                "target_questions": ["What is directly visible?"],
                "allowed_actions": asset["allowed_actions"],
                "discipline": "art_history",
                "ontology_binding": {"version": "2.0.0"},
                "resource_limits": {"max_assets": 1, "max_observations": 4, "max_seconds": 60},
                "provider_policy": {},
            }
        },
        "reviewer": {
            "reviewer_id": "human-reviewer-1",
            "role": "independent-multimodal-reviewer",
            "discipline_competence_basis": "documented art-history training",
            "rights_review_competence_basis": "documented rights-review training",
            "independence_attestation": "I reviewed independently.",
            "reviewed_at": "2026-09-04T00:00:00Z",
            "conflict_declaration": {"has_conflict": False, "details": "none"},
            "decision_origin": "human",
        },
        "rights_review": {
            "object_asset_identity_correct": True,
            "rights_designation_verified": True,
            "third_party_restrictions_checked": True,
            "allowed_actions_verified": asset["allowed_actions"],
            "attribution_or_credit_correct": True,
            "derivative_lineage_correct": True,
            "disposition": "admit",
            "rationale": "Exact source and rights records were reviewed.",
            "decision_origin": "human",
        },
        "grounding_review": {
            "region_claim_records_reviewed": ["REG-1"],
            "decisions": {
                "REG-1": {
                    "observation": "A bounded visual observation.",
                    "observation_ids": ["observation-1"],
                    "grounding_correct": True,
                    "expected_region": [0, 0, 1600, 1200],
                    "rationale": "The selector is bounded to the reviewed asset.",
                }
            },
            "rationale": "The region claim is directly reviewable.",
            "decision_origin": "human",
        },
        "cross_modal_review": {
            "pair_records_reviewed": ["XMOD-1"],
            "decisions": {
                "XMOD-1": {
                    "expected_supported": True,
                    "relation": "supported",
                    "rationale": "The bound metadata supports the claim.",
                }
            },
            "rationale": "The text/image relation is explicit.",
            "decision_origin": "human",
        },
        "discipline_review": {
            "task_records_reviewed": ["DISC-AH-001"],
            "decisions": {
                "DISC-AH-001": {
                    "appropriate": True,
                    "expected_answer": "Only the visible description is supported.",
                    "rationale": "The task separates observation and inference.",
                }
            },
            "rationale": "The discipline task is appropriate.",
            "decision_origin": "human",
        },
        "accessibility_review": {
            "accessibility_records_reviewed": [f"ACC-{asset['asset_id']}"],
            "decisions": {
                f"ACC-{asset['asset_id']}": {
                    "purpose": "evidentiary",
                    "short_alternative": "A painting in the reviewed collection.",
                    "long_description": "A bounded description for evidentiary use.",
                    "fit_for_purpose": True,
                    "human_validated": True,
                    "rationale": "The description is fit for the declared purpose.",
                }
            },
            "rationale": "Accessibility was reviewed independently.",
            "decision_origin": "human",
        },
        "adversarial_review": {
            "case_records_reviewed": ["ADV-1"],
            "decisions": {
                "ADV-1": {
                    "unsafe_or_false": True,
                    "expected_disposition": "block",
                    "rationale": "The attribution is unsupported by the bound evidence.",
                }
            },
            "rationale": "The adversarial case is valid.",
            "decision_origin": "human",
        },
        "overall": {
            "disposition": "lock",
            "limitations": ["One test object is used only for importer regression."],
            "rationale": "All candidate review legs are complete.",
            "decision_origin": "human",
        },
        "integrity": {
            "review_record_sha256": None,
            "immutable_external_record_uri": "https://review.invalid/t111/review-1",
        },
    }
    review["integrity"]["review_record_sha256"] = _record_digest(review, "review_record_sha256")
    review_path = root / "completed-reviews.jsonl"
    _write_jsonl(review_path, [review])
    return candidate_path, review_path


class T111MultimodalPreparationTests(unittest.TestCase):
    def test_alternate_manifest_is_bound_to_exact_primary_manifest_bytes(self) -> None:
        module = _load_t111_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, _ = _source_manifest(root)
            alternate_path = _alternate_manifest(root, source_path)

            loaded = module.load_alternate_manifest(alternate_path, source_path)

            self.assertEqual(16, loaded["record_count"])
            self.assertTrue(
                all(record["human_rights_review"] is None for record in loaded["records"])
            )
            self.assertTrue(
                all(record["human_identity_review"] is None for record in loaded["records"])
            )

    def test_preparation_merges_primary_crop_and_alternate_renditions(self) -> None:
        module = _load_t111_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, _ = _source_manifest(root)
            alternate_path = _alternate_manifest(root, source_path)
            output = root / "output"

            result = module.prepare_corpus(
                source_path,
                output,
                alternate_view_manifest=alternate_path,
                download_derived=False,
            )

            self.assertEqual(86, result["counts"]["objects"])
            self.assertEqual(112, result["counts"]["renditions"])
            self.assertEqual(3, result["counts"]["mediation_conditions"])
            self.assertEqual(16, result["counts"]["alternate_view_renditions"])
            self.assertEqual(80, result["counts"]["primary_renditions"])
            self.assertFalse(result["release_evidence"])
            self.assertIsNone(result["human_review"])
            self.assertEqual(
                112,
                len({asset["asset_id"] for asset in result["assets"]}),
            )

    def test_duplicate_primary_and_alternate_bytes_are_rejected(self) -> None:
        module = _load_t111_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, _ = _source_manifest(root)
            alternate_path = _alternate_manifest(root, source_path, duplicate_digest=True)

            with self.assertRaisesRegex(ValueError, "duplicate.*rendition|byte digest"):
                module.prepare_corpus(
                    source_path,
                    root / "output",
                    alternate_view_manifest=alternate_path,
                    download_derived=False,
                )

    def test_alternate_view_manifest_digest_mismatch_fails_closed(self) -> None:
        module = _load_t111_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, _ = _source_manifest(root)
            alternate_path = _alternate_manifest(root, source_path)
            payload = json.loads(alternate_path.read_text(encoding="utf-8"))
            payload["source_candidate_manifest_sha256"] = "0" * 64
            _write_json(alternate_path, payload)

            with self.assertRaisesRegex(ValueError, "source candidate manifest.*digest"):
                module.load_alternate_manifest(alternate_path, source_path)

    def test_completed_review_import_requires_all_human_legs_and_keeps_release_off(self) -> None:
        importer_spec = importlib.util.spec_from_file_location(
            "t111_import_completed_reviews",
            REPOSITORY_ROOT
            / "research"
            / "research-grade-external-evidence"
            / "T111-IMPORT-COMPLETED-REVIEWS.py",
        )
        if importer_spec is None or importer_spec.loader is None:
            raise RuntimeError("unable to load T111 importer")
        importer = importlib.util.module_from_spec(importer_spec)
        importer_spec.loader.exec_module(importer)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path, review_path = _completed_review_fixture(root)
            result = importer.import_completed_reviews(
                candidate_path,
                review_path,
                root / "imported",
                minimums={name: 1 for name in importer.MINIMUMS if name != "mediation_conditions"}
                | {"mediation_conditions": 1},
            )

            self.assertEqual("ready", result["status"])
            self.assertFalse(result["release_evidence"])
            self.assertEqual(1, len(result["cases"]))
            self.assertEqual(
                "reviewed", result["asset_records"][0]["accessibility"]["review_status"]
            )
            self.assertEqual(
                result["review"]["review_record_digests"][0]["review_record_sha256"],
                result["asset_records"][0]["provenance"]["review_record_sha256"],
            )

    def test_completed_review_rejects_machine_decision_origin(self) -> None:
        importer_spec = importlib.util.spec_from_file_location(
            "t111_import_completed_reviews_machine_origin",
            REPOSITORY_ROOT
            / "research"
            / "research-grade-external-evidence"
            / "T111-IMPORT-COMPLETED-REVIEWS.py",
        )
        if importer_spec is None or importer_spec.loader is None:
            raise RuntimeError("unable to load T111 importer")
        importer = importlib.util.module_from_spec(importer_spec)
        importer_spec.loader.exec_module(importer)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path, review_path = _completed_review_fixture(root)
            review = json.loads(review_path.read_text(encoding="utf-8").splitlines()[0])
            review["grounding_review"]["decision_origin"] = "model"
            review["integrity"]["review_record_sha256"] = _record_digest(
                review, "review_record_sha256"
            )
            _write_jsonl(review_path, [review])

            with self.assertRaisesRegex(ValueError, "human decision origin"):
                importer.import_completed_reviews(
                    candidate_path,
                    review_path,
                    root / "imported",
                    minimums={name: 1 for name in importer.MINIMUMS},
                )


if __name__ == "__main__":
    unittest.main()
