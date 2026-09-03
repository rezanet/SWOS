#!/usr/bin/env python3
"""Prepare two blind T070 human-annotation worksets plus adjudication bindings.

This tool is intentionally unable to label a pair. It refuses duplicate semantic
spans, pre-populated annotation/adjudication fields, duplicate IDs, and malformed
source digests. Acquisition strata, pattern IDs and semantic-partition intent are
excluded from annotator-facing worksets so retrieval/generator intent does not
bias the two independent annotations.

Run only after the PR #66 packet-integrity P1 findings are repaired and the exact
source rights review has admitted the corresponding source copies for annotation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

ALLOWED_LABELS = (
    "directly_supports",
    "partially_supports",
    "context_only",
    "contradicts",
    "not_supported",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_no}: JSON object required")
            yield line_no, value


def blank_human_fields(row: dict[str, Any], line_no: int) -> None:
    annotations = row.get("annotations")
    if not isinstance(annotations, list) or len(annotations) != 2:
        raise ValueError(f"line {line_no}: exactly two annotation slots are required")
    for index, item in enumerate(annotations):
        if not isinstance(item, dict):
            raise ValueError(f"line {line_no}: annotation {index + 1} is not an object")
        if any(item.get(key) not in (None, "") for key in ("annotator_id", "label", "rationale")):
            raise ValueError(f"line {line_no}: annotation {index + 1} is already populated")
    adjudication = row.get("adjudication")
    if not isinstance(adjudication, dict) or adjudication.get("status") != "pending":
        raise ValueError(f"line {line_no}: adjudication must be pending")
    if any(adjudication.get(key) not in (None, "") for key in ("adjudicator_id", "label", "rationale")):
        raise ValueError(f"line {line_no}: adjudication is already populated")


def nonempty(row: dict[str, Any], field: str, line_no: int) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"line {line_no}: missing {field}")
    return value.strip()


def prepare_row(row: dict[str, Any], line_no: int) -> tuple[str, tuple[str, str, str], dict[str, Any]]:
    if row.get("schema_version") != "2.0.0" or row.get("packet_type") != "citation_support_unlabelled_annotation":
        raise ValueError(f"line {line_no}: unsupported T070 packet schema/type")
    if any(key in row for key in ("label", "relation", "retrieval_intent")):
        raise ValueError(f"line {line_no}: unlabelled packet exposes a forbidden truth/intent field")
    blank_human_fields(row, line_no)
    pair_id = nonempty(row, "pair_id", line_no)
    packet_id = nonempty(row, "packet_id", line_no)
    source_id = nonempty(row, "source_id", line_no)
    source_digest = nonempty(row, "source_digest", line_no).lower()
    if len(source_digest) != 64 or any(ch not in "0123456789abcdef" for ch in source_digest):
        raise ValueError(f"line {line_no}: source_digest is not lowercase SHA-256")
    claim_family_id = nonempty(row, "claim_family_id", line_no)
    claim = nonempty(row, "candidate_claim", line_no)
    quote = nonempty(row, "exact_quote", line_no)
    context = nonempty(row, "context", line_no)
    packet_digest = sha256_json(row)
    blind = {
        "schema_version": "research-handoff.t070.blind-annotation-item.v1",
        "pair_binding": {
            "pair_id": pair_id,
            "packet_id": packet_id,
            "packet_sha256": packet_digest,
            "source_id": source_id,
            "source_sha256": source_digest,
            "claim_family_id": claim_family_id,
            "discipline": row.get("discipline"),
            "candidate_claim": claim,
            "exact_quote": quote,
            "context": context,
            "source_uri": row.get("source_uri"),
            "acquired_copy_uri": row.get("acquired_copy_uri"),
            "licence": row.get("licence"),
            "attribution": row.get("attribution"),
        },
        "source_rights_review_binding": {
            "review_record_id": None,
            "review_record_sha256": None,
            "status_required": "approved_for_candidate_annotation"
        },
        "annotation": {
            "annotator_id": None,
            "annotator_role": None,
            "competence_basis": None,
            "independence_attestation": None,
            "conflict_declaration": None,
            "reviewed_at": None,
            "label": None,
            "allowed_labels": list(ALLOWED_LABELS),
            "rationale": None,
            "quote_support_locator": None,
            "ambiguity_or_limitations": [],
            "disposition": None,
        },
        "integrity": {
            "record_sha256": None,
            "signed_or_immutable_external_record_uri": None
        },
        "blindness": {
            "acquisition_stratum_hidden": True,
            "candidate_pattern_hidden": True,
            "semantic_partition_hidden": True,
            "other_annotator_decision_hidden": True,
            "machine_prediction_hidden": True
        }
    }
    semantic_key = (source_id, claim_family_id, quote)
    return pair_id, semantic_key, blind


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        pair_ids: set[str] = set()
        semantic_keys: set[tuple[str, str, str]] = set()
        blind_rows: list[dict[str, Any]] = []
        adjudication_rows: list[dict[str, Any]] = []
        for line_no, row in read_jsonl(args.pairs):
            pair_id, semantic_key, blind = prepare_row(row, line_no)
            if pair_id in pair_ids:
                raise ValueError(f"line {line_no}: duplicate pair_id {pair_id}")
            if semantic_key in semantic_keys:
                raise ValueError(
                    f"line {line_no}: duplicate semantic span {semantic_key[0]}/{semantic_key[1]}; repair and backfill before human review"
                )
            pair_ids.add(pair_id)
            semantic_keys.add(semantic_key)
            blind_rows.append(blind)
            binding = blind["pair_binding"]
            adjudication_rows.append({
                "schema_version": "research-handoff.t070.adjudication-binding.v1",
                "pair_binding": {
                    "pair_id": pair_id,
                    "packet_sha256": binding["packet_sha256"],
                    "source_sha256": binding["source_sha256"],
                    "claim_family_id": binding["claim_family_id"],
                },
                "annotation_bindings": [
                    {"slot": "A", "annotation_record_id": None, "annotation_record_sha256": None, "annotator_id": None},
                    {"slot": "B", "annotation_record_id": None, "annotation_record_sha256": None, "annotator_id": None},
                ],
                "adjudication": {
                    "adjudicator_id": None,
                    "competence_basis": None,
                    "independence_attestation": None,
                    "reviewed_at": None,
                    "final_label": None,
                    "allowed_labels": list(ALLOWED_LABELS),
                    "rationale": None,
                    "disposition": None
                }
            })
        if not blind_rows:
            raise ValueError("no candidate pairs found")
        out = args.output_dir.resolve()
        if out.exists() and any(out.iterdir()):
            raise ValueError(f"refusing to overwrite non-empty workset directory: {out}")
        out.mkdir(parents=True, exist_ok=True)
        # A and B are byte-identical candidate order/content by design. They are
        # distributed separately and completed independently by different humans.
        write_jsonl(out / "annotator-A.jsonl", blind_rows)
        write_jsonl(out / "annotator-B.jsonl", blind_rows)
        write_jsonl(out / "adjudication-bindings.jsonl", adjudication_rows)
        manifest = {
            "schema_version": "research-handoff.t070.blind-workset-manifest.v1",
            "status": "READY_FOR_RIGHTS_BINDING_THEN_HUMAN_ANNOTATION",
            "source_pairs_path": str(args.pairs.resolve()),
            "source_pairs_sha256": sha256_file(args.pairs),
            "pair_count": len(blind_rows),
            "unique_pair_ids": len(pair_ids),
            "unique_source_claim_quote_tuples": len(semantic_keys),
            "required_human_annotations_per_pair": 2,
            "required_independent_adjudications_per_pair": 1,
            "worksets": {
                "A": {"path": "annotator-A.jsonl", "sha256": sha256_file(out / "annotator-A.jsonl")},
                "B": {"path": "annotator-B.jsonl", "sha256": sha256_file(out / "annotator-B.jsonl")},
                "adjudication": {"path": "adjudication-bindings.jsonl", "sha256": sha256_file(out / "adjudication-bindings.jsonl")}
            },
            "release_evidence": False,
            "preconditions": [
                "PR #66 integrity/author-attribution/duplicate-span P1s repaired on the exact packet head",
                "exact source copies receive genuine rights review before annotation",
                "annotator A and B are genuine independent competent humans",
                "adjudicator is a genuine competent human independent of both annotators"
            ]
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "PREPARATION_REFUSED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": manifest["status"], "pair_count": manifest["pair_count"], "output_dir": str(out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
