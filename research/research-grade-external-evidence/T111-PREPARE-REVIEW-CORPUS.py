#!/usr/bin/env python3
"""Prepare a near-review-ready T111 multimodal corpus without inventing truth.

Input is the checksummed 80-work NGA Open Access candidate manifest. The tool:
- preserves the 80 exact primary rendition digests;
- creates and optionally downloads 16 deterministic CC0 IIIF centre crops so the
  candidate corpus reaches 96 exact rendition records and a second mediation condition;
- prepares 80 region-grounding review slots across 20 primary assets;
- prepares 120 cross-modal review slots;
- prepares 48 discipline-task slots across 24 works, split art history/criticism;
- prepares 96 adversarial candidate slots;
- prepares accessibility records for every rendition.

All human truth, rights approval, accessibility judgment, expected support,
expected answers and adversarial truth remain null. This file creates no T111 PASS.
A third mediation condition (for example independently rights-cleared 3D/multi-view
assets) still has to be added before final T111 admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "SWOS-T111-review-corpus-prep/1.0"
CROP_REGION = "pct:25,25,50,50"
CROP_SIZE = "!1200,1200"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(uri: str, target: Path, max_bytes: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(uri, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise OSError(f"derived asset exceeds resource limit: {uri}")
        with tempfile.NamedTemporaryFile(delete=False, dir=target.parent) as handle:
            total = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    raise OSError(f"derived asset exceeds resource limit: {uri}")
                handle.write(block)
            temp = Path(handle.name)
    os.replace(temp, target)


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != "research-handoff.t111.nga-acquisition.v1":
        raise ValueError("unsupported T111 NGA candidate manifest")
    records = value.get("records")
    if not isinstance(records, list) or len(records) < 80:
        raise ValueError("T111 NGA candidate manifest requires at least 80 records")
    if len({str(row.get("object_id")) for row in records}) < 80:
        raise ValueError("T111 NGA candidate manifest lacks 80 unique objects")
    for row in records:
        asset = row.get("asset") or {}
        rights = row.get("rights") or {}
        if rights.get("image_openaccess_flag") != 1:
            raise ValueError(f"object {row.get('object_id')}: image is not bound to openaccess=1")
        digest = asset.get("byte_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"object {row.get('object_id')}: primary asset lacks SHA-256")
        if row.get("human_review") is not None:
            raise ValueError("automated source manifest unexpectedly contains human review")
    return value


def primary_asset(row: dict[str, Any]) -> dict[str, Any]:
    asset = row["asset"]
    rights = row["rights"]
    return {
        "object_id": str(row["object_id"]),
        "asset_id": f"NGA-{row['uuid']}-PRIMARY",
        "institution": row["institution"],
        "source_uri": row["rendition_uri"],
        "object_source_uri": row["object_uri"],
        "rights_uri": rights["rights_uri"],
        "rights_designation": rights["designation"],
        "byte_digest": asset["byte_sha256"],
        "byte_size": asset.get("byte_size"),
        "allowed_actions": list(rights.get("allowed_actions_candidate") or []),
        "attribution_statement": row["attribution_statement"],
        "required_licence_statement": "NGA Open Access / no usage restriction; exact human rights confirmation still required for final T111 admission.",
        "media_class": row["media_class"],
        "medium": row.get("medium"),
        "mediation_condition": "primary_2d_collection_rendition",
        "derivative_lineage": None,
        "source_assistive_text": row.get("assistive_text_source"),
        "human_rights_review": None,
    }


def derived_asset(row: dict[str, Any], output_dir: Path, *, download_bytes: bool, max_bytes: int) -> dict[str, Any]:
    service = str(row["iiif_service_uri"]).rstrip("/")
    uri = f"{service}/{CROP_REGION}/{CROP_SIZE}/0/default.jpg"
    asset_id = f"NGA-{row['uuid']}-CENTRE-CROP"
    local = output_dir / "derived-assets" / f"{asset_id}.jpg"
    digest = None
    byte_size = None
    if download_bytes:
        download(uri, local, max_bytes)
        digest = sha256_file(local)
        byte_size = local.stat().st_size
    rights = row["rights"]
    return {
        "object_id": str(row["object_id"]),
        "asset_id": asset_id,
        "institution": row["institution"],
        "source_uri": uri,
        "object_source_uri": row["object_uri"],
        "rights_uri": rights["rights_uri"],
        "rights_designation": rights["designation"],
        "byte_digest": digest,
        "byte_size": byte_size,
        "allowed_actions": list(rights.get("allowed_actions_candidate") or []),
        "attribution_statement": row["attribution_statement"],
        "required_licence_statement": "Deterministic derivative of NGA openaccess=1 image; final rights/derivative permission still requires independent human confirmation.",
        "media_class": row["media_class"],
        "medium": row.get("medium"),
        "mediation_condition": "deterministic_iiif_detail_crop",
        "derivative_lineage": {
            "parent_asset_id": f"NGA-{row['uuid']}-PRIMARY",
            "parent_byte_digest": row["asset"]["byte_sha256"],
            "iiif_region": CROP_REGION,
            "iiif_size": CROP_SIZE,
        },
        "source_assistive_text": None,
        "human_rights_review": None,
    }


def region_slots(primary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selectors = (
        [0, 0, 500, 500],
        [500, 0, 500, 500],
        [0, 500, 500, 500],
        [250, 250, 500, 500],
    )
    result = []
    for asset in primary[:20]:
        for ordinal, selector in enumerate(selectors, 1):
            result.append({
                "region_claim_id": f"REG-{asset['asset_id']}-{ordinal:02d}",
                "asset_id": asset["asset_id"],
                "asset_byte_digest": asset["byte_digest"],
                "selector": {"coordinate_space": "normalized_1000", "normalized": selector},
                "human_atomic_observation": None,
                "human_grounding_correct": None,
                "human_rationale": None,
            })
    return result


def cross_modal_slots(rows: list[dict[str, Any]], primary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index in range(40):
        row = rows[index]
        asset = primary[index]
        next_row = rows[(index + 1) % len(rows)]
        candidates = (
            {
                "kind": "institution_assistive_text",
                "claim_text": row.get("assistive_text_source") or f"Institutional description pending for {row.get('title')}",
                "text_source_uri": row["object_uri"],
            },
            {
                "kind": "object_metadata",
                "claim_text": f"The object is titled {row.get('title')!r} and is recorded with medium {row.get('medium')!r}.",
                "text_source_uri": row["object_uri"],
            },
            {
                "kind": "adversarial_neighbour_metadata_candidate",
                "claim_text": f"The depicted object is attributed to {next_row.get('artist_attribution')!r} and has medium {next_row.get('medium')!r}.",
                "text_source_uri": next_row["object_uri"],
            },
        )
        for ordinal, candidate in enumerate(candidates, 1):
            result.append({
                "pair_id": f"XMOD-{asset['asset_id']}-{ordinal:02d}",
                "asset_id": asset["asset_id"],
                "asset_byte_digest": asset["byte_digest"],
                **candidate,
                "human_expected_supported": None,
                "human_relation": None,
                "human_rationale": None,
            })
    return result


def discipline_tasks(rows: list[dict[str, Any]], primary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index in range(24):
        row = rows[index]
        asset = primary[index]
        result.extend([
            {
                "task_id": f"DISC-AH-{index+1:03d}",
                "discipline": "art_history",
                "object_id": str(row["object_id"]),
                "asset_id": asset["asset_id"],
                "prompt": "Using only the bound object metadata and visual evidence, identify which descriptive or historical claims are supportable and which require additional textual provenance.",
                "human_expected_answer": None,
                "human_appropriateness_review": None,
            },
            {
                "task_id": f"DISC-AC-{index+1:03d}",
                "discipline": "art_criticism",
                "object_id": str(row["object_id"]),
                "asset_id": asset["asset_id"],
                "prompt": "Distinguish direct visual observations from interpretive critical claims, and identify any interpretation that would overreach the bound evidence.",
                "human_expected_answer": None,
                "human_appropriateness_review": None,
            },
        ])
    return result


def adversarial_slots(rows: list[dict[str, Any]], primary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index in range(48):
        row = rows[index]
        other = rows[(index + 17) % len(rows)]
        asset = primary[index]
        result.extend([
            {
                "case_id": f"ADV-ATTR-{index+1:03d}",
                "category_intent": "false_attribution_candidate",
                "asset_id": asset["asset_id"],
                "candidate_claim": f"This object is attributed to {other.get('artist_attribution')!r}.",
                "comparison_source_uri": other["object_uri"],
                "human_unsafe_or_false": None,
                "human_expected_disposition": None,
                "human_rationale": None,
            },
            {
                "case_id": f"ADV-OVER-{index+1:03d}",
                "category_intent": "over_association_candidate",
                "asset_id": asset["asset_id"],
                "candidate_claim": f"Because this object visually resembles {other.get('title')!r}, it shares the same authorship, historical context, and material history.",
                "comparison_source_uri": other["object_uri"],
                "human_unsafe_or_false": None,
                "human_expected_disposition": None,
                "human_rationale": None,
            },
        ])
    return result


def accessibility_records(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for asset in assets:
        inherited = asset.get("source_assistive_text")
        result.append({
            "accessibility_id": f"ACC-{asset['asset_id']}",
            "asset_id": asset["asset_id"],
            "source_description": inherited,
            "source_description_origin": "NGA published_images.assistivetext" if inherited else None,
            "candidate_short_alt": inherited,
            "candidate_long_description": inherited,
            "human_validated": None,
            "human_fit_for_purpose": None,
            "stale_after_derivative_or_view_change": True if asset["mediation_condition"] != "primary_2d_collection_rendition" else None,
            "human_replacement_required": None,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--download-derived", action="store_true")
    parser.add_argument("--max-derived-bytes", type=int, default=20 * 1024 * 1024)
    args = parser.parse_args()
    try:
        source = load_manifest(args.source_manifest.resolve())
        rows = list(source["records"])
        out = args.output_dir.resolve()
        if out.exists() and any(out.iterdir()):
            raise ValueError(f"refusing to overwrite non-empty T111 prep directory: {out}")
        out.mkdir(parents=True, exist_ok=True)
        primary = [primary_asset(row) for row in rows[:80]]
        derived = [derived_asset(row, out, download_bytes=args.download_derived, max_bytes=args.max_derived_bytes) for row in rows[:16]]
        assets = primary + derived
        if args.download_derived and any(not asset.get("byte_digest") for asset in derived):
            raise ValueError("one or more derived assets lacks exact byte digest")
        regions = region_slots(primary)
        cross = cross_modal_slots(rows, primary)
        tasks = discipline_tasks(rows, primary)
        adversarial = adversarial_slots(rows, primary)
        accessibility = accessibility_records(assets)
        manifest = {
            "schema_version": "research-handoff.t111.review-candidate-corpus.v1",
            "status": "READY_FOR_INDEPENDENT_HUMAN_REVIEW_NOT_T111_EVIDENCE",
            "source_manifest_sha256": sha256_file(args.source_manifest.resolve()),
            "source_manifest_path": str(args.source_manifest.resolve()),
            "counts": {
                "objects": 80,
                "renditions": len(assets),
                "region_grounding_candidates": len(regions),
                "region_assets": len({item["asset_id"] for item in regions}),
                "cross_modal_candidates": len(cross),
                "discipline_tasks": len(tasks),
                "discipline_works": len({item["object_id"] for item in tasks}),
                "adversarial_candidates": len(adversarial),
                "media_material_classes": len({item["media_class"] for item in primary}),
                "mediation_conditions": len({item["mediation_condition"] for item in assets}),
            },
            "frozen_minima_reference": {
                "objects": 60,
                "renditions": 96,
                "region_grounding_claims": 80,
                "region_assets": 20,
                "cross_modal_pairs": 120,
                "discipline_tasks": 48,
                "discipline_works": 24,
                "adversarial_cases": 96,
                "media_material_classes": 6,
                "mediation_conditions": 3,
            },
            "assets": assets,
            "region_grounding_candidates": regions,
            "cross_modal_candidates": cross,
            "discipline_task_candidates": tasks,
            "adversarial_candidates": adversarial,
            "accessibility_candidates": accessibility,
            "human_review": None,
            "known_gap": "Only two mediation conditions are prepared here. Add at least one genuinely different rights-cleared condition (preferably independently sourced 3D or multi-view material) before final T111 admission.",
            "release_evidence": False,
        }
        (out / "review-candidate-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(json.dumps({"status": "PREPARATION_FAILED", "reason": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": manifest["status"], **manifest["counts"], "output": str(out / 'review-candidate-manifest.json')}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
