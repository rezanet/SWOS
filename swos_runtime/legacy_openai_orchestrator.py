"""Autonomous SWOS reference orchestrator."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .governance import (
    IntegrityChain,
    body_word_count,
    canonical_sha256,
    citation_markers,
    detect_prompt_injection,
    exact_quote_supported,
    verify_manifest,
)
from .llm import OpenAIStageProvider
from .models import ResearchRequest, RunOutcome, SourceRecord, swos_id
from .retrieval import PublicWebRetriever

RUNTIME_VERSION = "0.1.0"
REVIEW_RESEARCH_CATEGORIES = {
    "missing_counter_evidence",
    "coverage_gap",
    "source_bias",
    "citation_laundering",
    "citation_metadata_error",
    "unsupported_claim",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _legal_topic(topic: str) -> bool:
    lowered = topic.lower()
    return any(term in lowered for term in ("court", "witness", "evidence", "legal", "law"))


def _scope_hint(request: ResearchRequest) -> str:
    if request.jurisdiction:
        return f"User-specified jurisdiction/scope: {request.jurisdiction}."
    if _legal_topic(request.topic):
        return (
            "Governed default: comparative analysis centred on Commonwealth of Australia evidence law, "
            "with England and Wales and United States federal evidence rules as contrasts where supported. "
            "This default avoids pretending that a jurisdiction-sensitive question has one universal answer."
        )
    return "Governed default: scope the question to the strongest retrievable evidence and state coverage limits."


def _state_entry(state: str, phase: str, checkpoint: str) -> dict[str, Any]:
    return {
        "state": state,
        "entered_at": utc_now(),
        "sdlc_phase": phase,
        "governance_checkpoint": checkpoint,
        "epg_state": checkpoint,
        "entered_by": {
            "actor_type": "orchestrator",
            "actor_id": "swos-autonomous-reference-runtime",
            "display_name": "Autonomous SWOS reference runtime",
            "version": RUNTIME_VERSION,
        },
    }


class AutonomousSWOS:
    """One-request research-writing runtime with governed, fail-closed release semantics."""

    def __init__(
        self,
        *,
        stage_provider: Any | None = None,
        retriever: Any | None = None,
        prose_transform: Callable[[str, ResearchRequest], tuple[str, dict[str, Any]]] | None = None,
    ) -> None:
        self.stage_provider = stage_provider or OpenAIStageProvider()
        self.retriever = retriever or PublicWebRetriever()
        self.prose_transform = prose_transform

    def _apply_prose(self, article: str, request: ResearchRequest) -> tuple[str, dict[str, Any]]:
        if self.prose_transform is not None:
            return self.prose_transform(article, request)
        from swos_prose.modes import SUPPORTED_PRESETS
        from swos_prose.providers.openai_responses import OpenAIResponsesSemanticVerifierProvider
        from swos_prose.providers.openai_rewrite import OpenAIResponsesRewriteProvider
        from swos_prose.rewrite import edit_text

        preset = request.style if request.style in SUPPORTED_PRESETS else None
        rewrite_provider = OpenAIResponsesRewriteProvider(
            model=os.environ.get("SWOS_PROSE_OPENAI_REWRITE_MODEL", "gpt-5.6-luna")
        )
        verifier = OpenAIResponsesSemanticVerifierProvider(
            model=os.environ.get("SWOS_PROSE_OPENAI_MODEL", "gpt-5.6-luna")
        )
        chunks = self._prose_chunks(article)
        outputs: list[str] = []
        evidence: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            try:
                result = edit_text(
                    source=chunk,
                    rewrite_provider=rewrite_provider,
                    verifier_provider=verifier,
                    assurance="strict",
                    mode="polish",
                    preset=preset,
                    run_diagnostics=True,
                )
                outputs.append(result.final_text)
                record = result.to_dict()
                record["chunk_index"] = index
                evidence.append(record)
            except Exception as exc:
                outputs.append(chunk)
                evidence.append(
                    {
                        "chunk_index": index,
                        "safe_for_automatic_use": False,
                        "used_source_fallback": True,
                        "error": str(exc),
                    }
                )
        return "\n\n".join(outputs).strip(), {
            "invoked": bool(chunks),
            "chunks": evidence,
            "all_changed_text_safe": all(
                item.get("safe_for_automatic_use", False) or item.get("used_source_fallback", False)
                for item in evidence
            ),
        }

    @staticmethod
    def _prose_chunks(article: str, max_words: int = 650) -> list[str]:
        paragraphs = [part.strip() for part in article.split("\n\n") if part.strip()]
        chunks: list[str] = []
        current: list[str] = []
        count = 0
        for paragraph in paragraphs:
            words = len(paragraph.split())
            if current and count + words > max_words:
                chunks.append("\n\n".join(current))
                current = []
                count = 0
            current.append(paragraph)
            count += words
        if current:
            chunks.append("\n\n".join(current))
        return chunks

    def _build_evidence_matrix(
        self,
        work_id: str,
        candidates: list[dict[str, Any]],
        sources: list[SourceRecord],
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        source_map = {source.source_id: source for source in sources}
        deterministic_valid: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for candidate in candidates:
            source = source_map.get(str(candidate.get("source_id", "")))
            if source is None or not source.metadata_verified:
                rejected.append(
                    {"candidate": candidate, "reason": "source missing or metadata unverified"}
                )
                continue
            if not exact_quote_supported(str(candidate.get("exact_quote", "")), source):
                rejected.append(
                    {
                        "candidate": candidate,
                        "reason": "evidence quote not found verbatim in source",
                    }
                )
                continue
            deterministic_valid.append(candidate)

        audits = self.stage_provider.audit_evidence(deterministic_valid, source_map).get(
            "audits", []
        )
        audit_by_index = {
            int(item["index"]): item
            for item in audits
            if isinstance(item, dict) and isinstance(item.get("index"), int)
        }
        rows: list[dict[str, Any]] = []
        internal_rows: list[dict[str, Any]] = []
        for index, candidate in enumerate(deterministic_valid):
            audit = audit_by_index.get(index, {})
            support = str(audit.get("support_level", "invalid_citation"))
            if support != "directly_supports":
                rejected.append(
                    {
                        "candidate": candidate,
                        "reason": f"independent support audit returned {support}",
                        "audit": audit,
                    }
                )
                continue
            claim_id = swos_id("clm")
            epg_node_id = claim_id
            citation = {
                "source_id": candidate["source_id"],
                "support_level": support,
                "evidence_span": {
                    "locator": candidate.get("locator") or "retrieved passage",
                    "quoted_text": candidate["exact_quote"][:500],
                    "span_type": "passage",
                },
                "support_rationale": candidate.get("rationale") or audit.get("reason") or "",
                "verified_by": {
                    "actor_type": "agent",
                    "actor_id": "swos-citation-auditor",
                    "display_name": "SWOS Citation Auditor",
                    "version": RUNTIME_VERSION,
                },
                "metadata_verified": True,
                "retraction_checked": False,
                "licence_cleared": False,
            }
            row = {
                "claim_id": claim_id,
                "claim_text": candidate["claim"],
                "epistemic_type": candidate.get("epistemic_type", "source_backed_claim"),
                "confidence": candidate.get("confidence", "medium"),
                "citation_burden": "primary_source_required"
                if source_map[candidate["source_id"]].source_type == "primary_law"
                else "single_source",
                "citations": [citation],
                "counter_evidence": [],
                "uncertainty": [],
                "verification_status": "pass",
                "discipline": "interdisciplinary",
                "argument_node_ids": [],
                "epg_node_id": epg_node_id,
                "state": "evidence_verified",
            }
            rows.append(row)
            internal_rows.append(
                {
                    "claim_id": claim_id,
                    "claim": candidate["claim"],
                    "source_id": candidate["source_id"],
                    "source_title": source_map[candidate["source_id"]].title,
                    "source_marker": None,
                    "quote": candidate["exact_quote"],
                    "locator": candidate.get("locator"),
                    "stance": candidate.get("stance", "support"),
                    "confidence": candidate.get("confidence", "medium"),
                }
            )
        counter_present = any(
            row.get("stance") in {"counter", "limitation"} for row in internal_rows
        )
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
        return matrix, internal_rows, rejected

    def _build_argument_graph(
        self,
        work_id: str,
        topic: str,
        evidence_rows: list[dict[str, Any]],
        rival_theses: list[str],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        raw = self.stage_provider.build_argument(topic, evidence_rows, rival_theses)
        local_to_id: dict[str, str] = {}
        nodes: list[dict[str, Any]] = []
        valid_claim_ids = {row["claim_id"] for row in evidence_rows}
        for raw_node in raw.get("nodes", []):
            local = str(raw_node.get("local_id", "node"))
            node_id = swos_id("arg")
            local_to_id[local] = node_id
            claims = [
                cid for cid in raw_node.get("evidence_claim_ids", []) if cid in valid_claim_ids
            ]
            nodes.append(
                {
                    "node_id": node_id,
                    "node_type": raw_node.get("node_type", "claim"),
                    "statement": raw_node.get("statement", ""),
                    "evidence_claim_ids": claims,
                    "strength": "high" if claims else "medium",
                    "hidden_premise": False,
                    "status": "accepted",
                }
            )
        edges = []
        for raw_edge in raw.get("edges", []):
            source = local_to_id.get(str(raw_edge.get("from_local_id", "")))
            target = local_to_id.get(str(raw_edge.get("to_local_id", "")))
            if source and target:
                edges.append(
                    {
                        "from_node": source,
                        "to_node": target,
                        "relation": raw_edge.get("relation", "depends_on"),
                        "relation_confidence": "medium",
                    }
                )
        thesis_id = next(
            (node["node_id"] for node in nodes if node["node_type"] == "claim"), nodes[0]["node_id"]
        )
        graph = {
            "schema_version": "1.0.0",
            "work_id": work_id,
            "thesis": {
                "node_id": thesis_id,
                "statement": raw.get("thesis", ""),
                "contribution_type": "synthesis",
                "rival_theses_considered": rival_theses,
            },
            "nodes": nodes,
            "edges": edges,
            "unresolved_objections": [],
        }
        return graph, raw

    @staticmethod
    def _review_requires_research(findings: list[dict[str, Any]]) -> bool:
        research_categories = {
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
            "over_association",
            "genre_mismatch",
        }
        return any(finding.get("category") in research_categories for finding in findings)

    @staticmethod
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

    @staticmethod
    def _source_labels(sources: list[SourceRecord]) -> dict[str, str]:
        return {source.source_id: f"S{index}" for index, source in enumerate(sources, start=1)}

    @staticmethod
    def _append_references(
        article: str, sources: list[SourceRecord], labels: dict[str, str]
    ) -> str:
        article = re.split(r"(?im)^\s*##\s+References\s*$", article)[0].strip()
        used_markers = set(citation_markers(article))
        lines = ["## References"]
        for source in sources:
            label = labels[source.source_id]
            if label not in used_markers:
                continue
            author = f"{source.author}. " if source.author else ""
            date = f" ({source.published_date})" if source.published_date else ""
            lines.append(f"- [{label}] {author}{source.title}{date}. {source.url}")
        return article + "\n\n" + "\n".join(lines) + "\n"

    @staticmethod
    def _citation_map(article: str, labels: dict[str, str]) -> dict[str, Any]:
        reverse = {label: source_id for source_id, label in labels.items()}
        occurrences: dict[str, list[str]] = {label: [] for label in reverse}
        for paragraph in [part.strip() for part in article.split("\n\n") if part.strip()]:
            for marker in set(citation_markers(paragraph)):
                if marker in occurrences:
                    occurrences[marker].append(paragraph[:700])
        return {
            "markers": [
                {
                    "marker": marker,
                    "source_id": reverse[marker],
                    "occurrences": snippets,
                }
                for marker, snippets in occurrences.items()
                if snippets
            ]
        }

    def _review_documents(
        self, work_id: str, review_result: dict[str, Any], iteration: int
    ) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        for review in review_result.get("reviews", []):
            findings = []
            for finding in review.get("findings", []):
                findings.append(
                    {
                        "finding_id": swos_id("rev"),
                        "severity": finding["severity"],
                        "category": finding["category"],
                        "description": finding["description"],
                        "locus": finding.get("locus") or "article",
                        "required_action": finding.get("required_action") or "review",
                        "status": "open",
                    }
                )
            documents.append(
                {
                    "schema_version": "1.0.0",
                    "work_id": work_id,
                    "reviewer_role": review["role"],
                    "discipline": "interdisciplinary",
                    "iteration": iteration,
                    "verdict": review["verdict"],
                    "blind_review": review["role"] in {"argument_examiner", "hostile_reviewer"},
                    "findings": findings,
                }
            )
        return documents

    @staticmethod
    def _blocking_findings(review_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            finding
            for review in review_documents
            for finding in review.get("findings", [])
            if finding.get("severity") in {"blocker", "major"} and finding.get("status") == "open"
        ]

    def _build_epg(
        self,
        work_id: str,
        sources: list[SourceRecord],
        evidence_matrix: dict[str, Any],
        argument_graph: dict[str, Any],
        status: str,
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
                        "access_status": "open_access",
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
                        "at_time": utc_now(),
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
        output_entity = swos_id("prov")
        entities.append(
            {
                "entity_id": output_entity,
                "entity_type": "output_bundle",
                "label": f"Autonomous SWOS run {status}",
                "data_classification": "public",
            }
        )
        activity_types = [
            "search",
            "retrieval",
            "classification",
            "citation_check",
            "argument_construction",
            "drafting",
            "review",
            "revision",
            "evaluation",
        ]
        activities = [
            {
                "activity_id": swos_id("prov"),
                "activity_type": activity,
                "started_at": utc_now(),
                "ended_at": utc_now(),
                "tool_id": "swos-autonomous-reference-runtime",
            }
            for activity in activity_types
        ]
        return {
            "schema_version": "1.0.0",
            "work_id": work_id,
            "prov_compatibility": {"prov_model": "W3C PROV-DM", "serialisation": "prov-json"},
            "entities": entities,
            "activities": activities,
            "agents": [
                {
                    "agent_id": "agt-00000000-0000-0000-0000-000000000001",
                    "agent_kind": "orchestrator",
                    "label": "Autonomous SWOS reference runtime",
                    "version": RUNTIME_VERSION,
                },
                {
                    "agent_id": "agt-00000000-0000-0000-0000-000000000002",
                    "agent_kind": "model",
                    "label": getattr(self.stage_provider, "model", "injected-provider"),
                    "version": "runtime-configured",
                },
            ],
            "relations": relations,
        }

    @staticmethod
    def _build_sdl(
        work_id: str, scope_hint: str, status: str, evidence_refs: list[str]
    ) -> dict[str, Any]:
        actor = {
            "actor_type": "orchestrator",
            "actor_id": "swos-autonomous-reference-runtime",
            "display_name": "Autonomous SWOS reference runtime",
            "version": RUNTIME_VERSION,
        }
        return {
            "schema_version": "1.0.0",
            "work_id": work_id,
            "append_only": True,
            "entries": [
                {
                    "decision_id": swos_id("dec"),
                    "decision_type": "scope",
                    "question": "How should an underspecified jurisdictional scope be handled without interrupting the user?",
                    "options_considered": [
                        {"option": "Apply the governed comparative/default scope and record it."},
                        {
                            "option": "Interrupt the user for routine scope clarification.",
                            "why_rejected": "Violates the Autonomy Contract when a conservative useful default exists.",
                        },
                    ],
                    "selected_option": scope_hint,
                    "rationale": "Ordinary ambiguity is resolved by a transparent, conservative assumption rather than making the user orchestrate the workflow.",
                    "criteria_applied": ["autonomy-contract", "jurisdiction-sensitive-research"],
                    "evidence_refs": [],
                    "counter_evidence_refs": [],
                    "argument_refs": [],
                    "confidence": "medium",
                    "uncertainty": ["domain_transfer_risk"],
                    "review_status": "passed",
                    "responsible_agent": actor,
                    "timestamp": utc_now(),
                    "lifecycle_status": "evaluated",
                    "reversibility": "reversible",
                },
                {
                    "decision_id": swos_id("dec"),
                    "decision_type": "governance",
                    "question": "Does this run satisfy the automatic-delivery governance gate?",
                    "options_considered": [
                        {"option": "APPROVED"},
                        {"option": "REVIEW_REQUIRED"},
                    ],
                    "selected_option": status,
                    "rationale": "Selected from deterministic evidence, citation, review, semantic, provenance and package-integrity gates.",
                    "criteria_applied": [
                        "SWOS constitutional rules 3-7",
                        "Autonomous SWOS final gate",
                    ],
                    "evidence_refs": evidence_refs,
                    "counter_evidence_refs": [],
                    "argument_refs": [],
                    "confidence": "high" if status == "APPROVED" else "medium",
                    "uncertainty": [] if status == "APPROVED" else ["missing_evidence"],
                    "review_status": "passed" if status == "APPROVED" else "escalated",
                    "responsible_agent": actor,
                    "timestamp": utc_now(),
                    "lifecycle_status": "approved" if status == "APPROVED" else "challenged",
                    "reversibility": "reversible",
                },
            ],
        }

    @staticmethod
    def _rpm_snapshot() -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "programme_id": "work-00000000-0000-0000-0000-000000000001",
            "title": "Autonomous SWOS reference runtime",
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

    @staticmethod
    def _scholarly_state(work_id: str, states: list[dict[str, Any]], status: str) -> dict[str, Any]:
        current = "approved" if status == "APPROVED" else states[-1]["state"]
        history = list(states)
        if status == "APPROVED" and history[-1]["state"] != "approved":
            history.append(
                _state_entry("approved", "release", "automatic-delivery-governance-pass")
            )
        return {
            "schema_version": "1.0.0",
            "work_id": work_id,
            "current_state": current,
            "history": history,
            "blocked_transitions": [],
        }

    @staticmethod
    def _validate_schemas(output_dir: Path) -> list[str]:
        try:
            import jsonschema
        except ImportError:
            return ["jsonschema unavailable; frozen artefact contracts could not be validated"]
        root = Path(__file__).resolve().parents[1]
        schema_dir = root / "schemas"
        mappings = {
            "evidence-matrix.json": "evidence-matrix/evidence-matrix.schema.json",
            "argument-graph.json": "argument-graph/argument-graph.schema.json",
            "provenance.json": "provenance-graph/epg.schema.json",
            "decision-ledger.json": "decision-ledger/sdl.schema.json",
            "rpm.json": "memory/rpm.schema.json",
            "scholarly-state.json": "state/scholarly-state.schema.json",
        }
        required_schemas = list(mappings.values()) + [
            "common/common.schema.json",
            "reviewer/reviewer-finding.schema.json",
        ]
        store: dict[str, Any] = {}
        for rel in required_schemas:
            schema = json.loads((schema_dir / rel).read_text(encoding="utf-8"))
            store[schema["$id"]] = schema
        errors: list[str] = []
        for filename, rel in mappings.items():
            path = output_dir / filename
            schema = json.loads((schema_dir / rel).read_text(encoding="utf-8"))
            instance = json.loads(path.read_text(encoding="utf-8"))
            resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
            validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
            errors.extend(
                f"{filename}: {'/'.join(str(part) for part in err.path)}: {err.message}"
                for err in validator.iter_errors(instance)
            )
        reviewer_schema = json.loads(
            (schema_dir / "reviewer/reviewer-finding.schema.json").read_text(encoding="utf-8")
        )
        resolver = jsonschema.RefResolver(
            base_uri=reviewer_schema["$id"], referrer=reviewer_schema, store=store
        )
        reviewer_validator = jsonschema.Draft202012Validator(reviewer_schema, resolver=resolver)
        for path in sorted((output_dir / "review-findings").glob("*.json")):
            instance = json.loads(path.read_text(encoding="utf-8"))
            errors.extend(
                f"{path.name}: {'/'.join(str(part) for part in err.path)}: {err.message}"
                for err in reviewer_validator.iter_errors(instance)
            )
        return errors

    def run(self, request: ResearchRequest, output_dir: str | Path) -> RunOutcome:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        review_dir = output / "review-findings"
        review_dir.mkdir(exist_ok=True)
        run_id = swos_id("evl")
        work_id = swos_id("work")
        chain = IntegrityChain()
        states = [_state_entry("initiated", "discover", "request-normalised")]
        blockers: list[str] = []
        unresolved: list[str] = []
        scope_hint = _scope_hint(request)
        chain.append("request.accepted", request.to_dict())

        plan = self.stage_provider.plan(request.to_dict(), scope_hint)
        _write_json(output / "research-plan.json", plan)
        states.append(_state_entry("planned", "design", "research-plan-complete"))
        chain.append(
            "research.planned", {"scope": plan.get("scope"), "queries": plan.get("queries", [])}
        )

        sources = self.retriever.retrieve(request.topic, plan.get("queries", []))
        states.append(_state_entry("evidence_gathering", "build", "retrieval-complete"))
        if not sources:
            blockers.append("No retrievable sources were available.")
        ranked: list[SourceRecord] = sources
        rerank_record: dict[str, Any] = {"method": "not_run", "scores": []}
        if sources:
            ranked, rerank_record = self.stage_provider.rerank(request.topic, sources, top_k=10)
        for source in ranked:
            source.injection_detected = source.injection_detected or detect_prompt_injection(
                source.text
            )
        labels = self._source_labels(ranked)
        _write_json(
            output / "retrieval.json",
            {
                "queries": plan.get("queries", []),
                "retriever_events": getattr(self.retriever, "events", []),
                "source_count": len(sources),
            },
        )
        _write_json(output / "reranking.json", rerank_record)
        _write_json(
            output / "source-register.json",
            [
                {**source.to_dict(include_text=False), "marker": labels.get(source.source_id)}
                for source in ranked
            ],
        )
        security_events = [
            {
                "event": "security.injection_attempt",
                "source_id": source.source_id,
                "title": source.title,
                "instruction_followed": False,
                "content_preserved_in_source_record": True,
            }
            for source in ranked
            if source.injection_detected
        ]
        _write_json(output / "security-report.json", {"events": security_events})
        chain.append(
            "retrieval.complete",
            {"source_count": len(ranked), "security_events": len(security_events)},
        )

        evidence_matrix = {
            "schema_version": "1.0.0",
            "work_id": work_id,
            "coverage": {
                "total_claims": 0,
                "supported_claims": 0,
                "unsupported_claims": 0,
                "uncertain_claims": 0,
                "counter_evidence_present": False,
                "source_diversity_index": 0,
            },
            "rows": [],
        }
        evidence_rows: list[dict[str, Any]] = []
        rejected_evidence: list[dict[str, Any]] = []
        research_expansions: list[dict[str, Any]] = []

        def rebuild_evidence() -> None:
            nonlocal evidence_matrix, evidence_rows, rejected_evidence
            if not ranked:
                return
            evidence_candidates = self.stage_provider.build_evidence(request.topic, ranked).get(
                "claims", []
            )
            matrix, rows, rejections = self._build_evidence_matrix(
                work_id, evidence_candidates, ranked
            )
            evidence_matrix = matrix
            evidence_rows = rows
            rejected_evidence.extend(rejections)

        rebuild_evidence()

        for attempt in range(1, 3):
            needs_claims = len(evidence_rows) < 5
            needs_counter = not evidence_matrix["coverage"].get("counter_evidence_present")
            if not needs_claims and not needs_counter:
                break

            expansion_queries: list[str] = []
            if needs_counter:
                expansion_queries.extend(
                    str(item) for item in plan.get("rival_theses", [])[:3] if str(item).strip()
                )
            if needs_claims:
                expansion_queries.extend(
                    str(item)
                    for item in plan.get("known_uncertainties", [])[:2]
                    if str(item).strip()
                )
            expansion_queries.append(
                f"{request.topic} counterexamples exceptions limitations evidence"
            )

            before_keys = {
                (source.identifiers.get("doi") or source.url or source.title).lower()
                for source in sources
            }
            expanded = self.retriever.retrieve(request.topic, expansion_queries)
            added = []
            for source in expanded:
                key = (source.identifiers.get("doi") or source.url or source.title).lower()
                if key in before_keys:
                    continue
                before_keys.add(key)
                sources.append(source)
                added.append(source)

            expansion_record = {
                "attempt": attempt,
                "reason": {
                    "fewer_than_five_verified_claims": needs_claims,
                    "missing_counter_or_limitation": needs_counter,
                },
                "queries": expansion_queries,
                "new_sources": len(added),
            }
            research_expansions.append(expansion_record)
            chain.append("research.expanded", expansion_record)
            if not added:
                break

            ranked, rerank_record = self.stage_provider.rerank(request.topic, sources, top_k=10)
            for source in ranked:
                source.injection_detected = source.injection_detected or detect_prompt_injection(
                    source.text
                )
            labels = self._source_labels(ranked)
            rebuild_evidence()

        if sources:
            blockers = [
                blocker
                for blocker in blockers
                if blocker != "No retrievable sources were available."
            ]

        labels = self._source_labels(ranked)
        _write_json(
            output / "retrieval.json",
            {
                "queries": plan.get("queries", []),
                "research_expansions": research_expansions,
                "retriever_events": getattr(self.retriever, "events", []),
                "source_count": len(sources),
            },
        )
        _write_json(output / "reranking.json", rerank_record)
        _write_json(
            output / "source-register.json",
            [
                {**source.to_dict(include_text=False), "marker": labels.get(source.source_id)}
                for source in ranked
            ],
        )
        security_events = [
            {
                "event": "security.injection_attempt",
                "source_id": source.source_id,
                "title": source.title,
                "instruction_followed": False,
                "content_preserved_in_source_record": True,
            }
            for source in ranked
            if source.injection_detected
        ]
        _write_json(output / "security-report.json", {"events": security_events})
        _write_json(output / "evidence-matrix.json", evidence_matrix)
        _write_json(output / "evidence-rejections.json", rejected_evidence)
        chain.append(
            "evidence.verified",
            {
                "supported_claims": len(evidence_rows),
                "rejected_candidates": len(rejected_evidence),
            },
        )
        if not evidence_rows:
            blockers.append(
                "No claim survived exact-span and independent citation-support verification."
            )

        used_source_ids = {row["source_id"] for row in evidence_rows}
        if _legal_topic(request.topic) and not any(
            source.primary and source.source_id in used_source_ids for source in ranked
        ):
            blockers.append(
                "No verified primary legal authority survived into the Evidence Matrix."
            )
        if rerank_record.get("method") != "openai_joint_query_document_cross_encoder":
            blockers.append("The governed semantic cross-encoder reranker did not execute.")
        if len(evidence_rows) < 5:
            blockers.append("Fewer than five verified evidence claims survived the evidence gate.")
        if not evidence_matrix["coverage"].get("counter_evidence_present"):
            blockers.append(
                "No verified limitation or counter-evidence survived the evidence gate."
            )

        argument_graph = {
            "schema_version": "1.0.0",
            "work_id": work_id,
            "thesis": {
                "node_id": swos_id("arg"),
                "statement": "",
                "contribution_type": "synthesis",
                "rival_theses_considered": plan.get("rival_theses", []),
            },
            "nodes": [],
            "edges": [],
            "unresolved_objections": [],
        }
        argument_raw: dict[str, Any] = {}
        if not blockers:
            states.append(_state_entry("evidence_verified", "validate", "evidence-gate-pass"))
            argument_graph, argument_raw = self._build_argument_graph(
                work_id, request.topic, evidence_rows, plan.get("rival_theses", [])
            )
            if not argument_graph.get("nodes"):
                blockers.append("Argument Graph contains no nodes.")
        _write_json(output / "argument-graph.json", argument_graph)
        if not blockers:
            states.append(_state_entry("argument_constructed", "build", "argument-graph-complete"))
        chain.append(
            "argument.constructed",
            {
                "nodes": len(argument_graph.get("nodes", [])),
                "edges": len(argument_graph.get("edges", [])),
            },
        )

        preliminary_status = "REVIEW_REQUIRED" if blockers else "APPROVED"
        preliminary_epg = self._build_epg(
            work_id, ranked, evidence_matrix, argument_graph, preliminary_status
        )
        preliminary_sdl = self._build_sdl(
            work_id,
            scope_hint,
            preliminary_status,
            [row["claim_id"] for row in evidence_matrix.get("rows", [])],
        )
        _write_json(output / "provenance.json", preliminary_epg)
        _write_json(output / "decision-ledger.json", preliminary_sdl)
        _write_json(output / "rpm.json", self._rpm_snapshot())

        article = ""
        prose_evidence: dict[str, Any] = {"invoked": False, "chunks": []}
        all_review_documents: list[dict[str, Any]] = []
        latest_review_documents: list[dict[str, Any]] = []
        revision_count = 0
        if not blockers:
            source_labels = labels
            for row in evidence_rows:
                row["source_marker"] = source_labels[row["source_id"]]
            article = self.stage_provider.draft(
                request.to_dict(), plan, evidence_rows, argument_raw, source_labels
            )
            article = self._enforce_requested_title(article, request.topic)
            states.append(_state_entry("draft_generated", "build", "draft-complete"))
            chain.append("draft.generated", {"body_words": body_word_count(article)})
            article, prose_evidence = self._apply_prose(article, request)
            article = self._enforce_requested_title(article, request.topic)
            for iteration in range(1, 5):
                review_result = self.stage_provider.review(
                    article, evidence_rows, argument_raw, ranked, iteration=iteration
                )
                documents = self._review_documents(work_id, review_result, iteration)
                latest_review_documents = documents
                all_review_documents.extend(documents)
                blocking = self._blocking_findings(documents)
                if not blocking:
                    break
                if iteration == 4:
                    break

                research_repaired = False
                if self._review_requires_research(blocking):
                    repair_plan = self.stage_provider.plan_review_repair(request.topic, blocking)
                    repair_queries = [
                        str(query).strip()
                        for query in repair_plan.get("queries", [])
                        if str(query).strip()
                    ][:6]
                    before_keys = {
                        (source.identifiers.get("doi") or source.url or source.title).lower()
                        for source in sources
                    }
                    expanded = self.retriever.retrieve(request.topic, repair_queries)
                    added: list[SourceRecord] = []
                    for source in expanded:
                        key = (source.identifiers.get("doi") or source.url or source.title).lower()
                        if key in before_keys:
                            continue
                        before_keys.add(key)
                        sources.append(source)
                        added.append(source)

                    repair_record = {
                        "attempt": len(research_expansions) + 1,
                        "phase": "review_repair",
                        "review_iteration": iteration,
                        "trigger_categories": sorted(
                            {str(finding.get("category")) for finding in blocking}
                        ),
                        "research_goal": repair_plan.get("research_goal"),
                        "queries": repair_queries,
                        "new_sources": len(added),
                    }
                    research_expansions.append(repair_record)
                    chain.append("research.review_repair", repair_record)

                    if added:
                        old_ranked = ranked
                        old_rerank = rerank_record
                        old_labels = labels
                        old_matrix = evidence_matrix
                        old_rows = evidence_rows
                        old_argument_graph = argument_graph
                        old_argument_raw = argument_raw

                        ranked, rerank_record = self.stage_provider.rerank(
                            request.topic, sources, top_k=12
                        )
                        for source in ranked:
                            source.injection_detected = (
                                source.injection_detected or detect_prompt_injection(source.text)
                            )
                        labels = self._source_labels(ranked)
                        rebuild_evidence()
                        used_source_ids = {row["source_id"] for row in evidence_rows}
                        evidence_gate_ok = (
                            len(evidence_rows) >= 5
                            and evidence_matrix["coverage"].get("counter_evidence_present")
                            and (
                                not _legal_topic(request.topic)
                                or any(
                                    source.primary and source.source_id in used_source_ids
                                    for source in ranked
                                )
                            )
                        )
                        if evidence_gate_ok:
                            for row in evidence_rows:
                                row["source_marker"] = labels[row["source_id"]]
                            argument_graph, argument_raw = self._build_argument_graph(
                                work_id,
                                request.topic,
                                evidence_rows,
                                plan.get("rival_theses", []),
                            )
                            states.append(
                                _state_entry(
                                    "evidence_gathering",
                                    "build",
                                    "review-driven-research-complete",
                                )
                            )
                            states.append(
                                _state_entry(
                                    "evidence_verified",
                                    "validate",
                                    "review-driven-evidence-pass",
                                )
                            )
                            states.append(
                                _state_entry(
                                    "argument_constructed",
                                    "build",
                                    "review-driven-argument-rebuild",
                                )
                            )
                            article = self.stage_provider.draft(
                                request.to_dict(),
                                plan,
                                evidence_rows,
                                argument_raw,
                                labels,
                            )
                            article = self._enforce_requested_title(article, request.topic)
                            source_labels = labels
                            research_repaired = True
                        else:
                            ranked = old_ranked
                            rerank_record = old_rerank
                            labels = old_labels
                            evidence_matrix = old_matrix
                            evidence_rows = old_rows
                            argument_graph = old_argument_graph
                            argument_raw = old_argument_raw

                if not research_repaired:
                    argument_categories = {"hidden_premise", "invalid_inference", "structure"}
                    if any(finding.get("category") in argument_categories for finding in blocking):
                        argument_graph, argument_raw = self._build_argument_graph(
                            work_id,
                            request.topic,
                            evidence_rows,
                            plan.get("rival_theses", []),
                        )
                    article = self.stage_provider.revise(
                        article, blocking, evidence_rows, argument_raw, source_labels
                    )
                    article = self._enforce_requested_title(article, request.topic)

                revision_count += 1
                article, revision_prose = self._apply_prose(article, request)
                article = self._enforce_requested_title(article, request.topic)
                prose_evidence.setdefault("revision_passes", []).append(revision_prose)
            states.append(_state_entry("reviewed", "validate", "independent-review-complete"))
            if revision_count:
                states.append(_state_entry("revised", "validate", "bounded-revision-complete"))
            chain.append(
                "review.complete",
                {
                    "iterations": max(
                        (doc["iteration"] for doc in all_review_documents), default=0
                    ),
                    "revisions": revision_count,
                    "latest_blockers": len(self._blocking_findings(latest_review_documents)),
                },
            )

        # Persist the final research/evidence/argument state after any reviewer-driven repairs.
        labels = self._source_labels(ranked)
        _write_json(
            output / "retrieval.json",
            {
                "queries": plan.get("queries", []),
                "research_expansions": research_expansions,
                "retriever_events": getattr(self.retriever, "events", []),
                "source_count": len(sources),
            },
        )
        _write_json(output / "reranking.json", rerank_record)
        _write_json(
            output / "source-register.json",
            [
                {**source.to_dict(include_text=False), "marker": labels.get(source.source_id)}
                for source in ranked
            ],
        )
        security_events = [
            {
                "event": "security.injection_attempt",
                "source_id": source.source_id,
                "title": source.title,
                "instruction_followed": False,
                "content_preserved_in_source_record": True,
            }
            for source in ranked
            if source.injection_detected
        ]
        _write_json(output / "security-report.json", {"events": security_events})
        _write_json(output / "evidence-matrix.json", evidence_matrix)
        _write_json(output / "evidence-rejections.json", rejected_evidence)
        _write_json(output / "argument-graph.json", argument_graph)

        for document in all_review_documents:
            filename = f"{document['iteration']:02d}-{document['reviewer_role']}.json"
            _write_json(review_dir / filename, document)
        _write_json(output / "review-summary.json", all_review_documents)
        _write_json(output / "prose-evidence.json", prose_evidence)

        if article:
            article = self._append_references(article, ranked, labels)
            (output / "article.md").write_text(article, encoding="utf-8")
        else:
            (output / "article.md").write_text(
                "# REVIEW REQUIRED\n\nNo article was drafted because a pre-draft governance gate failed.\n",
                encoding="utf-8",
            )
        citation_map = self._citation_map(article, labels) if article else {"markers": []}
        _write_json(output / "citation-map.json", citation_map)

        used_markers = set(citation_markers(article)) if article else set()
        references = [
            {
                "marker": labels[source.source_id],
                **source.to_dict(include_text=False),
                "existence_verified": source.metadata_verified,
                "metadata_verified": source.metadata_verified,
            }
            for source in ranked
            if labels[source.source_id] in used_markers
        ]
        _write_json(output / "references.json", references)

        latest_blockers = self._blocking_findings(latest_review_documents)
        if latest_blockers:
            blockers.append(
                f"Final reviewer panel retained {len(latest_blockers)} blocker/major finding(s)."
            )
        if article:
            word_count = body_word_count(article)
            minimum = int(request.length * 0.85)
            maximum = int(request.length * 1.15)
            if not minimum <= word_count <= maximum:
                blockers.append(
                    f"Article body word count {word_count} is outside governed range {minimum}-{maximum}."
                )
            valid_markers = set(labels.values())
            article_markers = set(citation_markers(article))
            if not article_markers or not article_markers.issubset(valid_markers):
                blockers.append("Article contains missing or invalid source markers.")
            if len(article_markers) < 3:
                blockers.append("Article uses fewer than three independently retrieved sources.")
        else:
            word_count = 0
        if not prose_evidence.get("invoked"):
            blockers.append("SWOS Prose was not invoked on the generated article.")
        if prose_evidence.get("invoked") and not prose_evidence.get("all_changed_text_safe", True):
            blockers.append("A SWOS Prose chunk failed safe-use/fallback accounting.")
        if not chain.verify():
            blockers.append("Integrity chain verification failed.")

        provisional_status = "REVIEW_REQUIRED" if blockers else "APPROVED"
        epg = self._build_epg(work_id, ranked, evidence_matrix, argument_graph, provisional_status)
        sdl = self._build_sdl(
            work_id,
            scope_hint,
            provisional_status,
            [row["claim_id"] for row in evidence_matrix.get("rows", [])],
        )
        scholarly_state = self._scholarly_state(work_id, states, provisional_status)
        _write_json(output / "provenance.json", epg)
        _write_json(output / "decision-ledger.json", sdl)
        _write_json(output / "scholarly-state.json", scholarly_state)

        schema_errors = self._validate_schemas(output)
        if schema_errors:
            blockers.extend(f"Schema validation: {error}" for error in schema_errors[:20])
        status = "REVIEW_REQUIRED" if blockers else "APPROVED"
        if status != provisional_status:
            epg = self._build_epg(work_id, ranked, evidence_matrix, argument_graph, status)
            sdl = self._build_sdl(
                work_id,
                scope_hint,
                status,
                [row["claim_id"] for row in evidence_matrix.get("rows", [])],
            )
            scholarly_state = self._scholarly_state(work_id, states, status)
            _write_json(output / "provenance.json", epg)
            _write_json(output / "decision-ledger.json", sdl)
            _write_json(output / "scholarly-state.json", scholarly_state)

        unresolved = list(dict.fromkeys([*plan.get("known_uncertainties", []), *blockers]))
        confidence = "high" if status == "APPROVED" else ("medium" if evidence_rows else "low")
        _write_json(
            output / "confidence-report.json",
            {
                "confidence": confidence,
                "unresolved_questions": unresolved,
                "coverage_limits": plan.get("out_of_scope", []),
                "article_body_word_count": word_count,
            },
        )
        chain.append("governance.final", {"status": status, "blocking_reasons": blockers})
        chain.write(output / "integrity-chain.jsonl")

        provider_calls = [
            call.to_dict() if hasattr(call, "to_dict") else call
            for call in getattr(self.stage_provider, "calls", [])
        ]
        run_control = {
            "runtime_version": RUNTIME_VERSION,
            "run_id": run_id,
            "work_id": work_id,
            "status": status,
            "human_interventions": 0,
            "normal_user_questions_asked": 0,
            "blocking_reasons": blockers,
            "revision_count": revision_count,
            "cross_encoder": rerank_record,
            "provider_calls": provider_calls,
            "started_from_one_request": True,
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
            "request": request.to_dict(),
            "created_at": utc_now(),
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
            status = "REVIEW_REQUIRED"
            blockers.append("Final manifest hash verification failed.")
            run_control["status"] = status
            run_control["blocking_reasons"] = blockers
            _write_json(output / "run-control.json", run_control)

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
