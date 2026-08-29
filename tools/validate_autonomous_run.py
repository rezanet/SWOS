#!/usr/bin/env python3
"""Validate a completed Autonomous SWOS run against the full governed outcome contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from swos_runtime.governance import (
    IntegrityChain,
    body_word_count,
    cross_encoder_executed,
    verify_manifest,
)
from swos_runtime.schema_validation import validate_frozen_run_schemas

CANONICAL_TOPIC = "Can an AI-operated machine be a witness in court?"
CANONICAL_REQUEST = {
    "topic": CANONICAL_TOPIC,
    "length": 2500,
    "audience": "intelligent general reader",
    "style": "scholarly-natural",
    "depth": "rigorous",
}
REQUIRED_FILES = {
    "article.md",
    "references.json",
    "citation-map.json",
    "evidence-matrix.json",
    "argument-graph.json",
    "provenance.json",
    "decision-ledger.json",
    "review-summary.json",
    "review-assurance.json",
    "judgement-evidence.json",
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
REQUIRED_STAGE_ACTIVITIES = {
    "research_planning",
    "source_retrieval",
    "semantic_rerank",
    "evidence_extraction",
    "citation_support_audit",
    "argument_construction",
    "draft_generation",
    "prose_transformation",
    "semantic_verification",
    "hostile_review",
}
REQUIRED_STATE_SEQUENCE = [
    "initiated",
    "planned",
    "evidence_gathering",
    "evidence_verified",
    "argument_constructed",
    "draft_generated",
    "reviewed",
]


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_legal_topic(topic: str) -> bool:
    lowered = topic.lower()
    return any(term in lowered for term in ("court", "witness", "legal", " law ", "evidence act"))


def _ordered_subsequence(required: list[str], observed: list[str]) -> bool:
    position = 0
    for value in observed:
        if position < len(required) and value == required[position]:
            position += 1
    return position == len(required)


def _integrity_chain_valid(path: Path) -> tuple[bool, str | None]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    if not entries:
        return False, None
    chain = IntegrityChain()
    chain.entries = entries
    return chain.verify(), str(entries[-1].get("hash") or "") or None


def validate_run(root: Path, *, canonical: bool = False) -> list[str]:
    """Return all governed acceptance failures for a run directory."""

    failures: list[str] = []
    missing = sorted(name for name in REQUIRED_FILES if not (root / name).is_file())
    if missing:
        return [f"missing required files: {', '.join(missing)}"]

    manifest = load(root / "run-manifest.json")
    control = load(root / "run-control.json")
    evidence = load(root / "evidence-matrix.json")
    argument = load(root / "argument-graph.json")
    references = load(root / "references.json")
    sources = load(root / "source-register.json")
    reviews = load(root / "review-summary.json")
    review_assurance = load(root / "review-assurance.json")
    judgements = load(root / "judgement-evidence.json")
    scholarly_state = load(root / "scholarly-state.json")
    provenance = load(root / "provenance.json")
    prose = load(root / "prose-evidence.json")
    article = (root / "article.md").read_text(encoding="utf-8")
    request = manifest.get("request", {})

    if not verify_manifest(root, manifest):
        failures.append("run manifest hashes do not verify")
    if control.get("status") != "APPROVED" or manifest.get("status") != "APPROVED":
        failures.append(f"run is not APPROVED: {control.get('status')}")
    if control.get("blocking_reasons"):
        failures.append("run-control still contains blocking reasons at release")
    if control.get("human_interventions") != 0:
        failures.append("human intervention occurred")
    if control.get("normal_user_questions_asked") != 0:
        failures.append("normal user questions were asked mid-run")
    if not cross_encoder_executed(control.get("cross_encoder", {})):
        failures.append("governed semantic rerank did not execute")

    rows = evidence.get("rows", [])
    if len(rows) < 5:
        failures.append("fewer than five verified Evidence Matrix rows")
    if not evidence.get("coverage", {}).get("counter_evidence_present"):
        failures.append("no verified counter/limitation evidence")
    for index, row in enumerate(rows):
        if row.get("verification_status") != "pass":
            failures.append(f"Evidence Matrix row {index} is not verification_status=pass")
        citations = row.get("citations", [])
        if not citations:
            failures.append(f"Evidence Matrix row {index} has no citations")
        for citation in citations:
            if citation.get("support_level") != "directly_supports":
                failures.append(f"Evidence Matrix row {index} contains non-direct support")
            if citation.get("metadata_verified") is not True:
                failures.append(f"Evidence Matrix row {index} citation metadata is unverified")
            span = citation.get("evidence_span", {})
            if not str(span.get("quoted_text") or "").strip():
                failures.append(f"Evidence Matrix row {index} citation has no verified quote span")

    nodes = argument.get("nodes", [])
    if not str(argument.get("thesis", {}).get("statement") or "").strip():
        failures.append("Argument Graph has no thesis statement")
    if not nodes:
        failures.append("Argument Graph has no nodes")
    node_ids = {node.get("node_id") for node in nodes if isinstance(node, dict)}
    if not any(node.get("evidence_claim_ids") for node in nodes if isinstance(node, dict)):
        failures.append("Argument Graph has no evidence-linked node")
    for edge in argument.get("edges", []):
        if edge.get("from_node") not in node_ids or edge.get("to_node") not in node_ids:
            failures.append("Argument Graph contains an edge to an unknown node")

    if len(references) < 3:
        failures.append("fewer than three verified references used in article")
    if any(
        not item.get("metadata_verified") or not item.get("existence_verified")
        for item in references
    ):
        failures.append("one or more used references are unverified")

    topic = str(request.get("topic") or "")
    if canonical or is_legal_topic(topic):
        primary_ids = {
            item["source_id"]
            for item in sources
            if item.get("primary") and item.get("metadata_verified")
        }
        evidence_source_ids = {
            citation.get("source_id") for row in rows for citation in row.get("citations", [])
        }
        if not primary_ids.intersection(evidence_source_ids):
            failures.append("no verified primary legal authority is represented in Evidence Matrix")

    if not isinstance(reviews, list) or not reviews:
        failures.append("governed review did not complete")
    else:
        for review in reviews:
            if review.get("verdict") in {"fail", "escalate"}:
                failures.append(f"review {review.get('reviewer_role')} did not pass")
            for finding in review.get("findings", []):
                if (
                    finding.get("severity") in {"blocker", "major"}
                    and finding.get("status") != "resolved"
                ):
                    failures.append("open blocker/major reviewer finding remains at release")

    if review_assurance.get("meets_automatic_delivery_requirement") is not True:
        failures.append("review assurance does not meet automatic-delivery requirement")
    if review_assurance.get("independence") in {None, "unknown", "none", "unsupported"}:
        failures.append("review independence is missing or unsupported")

    records = judgements.get("records", []) if isinstance(judgements, dict) else []
    if not records:
        failures.append("model judgement evidence is missing")
    for record in records:
        if record.get("authority") != "advisory_evidence_for_swos_governance":
            failures.append("a model judgement claims authority beyond advisory evidence")

    states = [
        str(item.get("state"))
        for item in scholarly_state.get("history", [])
        if isinstance(item, dict)
    ]
    if not _ordered_subsequence(REQUIRED_STATE_SEQUENCE, states):
        failures.append("Scholarly State history does not contain the required ordered transitions")
    if scholarly_state.get("current_state") != "approved" or not states or states[-1] != "approved":
        failures.append("Scholarly State did not terminate in approved")

    activities = provenance.get("activities", [])
    activity_capabilities = {
        str(item.get("parameters", {}).get("capability"))
        for item in activities
        if isinstance(item, dict)
    }
    missing_activities = sorted(REQUIRED_STAGE_ACTIVITIES - activity_capabilities)
    if missing_activities:
        failures.append("provenance is missing stage activities: " + ", ".join(missing_activities))
    agent_kinds = {
        str(item.get("agent_kind"))
        for item in provenance.get("agents", [])
        if isinstance(item, dict)
    }
    if not {"orchestrator", "host_runtime", "model"}.issubset(agent_kinds):
        failures.append("provenance does not identify orchestrator, host runtime and model agents")

    execution = control.get("execution", {})
    host_label = str(execution.get("model_host") or "")
    host_agents = [
        item
        for item in provenance.get("agents", [])
        if isinstance(item, dict) and item.get("agent_kind") == "host_runtime"
    ]
    if host_label and not any(str(item.get("label") or "") == host_label for item in host_agents):
        failures.append("run-control host provenance does not match the provenance graph")

    chain_ok, _ = _integrity_chain_valid(root / "integrity-chain.jsonl")
    if not chain_ok:
        failures.append("integrity chain does not verify")

    if (
        prose.get("safe_for_automatic_use") is not True
        and prose.get("used_source_fallback") is not True
    ):
        failures.append("unsafe prose transformation reached release without source fallback")

    words = body_word_count(article)
    target = int(request.get("length") or 2500)
    minimum = int(target * 0.85)
    maximum = int(target * 1.15)
    if not minimum <= words <= maximum:
        failures.append(
            f"article body has {words} words; request-derived range is {minimum}-{maximum}"
        )

    if canonical:
        for key, expected in CANONICAL_REQUEST.items():
            if request.get(key) != expected:
                failures.append(f"canonical {key} mismatch")

    schema_errors = validate_frozen_run_schemas(root)
    if schema_errors:
        failures.extend(f"schema: {error}" for error in schema_errors)

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--canonical", action="store_true")
    args = parser.parse_args()
    failures = validate_run(args.run_dir, canonical=args.canonical)

    if failures:
        print("AUTONOMOUS RUN VALIDATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    root = args.run_dir
    evidence = load(root / "evidence-matrix.json")
    references = load(root / "references.json")
    article = (root / "article.md").read_text(encoding="utf-8")
    print("AUTONOMOUS RUN VALIDATION: PASS")
    print(
        "status=APPROVED "
        f"body_words={body_word_count(article)} "
        f"references={len(references)} evidence_rows={len(evidence.get('rows', []))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
