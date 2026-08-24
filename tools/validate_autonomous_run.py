#!/usr/bin/env python3
"""Validate a completed Autonomous SWOS run against its request and governance contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from swos_runtime.governance import body_word_count, cross_encoder_executed, verify_manifest
from swos_runtime.schema_validation import validate_frozen_run_schemas

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


def is_legal_topic(topic: str) -> bool:
    lowered = topic.lower()
    return any(term in lowered for term in ("court", "witness", "legal", " law ", "evidence act"))


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
    request = manifest.get("request", {})

    if not verify_manifest(root, manifest):
        failures.append("run manifest hashes do not verify")
    if control.get("status") != "APPROVED" or manifest.get("status") != "APPROVED":
        failures.append(f"run is not APPROVED: {control.get('status')}")
    if control.get("human_interventions") != 0:
        failures.append("human intervention occurred")
    if control.get("normal_user_questions_asked") != 0:
        failures.append("normal user questions were asked mid-run")
    if not cross_encoder_executed(control.get("cross_encoder", {})):
        failures.append("governed semantic rerank did not execute")
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

    topic = str(request.get("topic") or "")
    if args.canonical or is_legal_topic(topic):
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
    target = int(request.get("length") or 2500)
    minimum = int(target * 0.85)
    maximum = int(target * 1.15)
    if not minimum <= words <= maximum:
        failures.append(
            f"article body has {words} words; request-derived range is {minimum}-{maximum}"
        )

    if args.canonical:
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

    schema_errors = validate_frozen_run_schemas(root)
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
