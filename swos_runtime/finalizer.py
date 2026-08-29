"""Provider-neutral SWOS final governance and audit assembly.

Models and hosts may propose scholarly judgements. SWOS owns release authority.
This module consumes accepted work-order evidence, repeats deterministic checks,
records judgement provenance/limitations, validates frozen schemas and emits the
canonical audit package without calling a model provider.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .capabilities import CAPABILITY_CONTRACTS
from .governance import (
    IntegrityChain,
    body_word_count,
    canonical_sha256,
    citation_markers,
    detect_prompt_injection,
    exact_quote_supported,
    verify_manifest,
)
from .models import RunOutcome, SourceRecord, swos_id
from .schema_validation import validate_frozen_run_schemas
from .work_orders import WorkOrderError, WorkOrderRun

RUNTIME_VERSION = "0.2.0"
ID_RE = re.compile(r"^[a-z]{2,6}-[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
VALID_NODE_TYPES = {
    "claim",
    "grounds",
    "warrant",
    "backing",
    "qualifier",
    "objection",
    "rebuttal",
    "implication",
    "rival_reading",
}
VALID_EDGE_RELATIONS = {
    "supports",
    "warrants",
    "backs",
    "qualifies",
    "objects_to",
    "rebuts",
    "implies",
    "rivals",
    "depends_on",
}
VALID_REVIEW_ROLES = {
    "citation_auditor",
    "methodologist",
    "argument_examiner",
    "discipline_expert",
    "hostile_reviewer",
    "editor",
    "governance_reviewer",
}
VALID_FINDING_CATEGORIES = {
    "fabricated_citation",
    "citation_metadata_error",
    "citation_laundering",
    "unsupported_claim",
    "overclaim",
    "missing_counter_evidence",
    "coverage_gap",
    "source_bias",
    "hidden_premise",
    "invalid_inference",
    "circular_reasoning",
    "over_association",
    "method_weakness",
    "construct_validity",
    "statistical_overreach",
    "interpretive_flattening",
    "false_originality",
    "genre_mismatch",
    "structure",
    "clarity",
    "policy_breach",
    "missing_audit_trail",
    "data_classification_error",
}
ACCEPTABLE_AUTOMATIC_REVIEW_INDEPENDENCE = {
    "limited",
    "limited_same_host",
    "limited_same_provider",
    "independent",
    "verified_independent",
}
ACTIVITY_BY_STAGE = {
    "research_planning": "classification",
    "source_retrieval": "retrieval",
    "semantic_rerank": "classification",
    "evidence_extraction": "extraction",
    "citation_support_audit": "citation_check",
    "argument_construction": "argument_construction",
    "draft_generation": "drafting",
    "prose_transformation": "normalisation",
    "semantic_verification": "evaluation",
    "hostile_review": "review",
    "revision": "revision",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _actor() -> dict[str, str]:
    return {
        "actor_type": "orchestrator",
        "actor_id": "swos-final-governance",
        "display_name": "SWOS final governance",
        "version": RUNTIME_VERSION,
    }


def _legal_topic(topic: str) -> bool:
    lowered = topic.lower()
    return any(term in lowered for term in ("court", "witness", "legal", " law ", "evidence act"))


def _enforce_requested_title(article: str, topic: str) -> str:
    match = re.search(r"\btitled\s+['\"]([^'\"]+)['\"]", topic, flags=re.IGNORECASE)
    if not match:
        return article
    requested = match.group(1).strip()
    if not requested:
        return article
    if re.search(r"(?m)^#\s+.+$", article):
        return re.sub(r"(?m)^#\s+.+$", f"# {requested}", article, count=1)
    return f"# {requested}\n\n{article.lstrip()}"


def _source_labels(sources: list[SourceRecord]) -> dict[str, str]:
    return {source.source_id: f"S{index}" for index, source in enumerate(sources, start=1)}


def _append_references(article: str, sources: list[SourceRecord], labels: dict[str, str]) -> str:
    article = re.split(r"(?im)^\s*##\s+References\s*$", article)[0].strip()
    used = set(citation_markers(article))
    lines = ["## References"]
    for source in sources:
        marker = labels[source.source_id]
        if marker not in used:
            continue
        author = f"{source.author}. " if source.author else ""
        date = f" ({source.published_date})" if source.published_date else ""
        lines.append(f"- [{marker}] {author}{source.title}{date}. {source.url}")
    return article + "\n\n" + "\n".join(lines) + "\n"


def _citation_map(article: str, labels: dict[str, str]) -> dict[str, Any]:
    reverse = {marker: source_id for source_id, marker in labels.items()}
    occurrences: dict[str, list[str]] = {marker: [] for marker in reverse}
    for paragraph in [part.strip() for part in article.split("\n\n") if part.strip()]:
        for marker in set(citation_markers(paragraph)):
            if marker in occurrences:
                occurrences[marker].append(paragraph[:700])
    return {
        "markers": [
            {"marker": marker, "source_id": reverse[marker], "occurrences": snippets}
            for marker, snippets in occurrences.items()
            if snippets
        ]
    }


def _review_assurance(adapter: dict[str, Any], capability: str) -> dict[str, Any]:
    declaration = adapter.get("capabilities", {}).get(capability, {})
    if not isinstance(declaration, dict):
        declaration = {}
    return {
        "capability": capability,
        "contract": CAPABILITY_CONTRACTS[capability],
        "review_mode": str(declaration.get("review_mode") or "unspecified"),
        "independence": str(declaration.get("independence") or "unknown"),
        "blind_review_supported": bool(declaration.get("blind_review_supported", False)),
        "independence_limitations": list(declaration.get("independence_limitations") or []),
        "assurance": list(declaration.get("assurance") or []),
    }


def _canonical_sources(
    run: WorkOrderRun,
) -> tuple[list[SourceRecord], dict[str, str], list[str]]:
    retrieval = run._latest("source_retrieval") or {}
    raw_sources = retrieval.get("sources", [])
    sources: list[SourceRecord] = []
    id_map: dict[str, str] = {}
    blockers: list[str] = []
    for index, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            blockers.append(f"retrieved source {index} is not an object")
            continue
        raw_id = str(raw.get("source_id") or f"source-{index}")
        if raw_id in id_map:
            blockers.append(f"duplicate source id: {raw_id}")
            continue
        canonical_id = raw_id if ID_RE.fullmatch(raw_id) else swos_id("src")
        id_map[raw_id] = canonical_id
        text = str(raw.get("text") or "")
        source = SourceRecord(
            source_id=canonical_id,
            title=str(raw.get("title") or f"Untitled source {index}"),
            url=str(raw.get("url") or ""),
            source_type=str(raw.get("source_type") or "scholarly"),
            provider=str(raw.get("provider") or "retrieval-binding"),
            text=text,
            jurisdiction=raw.get("jurisdiction"),
            author=raw.get("author"),
            published_date=raw.get("published_date"),
            identifiers=dict(raw.get("identifiers") or {}),
            metadata_verified=bool(raw.get("metadata_verified", False)),
            primary=bool(raw.get("primary", False)),
            retrieval_query=str(raw.get("retrieval_query") or ""),
            raw_rank=index,
            injection_detected=detect_prompt_injection(text),
        )
        if not source.url:
            blockers.append(f"source {raw_id} has no URL")
        if not source.metadata_verified:
            blockers.append(f"source {raw_id} metadata is not verified")
        if not source.text.strip():
            blockers.append(f"source {raw_id} has no retrievable text")
        sources.append(source)
    return sources, id_map, blockers


def _evidence_matrix(
    *,
    work_id: str,
    run: WorkOrderRun,
    sources: list[SourceRecord],
    source_id_map: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    extraction = run._latest("evidence_extraction") or {}
    audit = run._latest("citation_support_audit") or {}
    candidates = extraction.get("claims", [])
    audits = audit.get("audits", [])
    audit_by_index = {
        int(item["index"]): item
        for item in audits
        if isinstance(item, dict) and isinstance(item.get("index"), int)
    }
    source_map = {source.source_id: source for source in sources}
    rows: list[dict[str, Any]] = []
    internal: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    blockers: list[str] = []

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            rejected.append({"index": index, "reason": "candidate is not an object"})
            continue
        raw_source_id = str(candidate.get("source_id") or "")
        source_id = source_id_map.get(raw_source_id)
        source = source_map.get(source_id or "")
        quote = str(candidate.get("exact_quote") or "")
        audit_item = audit_by_index.get(index, {})
        support = str(audit_item.get("support_level") or "invalid_citation")
        reason = str(audit_item.get("reason") or "")
        if source is None:
            rejected.append({"index": index, "candidate": candidate, "reason": "source missing"})
            continue
        if not source.metadata_verified:
            rejected.append(
                {"index": index, "candidate": candidate, "reason": "metadata unverified"}
            )
            continue
        if not exact_quote_supported(quote, source):
            rejected.append(
                {"index": index, "candidate": candidate, "reason": "exact quote not found"}
            )
            continue
        if support != "directly_supports":
            rejected.append(
                {
                    "index": index,
                    "candidate": candidate,
                    "reason": f"citation support judgement returned {support}",
                    "audit": audit_item,
                }
            )
            continue

        claim_text = str(candidate.get("claim") or "").strip()
        if not claim_text:
            rejected.append({"index": index, "candidate": candidate, "reason": "empty claim"})
            continue
        claim_id = swos_id("clm")
        stance = str(candidate.get("stance") or "support")
        epistemic_type = str(candidate.get("epistemic_type") or "source_backed_claim")
        if epistemic_type not in {
            "observed_fact",
            "source_backed_claim",
            "inference",
            "interpretation",
            "hypothesis",
            "speculation",
            "critical_assessment",
            "normative_judgement",
            "unverified_claim",
        }:
            epistemic_type = "source_backed_claim"
        confidence = str(candidate.get("confidence") or "medium")
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"
        citation = {
            "source_id": source.source_id,
            "support_level": "directly_supports",
            "evidence_span": {
                "locator": str(candidate.get("locator") or "retrieved passage"),
                "quoted_text": quote[:500],
                "span_type": "passage",
            },
            "support_rationale": str(candidate.get("rationale") or reason),
            "verified_by": {
                "actor_type": "orchestrator",
                "actor_id": "swos-deterministic-evidence-gate",
                "display_name": "SWOS deterministic evidence gate",
                "version": RUNTIME_VERSION,
            },
            "metadata_verified": True,
            "retraction_checked": bool(candidate.get("retraction_checked", False)),
            "licence_cleared": bool(candidate.get("licence_cleared", False)),
        }
        row = {
            "claim_id": claim_id,
            "claim_text": claim_text,
            "epistemic_type": epistemic_type,
            "confidence": confidence,
            "citation_burden": "primary_source_required" if source.primary else "single_source",
            "citations": [citation],
            "counter_evidence": [],
            "uncertainty": [],
            "verification_status": "pass",
            "discipline": "interdisciplinary",
            "argument_node_ids": [],
            "epg_node_id": claim_id,
            "state": "evidence_verified",
        }
        rows.append(row)
        internal.append(
            {
                "candidate_index": index,
                "claim_id": claim_id,
                "source_id": source.source_id,
                "stance": stance,
                "claim": claim_text,
            }
        )

    counter_present = any(item["stance"] in {"counter", "limitation"} for item in internal)
    providers = {source.provider for source in sources if source.metadata_verified}
    matrix = {
        "schema_version": "1.0.0",
        "work_id": work_id,
        "coverage": {
            "total_claims": len(candidates),
            "supported_claims": len(rows),
            "unsupported_claims": len(candidates) - len(rows),
            "uncertain_claims": 0,
            "counter_evidence_present": counter_present,
            "source_diversity_index": round(min(1.0, len(providers) / 3), 3),
        },
        "rows": rows,
    }
    if len(rows) < 5:
        blockers.append("Fewer than five verified evidence claims survived the evidence gate.")
    if not counter_present:
        blockers.append("No verified limitation or counter-evidence survived the evidence gate.")
    return matrix, internal, rejected, blockers


def _argument_graph(
    *, work_id: str, run: WorkOrderRun, evidence_internal: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    raw = run._latest("argument_construction") or {}
    index_to_claim = {item["candidate_index"]: item["claim_id"] for item in evidence_internal}
    local_to_id: dict[str, str] = {}
    nodes: list[dict[str, Any]] = []
    blockers: list[str] = []
    for index, raw_node in enumerate(raw.get("nodes", [])):
        if not isinstance(raw_node, dict):
            continue
        local = str(raw_node.get("local_id") or f"node-{index}")
        node_id = swos_id("arg")
        local_to_id[local] = node_id
        node_type = str(raw_node.get("node_type") or "claim")
        if node_type not in VALID_NODE_TYPES:
            node_type = "claim"
        evidence_refs = [
            index_to_claim[value]
            for value in raw_node.get("evidence_indices", [])
            if isinstance(value, int) and value in index_to_claim
        ]
        statement = str(raw_node.get("statement") or "").strip()
        if not statement:
            continue
        nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "statement": statement,
                "evidence_claim_ids": evidence_refs,
                "strength": "high" if evidence_refs else "medium",
                "hidden_premise": False,
                "status": "accepted",
            }
        )
    edges = []
    for raw_edge in raw.get("edges", []):
        if not isinstance(raw_edge, dict):
            continue
        source = local_to_id.get(str(raw_edge.get("from_local_id") or ""))
        target = local_to_id.get(str(raw_edge.get("to_local_id") or ""))
        relation = str(raw_edge.get("relation") or "depends_on")
        if source and target and relation in VALID_EDGE_RELATIONS:
            edges.append(
                {
                    "from_node": source,
                    "to_node": target,
                    "relation": relation,
                    "relation_confidence": "medium",
                }
            )
    if not nodes:
        blockers.append("Argument Graph contains no nodes.")
        thesis_id = swos_id("arg")
    else:
        thesis_id = next(
            (node["node_id"] for node in nodes if node["node_type"] == "claim"),
            nodes[0]["node_id"],
        )
    plan = run._latest("research_planning") or {}
    graph = {
        "schema_version": "1.0.0",
        "work_id": work_id,
        "thesis": {
            "node_id": thesis_id,
            "statement": str(raw.get("thesis") or ""),
            "contribution_type": "synthesis",
            "rival_theses_considered": list(plan.get("rival_theses") or []),
        },
        "nodes": nodes,
        "edges": edges,
        "unresolved_objections": [],
    }
    return graph, blockers


def _review_documents(
    run: WorkOrderRun, work_id: str, assurance: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    documents: list[dict[str, Any]] = []
    blockers: list[str] = []
    submissions = run._all("hostile_review")
    for iteration, submission in enumerate(submissions, start=1):
        reviews = submission.get("reviews", []) if isinstance(submission, dict) else []
        for raw_review in reviews:
            if not isinstance(raw_review, dict):
                continue
            findings = []
            for raw_finding in raw_review.get("findings", []):
                if not isinstance(raw_finding, dict):
                    continue
                severity = str(raw_finding.get("severity") or "advisory")
                if severity not in {"blocker", "major", "minor", "advisory"}:
                    severity = "advisory"
                category = str(raw_finding.get("category") or "policy_breach")
                if category not in VALID_FINDING_CATEGORIES:
                    category = "policy_breach"
                latest = iteration == len(submissions)
                status = "open" if latest and severity in {"blocker", "major"} else "resolved"
                if status == "open":
                    blockers.append(str(raw_finding.get("description") or category))
                findings.append(
                    {
                        "finding_id": swos_id("rev"),
                        "severity": severity,
                        "category": category,
                        "description": str(raw_finding.get("description") or category),
                        "locus": str(raw_finding.get("locus") or "article"),
                        "required_action": str(raw_finding.get("required_action") or "review"),
                        "status": status,
                    }
                )
            role = str(raw_review.get("role") or "hostile_reviewer")
            if role not in VALID_REVIEW_ROLES:
                role = "hostile_reviewer"
            verdict = str(raw_review.get("verdict") or "")
            if verdict not in {"pass", "pass_with_findings", "fail", "escalate"}:
                verdict = (
                    "fail"
                    if any(item["severity"] in {"blocker", "major"} for item in findings)
                    else ("pass_with_findings" if findings else "pass")
                )
            documents.append(
                {
                    "schema_version": "1.0.0",
                    "work_id": work_id,
                    "reviewer_role": role,
                    "discipline": "interdisciplinary",
                    "iteration": min(iteration, 3),
                    "verdict": verdict,
                    "blind_review": bool(assurance["blind_review_supported"]),
                    "findings": findings,
                }
            )
    if not documents:
        blockers.append("No governed reviewer result was submitted.")
    return documents, blockers


def _build_epg(
    *,
    work_id: str,
    status: str,
    run: WorkOrderRun,
    sources: list[SourceRecord],
    evidence_matrix: dict[str, Any],
    argument_graph: dict[str, Any],
) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for source in sources:
        entities.append(
            {
                "entity_id": source.source_id,
                "entity_type": "source_work",
                "label": source.title,
                "identifiers": {**source.identifiers, "url": source.url},
                "rights": {
                    "licence": "source-controlled",
                    "access_status": "unknown",
                    "redistribution_allowed": False,
                    "excerpt_limit_chars": 500,
                },
                "retraction_status": "not_checked",
                "data_classification": "public",
            }
        )
    for row in evidence_matrix.get("rows", []):
        entities.append(
            {
                "entity_id": row["claim_id"],
                "entity_type": "claim",
                "label": row["claim_text"],
                "data_classification": "public",
            }
        )
        for citation in row.get("citations", []):
            relations.append(
                {
                    "relation_type": "supportsClaim",
                    "subject": citation["source_id"],
                    "object": row["claim_id"],
                    "at_time": _now(),
                }
            )
    for node in argument_graph.get("nodes", []):
        entities.append(
            {
                "entity_id": node["node_id"],
                "entity_type": "argument_node",
                "label": node["statement"],
                "data_classification": "public",
            }
        )
    entities.append(
        {
            "entity_id": swos_id("prov"),
            "entity_type": "output_bundle",
            "label": f"SWOS governed output {status}",
            "data_classification": "public",
        }
    )

    activities = []
    model_names: set[str] = set()
    for item in run.state.get("submissions", []):
        stage = str(item.get("stage") or "")
        activity_type = ACTIVITY_BY_STAGE.get(stage)
        if not activity_type:
            continue
        payload = json.loads((run.run_dir / item["file"]).read_text(encoding="utf-8"))
        provenance = payload.get("provenance") or {}
        model = str(provenance.get("model") or "unreported-model")
        model_names.add(model)
        parameters = {
            "capability": payload.get("capability") or stage,
            "contract": payload.get("contract"),
            "contract_passed": bool(payload.get("contract_passed", False)),
            "instruction_id": provenance.get("instruction_id"),
            "instruction_sha256": provenance.get("instruction_sha256"),
            "adapter": provenance.get("adapter"),
            "model_host": provenance.get("model_host"),
            "model": model,
            "execution_mode": provenance.get("execution_mode"),
        }
        if isinstance(payload.get("judgement_evidence"), dict):
            parameters["judgement_type"] = payload["judgement_evidence"].get("judgement_type")
            parameters["judgement_authority"] = payload["judgement_evidence"].get("authority")
        activities.append(
            {
                "activity_id": swos_id("prov"),
                "activity_type": activity_type,
                "started_at": _now(),
                "ended_at": _now(),
                "parameters": parameters,
                "tool_id": "swos.work-orders.v1",
            }
        )
    adapter = run.state["adapter"]
    agents = [
        {
            "agent_id": swos_id("agt"),
            "agent_kind": "orchestrator",
            "label": "SWOS work-order orchestrator",
            "version": RUNTIME_VERSION,
        },
        {
            "agent_id": swos_id("agt"),
            "agent_kind": "host_runtime",
            "label": str(adapter.get("model_host") or adapter.get("adapter") or "host"),
            "version": str(adapter.get("execution_mode") or "runtime"),
        },
    ]
    agents.extend(
        {
            "agent_id": swos_id("agt"),
            "agent_kind": "model",
            "label": model,
            "version": "runtime-declared",
        }
        for model in sorted(model_names)
    )
    return {
        "schema_version": "1.0.0",
        "work_id": work_id,
        "prov_compatibility": {"prov_model": "W3C PROV-DM", "serialisation": "prov-json"},
        "entities": entities,
        "activities": activities,
        "agents": agents,
        "relations": relations,
    }


def _build_sdl(
    work_id: str, status: str, run: WorkOrderRun, evidence_refs: list[str]
) -> dict[str, Any]:
    plan = run._latest("research_planning") or {}
    scope = str(plan.get("scope") or "governed scope")
    return {
        "schema_version": "1.0.0",
        "work_id": work_id,
        "append_only": True,
        "entries": [
            {
                "decision_id": swos_id("dec"),
                "decision_type": "scope",
                "question": "What scope governs this research run?",
                "options_considered": [
                    {"option": scope},
                    {
                        "option": "Proceed with an unstated scope.",
                        "why_rejected": "Material scope assumptions must be recorded.",
                    },
                ],
                "selected_option": scope,
                "rationale": "SWOS accepted the research-planning stage and records its scope explicitly.",
                "criteria_applied": ["swos.research-planning.v1"],
                "evidence_refs": [],
                "counter_evidence_refs": [],
                "argument_refs": [],
                "confidence": "medium",
                "uncertainty": [],
                "review_status": "passed",
                "responsible_agent": _actor(),
                "timestamp": _now(),
                "lifecycle_status": "evaluated",
                "reversibility": "reversible",
            },
            {
                "decision_id": swos_id("dec"),
                "decision_type": "governance",
                "question": "Does this run satisfy the SWOS automatic-delivery gate?",
                "options_considered": [
                    {"option": "APPROVED"},
                    {"option": "REVIEW_REQUIRED"},
                ],
                "selected_option": status,
                "rationale": (
                    "SWOS—not a model—selected the release state from capability contracts, "
                    "deterministic source/evidence checks, declared review assurance, schema "
                    "conformance, state rules and integrity evidence. Model judgements are advisory evidence."
                ),
                "criteria_applied": [
                    "Host Independence Rule",
                    "swos.capabilities.v1",
                    "swos.stage-instructions.v1",
                    "SWOS automatic-delivery governance gate",
                ],
                "evidence_refs": evidence_refs,
                "counter_evidence_refs": [],
                "argument_refs": [],
                "confidence": "high" if status == "APPROVED" else "medium",
                "uncertainty": [] if status == "APPROVED" else ["missing_evidence"],
                "review_status": "passed" if status == "APPROVED" else "escalated",
                "responsible_agent": _actor(),
                "timestamp": _now(),
                "lifecycle_status": "approved" if status == "APPROVED" else "challenged",
                "reversibility": "reversible",
            },
        ],
    }


def _rpm_snapshot() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "programme_id": "work-00000000-0000-0000-0000-000000000001",
        "title": "Autonomous SWOS",
        "disciplines": ["interdisciplinary"],
        "items": [],
        "contradictions": [],
        "memory_policies": {
            "read": "Read active source-grounded items within project scope only.",
            "write": "Durable writes require EPG support, SDL rationale and human approval.",
            "update": "Never overwrite; correct or supersede with provenance.",
            "expiry": "Every durable item must carry an expiry date.",
            "correction": "Corrections preserve the prior item and add provenance.",
            "deletion": "Deletion follows governance and audit policy.",
            "default_retention_days": 365,
            "requires_human_approval_above": "all_durable_writes",
        },
    }


def _scholarly_state(work_id: str, status: str, run: WorkOrderRun) -> dict[str, Any]:
    actor = _actor()

    def entry(state: str, phase: str, checkpoint: str) -> dict[str, Any]:
        return {
            "state": state,
            "entered_at": _now(),
            "sdlc_phase": phase,
            "governance_checkpoint": checkpoint,
            "epg_state": checkpoint,
            "entered_by": actor,
        }

    history = [
        entry("initiated", "discover", "request-normalised"),
        entry("planned", "design", "research-plan-complete"),
        entry("evidence_gathering", "build", "retrieval-complete"),
        entry("evidence_verified", "validate", "deterministic-evidence-gate-pass"),
        entry("argument_constructed", "build", "argument-graph-complete"),
        entry("draft_generated", "build", "draft-complete"),
        entry("reviewed", "validate", "bounded-review-complete"),
    ]
    if run.state.get("revision_count", 0):
        history.append(entry("revised", "validate", "bounded-revision-complete"))
    if status == "APPROVED":
        history.append(entry("approved", "release", "automatic-delivery-governance-pass"))
    return {
        "schema_version": "1.0.0",
        "work_id": work_id,
        "current_state": "approved" if status == "APPROVED" else history[-1]["state"],
        "history": history,
        "blocked_transitions": [],
    }


def finalize_work_order_run(run: WorkOrderRun, output_dir: str | Path) -> RunOutcome:
    """Perform final SWOS governance without invoking model intelligence."""
    if run.status()["status"] != "READY_TO_FINALISE":
        raise WorkOrderError(f"run must be READY_TO_FINALISE, got {run.status()['status']}")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    review_dir = output / "review-findings"
    review_dir.mkdir(exist_ok=True)
    run.export_host_bundle(output / "host-bundle.json")

    run_id = swos_id("evl")
    work_id = swos_id("work")
    request = dict(run.state["request"])
    adapter = dict(run.state["adapter"])
    blockers: list[str] = []
    chain = IntegrityChain()
    chain.append("request.accepted", request)

    citation_assurance = _review_assurance(adapter, "citation_support_audit")
    hostile_assurance = _review_assurance(adapter, "hostile_review")
    review_assurance = {
        "assurance_level": "automatic_delivery",
        "policy": {
            "minimum_independence": "limited",
            "blind_review_required": False,
            "rule": "SWOS records actual review independence; a separate call/context is not presumed independent or blind.",
        },
        "citation_support_audit": citation_assurance,
        "hostile_review": hostile_assurance,
    }
    for record in (citation_assurance, hostile_assurance):
        if record["independence"] not in ACCEPTABLE_AUTOMATIC_REVIEW_INDEPENDENCE:
            blockers.append(
                f"{record['capability']} review independence {record['independence']!r} does not satisfy automatic-delivery assurance."
            )
    _write_json(output / "review-assurance.json", review_assurance)

    judgement_evidence = run.judgement_evidence()
    _write_json(
        output / "judgement-evidence.json",
        {
            "authority_boundary": "Models propose or judge; SWOS decides.",
            "records": judgement_evidence,
        },
    )

    sources, source_id_map, source_blockers = _canonical_sources(run)
    blockers.extend(source_blockers)
    labels = _source_labels(sources)
    _write_json(
        output / "source-register.json",
        [
            {**source.to_dict(include_text=False), "marker": labels[source.source_id]}
            for source in sources
        ],
    )
    retrieval_submission = run._latest("source_retrieval") or {}
    _write_json(
        output / "retrieval.json",
        {
            "capability": "source_retrieval",
            "contract": CAPABILITY_CONTRACTS["source_retrieval"],
            "contract_passed": bool(retrieval_submission.get("contract_passed")),
            "adapter": adapter.get("adapter"),
            "execution_mode": adapter.get("execution_mode"),
            "source_count": len(sources),
            "research_expansions": list(
                run.state.get("research_expansions", [])
                or retrieval_submission.get("research_expansions", [])
            ),
            "work_order_run_id": run.state["run_id"],
        },
    )

    raw_rerank = run._latest("semantic_rerank") or {}
    rerank_contract_passed = bool(
        raw_rerank.get("capability") == "semantic_rerank"
        and raw_rerank.get("contract") == CAPABILITY_CONTRACTS["semantic_rerank"]
        and raw_rerank.get("contract_passed") is True
    )
    if not rerank_contract_passed:
        blockers.append("The SWOS semantic-rerank capability contract did not pass.")
    rerank_record = {
        **{key: value for key, value in raw_rerank.items() if key != "provenance"},
        "capability": "semantic_rerank",
        "contract": CAPABILITY_CONTRACTS["semantic_rerank"],
        "contract_set": "swos.capabilities.v1",
        "contract_passed": rerank_contract_passed,
        "executed": rerank_contract_passed,
        "adapter": adapter.get("adapter"),
        "model_host": adapter.get("model_host"),
        "execution_mode": adapter.get("execution_mode"),
    }
    _write_json(output / "reranking.json", rerank_record)

    matrix, evidence_internal, rejected, evidence_blockers = _evidence_matrix(
        work_id=work_id,
        run=run,
        sources=sources,
        source_id_map=source_id_map,
    )
    blockers.extend(evidence_blockers)
    _write_json(output / "evidence-matrix.json", matrix)
    _write_json(output / "evidence-rejections.json", rejected)
    evidence_source_ids = {item["source_id"] for item in evidence_internal}
    if _legal_topic(str(request.get("topic") or "")) and not any(
        source.primary and source.source_id in evidence_source_ids for source in sources
    ):
        blockers.append("No verified primary legal authority survived into the Evidence Matrix.")

    argument_graph, argument_blockers = _argument_graph(
        work_id=work_id, run=run, evidence_internal=evidence_internal
    )
    blockers.extend(argument_blockers)
    _write_json(output / "argument-graph.json", argument_graph)

    review_documents, review_blockers = _review_documents(run, work_id, hostile_assurance)
    blockers.extend(review_blockers)
    for index, document in enumerate(review_documents, start=1):
        _write_json(review_dir / f"{index:02d}-{document['reviewer_role']}.json", document)
    _write_json(output / "review-summary.json", review_documents)

    source_article = run._latest_revision_or_draft() or ""
    transform = run._latest("prose_transformation") or {}
    verification = run._latest("semantic_verification") or {}
    candidate = transform.get("candidate") or transform.get("final_text")
    transform_passed = verification.get("status") == "PASS" and isinstance(candidate, str)
    article = candidate.strip() if transform_passed else source_article.strip()
    article = _enforce_requested_title(article, str(request.get("topic") or ""))
    prose_evidence = {
        "invoked": bool(transform),
        "capability": "prose_transformation",
        "contract": CAPABILITY_CONTRACTS["prose_transformation"],
        "semantic_verification_contract": CAPABILITY_CONTRACTS["semantic_verification"],
        "semantic_verification": verification,
        "safe_for_automatic_use": transform_passed,
        "used_source_fallback": not transform_passed,
        "authority": "SWOS uses the transformed candidate only after the semantic-verification contract returns PASS; otherwise source text is preserved.",
        "adapter": adapter.get("adapter"),
        "model_host": adapter.get("model_host"),
        "execution_mode": adapter.get("execution_mode"),
    }
    if not source_article:
        blockers.append("No draft or revised article exists.")
    if not transform:
        blockers.append("SWOS prose transformation was not performed.")
    _write_json(output / "prose-evidence.json", prose_evidence)

    article_markers = set(citation_markers(article))
    valid_markers = set(labels.values())
    if not article_markers or not article_markers.issubset(valid_markers):
        blockers.append("Article contains missing or invalid source markers.")
    if len(article_markers) < 3:
        blockers.append("Article uses fewer than three retrieved sources.")
    marker_to_source = {marker: source_id for source_id, marker in labels.items()}
    used_source_ids = {
        marker_to_source[marker] for marker in article_markers if marker in marker_to_source
    }
    if not used_source_ids.issubset(evidence_source_ids):
        blockers.append("Article cites a source that did not survive the Evidence Matrix.")

    word_count = body_word_count(article)
    target = int(request.get("length") or 2500)
    minimum = int(target * 0.85)
    maximum = int(target * 1.15)
    if not minimum <= word_count <= maximum:
        blockers.append(
            f"Article body word count {word_count} is outside governed range {minimum}-{maximum}."
        )

    article = _append_references(article, sources, labels) if article else article
    (output / "article.md").write_text(article, encoding="utf-8")
    _write_json(
        output / "citation-map.json", _citation_map(article, labels) if article else {"markers": []}
    )
    references = [
        {
            "marker": labels[source.source_id],
            **source.to_dict(include_text=False),
            "existence_verified": source.metadata_verified,
            "metadata_verified": source.metadata_verified,
        }
        for source in sources
        if labels[source.source_id] in article_markers
    ]
    _write_json(output / "references.json", references)

    plan = run._latest("research_planning") or {}
    _write_json(output / "research-plan.json", plan)
    security_events = [
        {
            "event": "security.injection_attempt",
            "source_id": source.source_id,
            "title": source.title,
            "instruction_followed": False,
            "content_preserved_in_source_record": True,
        }
        for source in sources
        if source.injection_detected
    ]
    _write_json(output / "security-report.json", {"events": security_events})

    chain.append(
        "work_orders.accepted",
        {
            "run_id": run.state["run_id"],
            "submissions": len(run.state.get("submissions", [])),
            "adapter": adapter.get("adapter"),
            "execution_mode": adapter.get("execution_mode"),
        },
    )
    chain.append(
        "evidence.verified",
        {"supported_claims": len(matrix["rows"]), "rejected_candidates": len(rejected)},
    )
    chain.append(
        "review.recorded",
        {
            "iterations": run.state.get("review_iteration", 0),
            "revisions": run.state.get("revision_count", 0),
            "blocking_findings": len(review_blockers),
            "independence": hostile_assurance["independence"],
            "blind_review_supported": hostile_assurance["blind_review_supported"],
        },
    )

    provisional_status = "REVIEW_REQUIRED" if blockers else "APPROVED"
    _write_json(
        output / "provenance.json",
        _build_epg(
            work_id=work_id,
            status=provisional_status,
            run=run,
            sources=sources,
            evidence_matrix=matrix,
            argument_graph=argument_graph,
        ),
    )
    _write_json(
        output / "decision-ledger.json",
        _build_sdl(
            work_id,
            provisional_status,
            run,
            [row["claim_id"] for row in matrix["rows"]],
        ),
    )
    _write_json(output / "rpm.json", _rpm_snapshot())
    _write_json(output / "scholarly-state.json", _scholarly_state(work_id, provisional_status, run))

    schema_errors = validate_frozen_run_schemas(output)
    if schema_errors:
        blockers.extend(f"Schema validation: {error}" for error in schema_errors[:20])
    status = "REVIEW_REQUIRED" if blockers else "APPROVED"
    if status != provisional_status:
        _write_json(
            output / "provenance.json",
            _build_epg(
                work_id=work_id,
                status=status,
                run=run,
                sources=sources,
                evidence_matrix=matrix,
                argument_graph=argument_graph,
            ),
        )
        _write_json(
            output / "decision-ledger.json",
            _build_sdl(work_id, status, run, [row["claim_id"] for row in matrix["rows"]]),
        )
        _write_json(output / "scholarly-state.json", _scholarly_state(work_id, status, run))

    unresolved = list(dict.fromkeys([*list(plan.get("known_uncertainties") or []), *blockers]))
    confidence = "high" if status == "APPROVED" else ("medium" if matrix["rows"] else "low")
    _write_json(
        output / "confidence-report.json",
        {
            "confidence": confidence,
            "unresolved_questions": unresolved,
            "coverage_limits": list(plan.get("out_of_scope") or []),
            "article_body_word_count": word_count,
        },
    )

    chain.append("governance.final", {"status": status, "blocking_reasons": blockers})
    chain.write(output / "integrity-chain.jsonl")
    if not chain.verify():
        blockers.append("Integrity chain verification failed.")
        status = "REVIEW_REQUIRED"

    capability_events = []
    for item in run.state.get("submissions", []):
        payload = json.loads((run.run_dir / item["file"]).read_text(encoding="utf-8"))
        capability_events.append(
            {
                "capability": payload.get("capability") or item.get("stage"),
                "contract": payload.get("contract"),
                "contract_passed": bool(payload.get("contract_passed", False)),
                "instruction_id": (payload.get("provenance") or {}).get("instruction_id"),
                "instruction_sha256": (payload.get("provenance") or {}).get("instruction_sha256"),
                "provenance": payload.get("provenance"),
                "judgement_evidence": payload.get("judgement_evidence"),
            }
        )
    run_control = {
        "runtime_version": RUNTIME_VERSION,
        "run_id": run_id,
        "work_id": work_id,
        "status": status,
        "human_interventions": 0,
        "normal_user_questions_asked": 0,
        "blocking_reasons": blockers,
        "revision_count": run.state.get("revision_count", 0),
        "research_expansions": list(run.state.get("research_expansions", [])),
        "cross_encoder": rerank_record,
        "capability_contract_set": "swos.capabilities.v1",
        "instruction_set": run.state.get("instruction_set", "swos.stage-instructions.v1"),
        "capability_events": capability_events,
        "review_assurance": review_assurance,
        "authority_boundary": "Models propose or judge. SWOS decides.",
        "execution": {
            "adapter": adapter.get("adapter"),
            "model_host": adapter.get("model_host"),
            "execution_mode": adapter.get("execution_mode"),
            "api_key_used": bool(adapter.get("api_key_used", False)),
            "paid_api_calls": int(adapter.get("paid_api_calls", 0)),
        },
        "started_from_one_request": True,
        "work_order_run_id": run.state["run_id"],
        "host_bundle_role": "replay_interchange_debug_reproducibility",
    }
    _write_json(output / "run-control.json", run_control)

    files_for_manifest = sorted(
        path
        for path in output.rglob("*")
        if path.is_file() and path.name not in {"run-manifest.json", "run-manifest.sha256"}
    )
    manifest = {
        "runtime_version": RUNTIME_VERSION,
        "run_id": run_id,
        "work_id": work_id,
        "status": status,
        "request": request,
        "created_at": _now(),
        "files": {
            str(path.relative_to(output)).replace("\\", "/"): canonical_sha256(path)
            for path in files_for_manifest
        },
    }
    _write_json(output / "run-manifest.json", manifest)
    (output / "run-manifest.sha256").write_text(
        canonical_sha256(output / "run-manifest.json") + "  run-manifest.json\n",
        encoding="utf-8",
    )
    if not verify_manifest(output, manifest):
        blockers.append("Final manifest hash verification failed.")
        status = "REVIEW_REQUIRED"

    return RunOutcome(
        run_id=run_id,
        work_id=work_id,
        status=status,
        output_dir=str(output),
        article_word_count=word_count,
        human_interventions=0,
        normal_user_questions_asked=0,
        unresolved_questions=unresolved,
        blocking_reasons=blockers,
    )
