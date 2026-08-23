#!/usr/bin/env python3
"""Validate a completed Autonomous SWOS run against the canonical acceptance contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from swos_runtime.governance import body_word_count, verify_manifest
from swos_runtime.orchestrator import AutonomousSWOS

CANONICAL_TOPIC = "Can an AI-operated machine be a witness in court?"
REQUIRED_FILES = {
    "article.md",
    "references.json",
    "citation-map.json",
    "evidence-matrix.json",
    "argument-graph.json",
    "provenance.json",
    "decision-ledger.json",
    "review-summary.json",
    "confidence-report.json",
    "research-plan.json",
    "source-register.json",
    "retrieval.json",
    "reranking.json",
    "prose-evidence.json",
    "security-report.json",
    "scholarly-state.json",
    "run-control.json",
    "integrity-chain.jsonl",
    "run-manifest.json",
    "run-manifest.sha256",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--canonical", action="store_true")
    args = parser.parse_args()
    root = args.run_dir
    failures: list[str] = []

    missing = sorted(name for name in REQUIRED_FILES if not (root / name).is_file())
    if missing:
        failures.append(f"missing required files: {', '.join(missing)}")
        print("AUTONOMOUS RUN VALIDATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    manifest = load(root / "run-manifest.json")
    control = load(root / "run-control.json")
    evidence = load(root / "evidence-matrix.json")
    references = load(root / "references.json")
    sources = load(root / "source-register.json")
    article = (root / "article.md").read_text(encoding="utf-8")

    if not verify_manifest(root, manifest):
        failures.append("run manifest hashes do not verify")
    if control.get("status") != "APPROVED" or manifest.get("status") != "APPROVED":
        failures.append(f"run is not APPROVED: {control.get('status')}")
    if control.get("human_interventions") != 0:
        failures.append("human intervention occurred")
    if control.get("normal_user_questions_asked") != 0:
        failures.append("normal user questions were asked mid-run")
    if (
        control.get("cross_encoder", {}).get("method")
        != "openai_joint_query_document_cross_encoder"
    ):
        failures.append("reference cross-encoder did not execute")
    if len(evidence.get("rows", [])) < 5:
        failures.append("fewer than five verified Evidence Matrix rows")
    if not evidence.get("coverage", {}).get("counter_evidence_present"):
        failures.append("no verified counter/limitation evidence")
    if len(references) < 3:
        failures.append("fewer than three verified references used in article")
    if any(
        not item.get("metadata_verified") or not item.get("existence_verified")
        for item in references
    ):
        failures.append("one or more used references are unverified")

    primary_ids = {
        item["source_id"]
        for item in sources
        if item.get("primary") and item.get("metadata_verified")
    }
    evidence_source_ids = {
        citation.get("source_id")
        for row in evidence.get("rows", [])
        for citation in row.get("citations", [])
    }
    if not primary_ids.intersection(evidence_source_ids):
        failures.append("no verified primary legal authority is represented in Evidence Matrix")

    words = body_word_count(article)
    if not 2125 <= words <= 2875:
        failures.append(f"article body has {words} words; canonical range is 2125-2875")

    if args.canonical:
        request = manifest.get("request", {})
        if request.get("topic") != CANONICAL_TOPIC:
            failures.append("manifest topic does not match canonical legal-AI acceptance topic")
        if request.get("length") != 2500:
            failures.append("canonical target length is not 2500")
        if request.get("audience") != "intelligent general reader":
            failures.append("canonical audience mismatch")
        if request.get("style") != "scholarly-natural":
            failures.append("canonical style mismatch")
        if request.get("depth") != "rigorous":
            failures.append("canonical depth mismatch")

    schema_errors = AutonomousSWOS._validate_schemas(root)
    if schema_errors:
        failures.extend(f"schema: {error}" for error in schema_errors)

    if failures:
        print("AUTONOMOUS RUN VALIDATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("AUTONOMOUS RUN VALIDATION: PASS")
    print(
        f"status=APPROVED body_words={words} references={len(references)} evidence_rows={len(evidence.get('rows', []))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
