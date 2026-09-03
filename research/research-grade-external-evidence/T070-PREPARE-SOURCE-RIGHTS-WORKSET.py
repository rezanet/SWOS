#!/usr/bin/env python3
"""Prepare one blank rights/identity review record per T070 candidate source.

The tool binds every form to the exact source-candidate manifest bytes and copies
only acquisition/provenance/licence metadata already present in that manifest.
It never decides whether a source is legally or identity-wise approved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DISPOSITIONS = (
    "approved_for_candidate_annotation",
    "approved_with_exclusions",
    "rejected_rights",
    "rejected_identity",
    "needs_more_evidence",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest_path = args.source_manifest.resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        sources = manifest.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError("source manifest has no sources array")
        source_ids: set[str] = set()
        records = []
        for index, source in enumerate(sources, 1):
            if not isinstance(source, dict):
                raise ValueError(f"source {index}: object required")
            source_id = source.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise ValueError(f"source {index}: source_id required")
            if source_id in source_ids:
                raise ValueError(f"duplicate source_id: {source_id}")
            source_ids.add(source_id)
            licence = source.get("licence") if isinstance(source.get("licence"), dict) else {}
            records.append({
                "schema_version": "research-handoff.t070.source-rights-review.v1",
                "status": "blank_template_not_evidence",
                "source_binding": {
                    "source_manifest_sha256": sha256_file(manifest_path),
                    "source_id": source_id,
                    "stable_uri": source.get("stable_uri"),
                    "source_uri": source.get("source_uri") or source.get("stable_uri"),
                    "acquired_copy_uri": source.get("content_uri") or source.get("acquired_copy_uri"),
                    "manifest_expected_sha256": source.get("expected_sha256") or source.get("source_digest"),
                    "title": source.get("title"),
                    "authors": source.get("authors"),
                    "publisher": source.get("publisher"),
                    "publication_date": source.get("publication_date"),
                    "doi": source.get("doi"),
                    "attribution": source.get("attribution"),
                    "allowed_uses_claimed_by_manifest": source.get("allowed_uses"),
                    "licence_metadata": licence,
                    "third_party_warning": source.get("third_party"),
                },
                "reviewer": {
                    "reviewer_id": None,
                    "role": None,
                    "competence_basis": None,
                    "conflict_declaration": None,
                    "reviewed_at": None,
                },
                "review": {
                    "exact_acquired_copy_sha256_observed": None,
                    "source_work_identity_confirmed": None,
                    "acquired_copy_identity_confirmed": None,
                    "article_or_work_level_licence_confirmed": None,
                    "licence_identifier_confirmed": None,
                    "licence_evidence_uri_confirmed": None,
                    "human_annotation_permitted": None,
                    "derived_annotation_storage_permitted": None,
                    "evaluation_use_permitted": None,
                    "redistribution_of_source_bytes_permitted": None,
                    "attribution_complete_and_correct": None,
                    "named_authors_complete_and_correct": None,
                    "third_party_material_inside_candidate_passages": None,
                    "excluded_passage_locators": [],
                    "limitations_and_obligations": [],
                    "disposition": None,
                    "allowed_dispositions": list(DISPOSITIONS),
                    "rationale": None,
                },
                "integrity": {
                    "review_record_sha256": None,
                    "immutable_external_record_uri": None,
                }
            })
        if len(records) != 536:
            raise ValueError(f"corrected PR #66 source corpus is expected to contain 536 sources; got {len(records)}")
        output = args.output.resolve()
        if output.exists():
            raise ValueError(f"refusing to overwrite rights workset: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "research-handoff.t070.source-rights-workset.v1",
            "status": "READY_FOR_INDEPENDENT_SOURCE_RIGHTS_REVIEW",
            "source_manifest_path": str(manifest_path),
            "source_manifest_sha256": sha256_file(manifest_path),
            "source_count": len(records),
            "records": records,
            "release_evidence": False,
            "rule": "Every disposition and reviewer field must be completed by a genuine competent human. Any rejected/excluded source that would reduce the 6000-pair floor requires corpus repair/backfill before annotation."
        }
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(json.dumps({"status": "PREPARATION_FAILED", "reason": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": payload["status"], "source_count": len(records), "output": str(output), "source_manifest_sha256": payload["source_manifest_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
