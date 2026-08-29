"""OpenAI API adapter for SWOS capability contracts.

This module owns OpenAI transport details only. Scholarly instructions are loaded
from canonical SWOS stage-instruction assets and are not defined by this adapter.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from swos_prose.cost import estimate_cost

from .instructions import instruction_text
from .models import ProviderCall, SourceRecord


def _object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


class OpenAIStageProvider:
    """OpenAI Responses transport for SWOS scholarly capabilities."""

    def __init__(
        self,
        *,
        model: str | None = None,
        review_model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model or os.environ.get("SWOS_RUNTIME_MODEL", "gpt-5.6-luna")
        self.review_model = review_model or os.environ.get("SWOS_RUNTIME_REVIEW_MODEL", self.model)
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client
        self.calls: list[ProviderCall] = []

    @staticmethod
    def _usage(response: Any) -> dict[str, int] | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        values = (
            usage
            if isinstance(usage, dict)
            else {
                name: getattr(usage, name, None)
                for name in ("input_tokens", "output_tokens", "total_tokens")
            }
        )
        clean = {
            name: int(value)
            for name, value in values.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        return clean or None

    def _record(self, stage: str, model: str, response: Any, elapsed: float) -> None:
        usage = self._usage(response)
        self.calls.append(
            ProviderCall(
                stage=stage,
                model=model,
                response_id=getattr(response, "id", None),
                input_tokens=(usage or {}).get("input_tokens"),
                output_tokens=(usage or {}).get("output_tokens"),
                total_tokens=(usage or {}).get("total_tokens"),
                cost_estimate_usd=estimate_cost(usage),
                elapsed_seconds=round(elapsed, 4),
            )
        )

    def json_call(
        self,
        stage: str,
        instructions: str,
        payload: dict[str, Any],
        schema: dict[str, Any],
        *,
        max_output_tokens: int = 7000,
        review: bool = False,
    ) -> dict[str, Any]:
        model = self.review_model if review else self.model
        started = time.perf_counter()
        response = self.client.responses.create(
            model=model,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            text={
                "format": {
                    "type": "json_schema",
                    "name": f"swos_{re.sub(r'[^a-z0-9_]', '_', stage.lower())}"[:60],
                    "schema": schema,
                    "strict": True,
                }
            },
            max_output_tokens=max_output_tokens,
            store=False,
        )
        self._record(stage, model, response, time.perf_counter() - started)
        output = getattr(response, "output_text", None)
        if not isinstance(output, str) or not output.strip():
            raise ValueError(f"{stage} returned no structured output")
        data = json.loads(output)
        if not isinstance(data, dict):
            raise ValueError(f"{stage} did not return an object")
        return data

    def text_call(
        self,
        stage: str,
        instructions: str,
        payload: dict[str, Any],
        *,
        max_output_tokens: int = 15000,
        review: bool = False,
    ) -> str:
        model = self.review_model if review else self.model
        started = time.perf_counter()
        response = self.client.responses.create(
            model=model,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            max_output_tokens=max_output_tokens,
            store=False,
        )
        self._record(stage, model, response, time.perf_counter() - started)
        output = getattr(response, "output_text", None)
        if not isinstance(output, str) or not output.strip():
            raise ValueError(f"{stage} returned no text")
        return output.strip()

    def plan(self, request: dict[str, Any], scope_hint: str) -> dict[str, Any]:
        schema = _object_schema(
            {
                "research_question": {"type": "string"},
                "scope": {"type": "string"},
                "out_of_scope": {"type": "array", "items": {"type": "string"}},
                "queries": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 6,
                    "items": {"type": "string"},
                },
                "rival_theses": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 4,
                    "items": {"type": "string"},
                },
                "known_uncertainties": {"type": "array", "items": {"type": "string"}},
                "reviewer_roles": {"type": "array", "items": {"type": "string"}},
            },
            [
                "research_question",
                "scope",
                "out_of_scope",
                "queries",
                "rival_theses",
                "known_uncertainties",
                "reviewer_roles",
            ],
        )
        return self.json_call(
            "research_plan",
            instruction_text("research_planning"),
            {"request": request, "scope_hint": scope_hint},
            schema,
        )

    def rerank(
        self, topic: str, sources: list[SourceRecord], *, top_k: int = 10
    ) -> tuple[list[SourceRecord], dict[str, Any]]:
        score_schema = _object_schema(
            {
                "source_id": {"type": "string"},
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "reason": {"type": "string"},
            },
            ["source_id", "score", "reason"],
        )
        schema = _object_schema({"scores": {"type": "array", "items": score_schema}}, ["scores"])
        payload = {
            "query": topic,
            "candidates": [
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "source_type": source.source_type,
                    "jurisdiction": source.jurisdiction,
                    "primary": source.primary,
                    "text": source.excerpt(1800),
                }
                for source in sources
            ],
        }
        result = self.json_call(
            "semantic_rerank",
            instruction_text("semantic_rerank"),
            payload,
            schema,
            max_output_tokens=5000,
        )
        scores = {item["source_id"]: float(item["score"]) for item in result.get("scores", [])}
        for source in sources:
            source.rerank_score = scores.get(source.source_id, 0.0)
        ranked = sorted(
            sources,
            key=lambda source: (
                source.rerank_score or 0.0,
                1 if source.primary else 0,
                1 if source.metadata_verified else 0,
            ),
            reverse=True,
        )
        return ranked[:top_k], {
            "implementation": "openai_responses_joint_query_document_scoring",
            "capability": "semantic_rerank",
            "contract": "swos.semantic-rerank.v1",
            "contract_passed": True,
            "model": self.model,
            "top_k": top_k,
            "scores": result.get("scores", []),
        }

    def build_evidence(self, topic: str, sources: list[SourceRecord]) -> dict[str, Any]:
        claim_schema = _object_schema(
            {
                "claim": {"type": "string"},
                "source_id": {"type": "string"},
                "exact_quote": {"type": "string"},
                "locator": {"type": "string"},
                "epistemic_type": {
                    "type": "string",
                    "enum": [
                        "observed_fact",
                        "source_backed_claim",
                        "inference",
                        "interpretation",
                        "critical_assessment",
                    ],
                },
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "stance": {"type": "string", "enum": ["support", "counter", "limitation"]},
                "rationale": {"type": "string"},
            },
            [
                "claim",
                "source_id",
                "exact_quote",
                "locator",
                "epistemic_type",
                "confidence",
                "stance",
                "rationale",
            ],
        )
        schema = _object_schema(
            {
                "claims": {
                    "type": "array",
                    "minItems": 6,
                    "maxItems": 18,
                    "items": claim_schema,
                }
            },
            ["claims"],
        )
        payload = {
            "topic": topic,
            "sources": [
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "source_type": source.source_type,
                    "jurisdiction": source.jurisdiction,
                    "primary": source.primary,
                    "text": source.excerpt(5200),
                }
                for source in sources
            ],
        }
        return self.json_call(
            "evidence_extraction",
            instruction_text("evidence_extraction"),
            payload,
            schema,
            max_output_tokens=9000,
        )

    def audit_evidence(
        self, candidates: list[dict[str, Any]], sources: dict[str, SourceRecord]
    ) -> dict[str, Any]:
        audit_schema = _object_schema(
            {
                "index": {"type": "integer", "minimum": 0},
                "support_level": {
                    "type": "string",
                    "enum": [
                        "directly_supports",
                        "partially_supports",
                        "context_only",
                        "contradicts",
                        "citation_laundering_risk",
                        "invalid_citation",
                    ],
                },
                "reason": {"type": "string"},
            },
            ["index", "support_level", "reason"],
        )
        schema = _object_schema({"audits": {"type": "array", "items": audit_schema}}, ["audits"])
        rows = []
        for index, candidate in enumerate(candidates):
            source = sources.get(candidate.get("source_id", ""))
            rows.append(
                {
                    "index": index,
                    "claim": candidate.get("claim"),
                    "quote": candidate.get("exact_quote"),
                    "source_title": source.title if source else None,
                    "source_type": source.source_type if source else None,
                    "source_metadata_verified": source.metadata_verified if source else False,
                }
            )
        return self.json_call(
            "citation_support_audit",
            instruction_text("citation_support_audit"),
            {"rows": rows},
            schema,
            review=True,
            max_output_tokens=7000,
        )

    def build_argument(
        self,
        topic: str,
        evidence_rows: list[dict[str, Any]],
        rival_theses: list[str],
    ) -> dict[str, Any]:
        node_schema = _object_schema(
            {
                "local_id": {"type": "string"},
                "node_type": {
                    "type": "string",
                    "enum": [
                        "claim",
                        "grounds",
                        "warrant",
                        "qualifier",
                        "objection",
                        "rebuttal",
                        "implication",
                        "rival_reading",
                    ],
                },
                "statement": {"type": "string"},
                "evidence_claim_ids": {"type": "array", "items": {"type": "string"}},
            },
            ["local_id", "node_type", "statement", "evidence_claim_ids"],
        )
        edge_schema = _object_schema(
            {
                "from_local_id": {"type": "string"},
                "to_local_id": {"type": "string"},
                "relation": {
                    "type": "string",
                    "enum": [
                        "supports",
                        "warrants",
                        "qualifies",
                        "objects_to",
                        "rebuts",
                        "implies",
                        "rivals",
                        "depends_on",
                    ],
                },
            },
            ["from_local_id", "to_local_id", "relation"],
        )
        schema = _object_schema(
            {
                "thesis": {"type": "string"},
                "nodes": {"type": "array", "minItems": 4, "items": node_schema},
                "edges": {"type": "array", "items": edge_schema},
            },
            ["thesis", "nodes", "edges"],
        )
        return self.json_call(
            "argument_construction",
            instruction_text("argument_construction"),
            {"topic": topic, "evidence": evidence_rows, "rival_theses": rival_theses},
            schema,
            max_output_tokens=7000,
        )

    def draft(
        self,
        request: dict[str, Any],
        plan: dict[str, Any],
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        source_labels: dict[str, str],
    ) -> str:
        payload = {
            "request": request,
            "plan": plan,
            "verified_evidence": evidence_rows,
            "argument": argument,
            "source_markers": source_labels,
            "body_word_target": {
                "target": request.get("length", 2500),
                "preferred_min": int(request.get("length", 2500) * 0.92),
                "preferred_max": int(request.get("length", 2500) * 1.08),
            },
        }
        return self.text_call("draft_generation", instruction_text("draft_generation"), payload)

    def review(
        self,
        article: str,
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        sources: list[SourceRecord],
        *,
        iteration: int,
    ) -> dict[str, Any]:
        roles = [
            "citation_auditor",
            "argument_examiner",
            "discipline_expert",
            "hostile_reviewer",
            "editor",
            "governance_reviewer",
        ]
        categories = [
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
            "structure",
            "clarity",
            "policy_breach",
            "missing_audit_trail",
        ]
        finding_schema = _object_schema(
            {
                "severity": {
                    "type": "string",
                    "enum": ["blocker", "major", "minor", "advisory"],
                },
                "category": {"type": "string", "enum": categories},
                "locus": {"type": "string"},
                "description": {"type": "string"},
                "required_action": {"type": "string"},
            },
            ["severity", "category", "locus", "description", "required_action"],
        )
        review_schema = _object_schema(
            {
                "role": {"type": "string", "enum": roles},
                "verdict": {
                    "type": "string",
                    "enum": ["pass", "pass_with_findings", "fail", "escalate"],
                },
                "attack_summary": {"type": "string"},
                "findings": {"type": "array", "items": finding_schema},
            },
            ["role", "verdict", "attack_summary", "findings"],
        )
        schema = _object_schema(
            {
                "reviews": {
                    "type": "array",
                    "minItems": len(roles),
                    "maxItems": len(roles),
                    "items": review_schema,
                }
            },
            ["reviews"],
        )
        payload = {
            "iteration": iteration,
            "article": article,
            "verified_evidence": evidence_rows,
            "argument": argument,
            "sources": [
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "source_type": source.source_type,
                    "primary": source.primary,
                    "metadata_verified": source.metadata_verified,
                    "excerpt": source.excerpt(1800),
                }
                for source in sources
            ],
        }
        return self.json_call(
            f"hostile_review_{iteration}",
            instruction_text("hostile_review"),
            payload,
            schema,
            review=True,
            max_output_tokens=10000,
        )

    def plan_review_repair(self, topic: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
        schema = _object_schema(
            {
                "research_goal": {"type": "string"},
                "queries": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 6,
                    "items": {"type": "string"},
                },
            },
            ["research_goal", "queries"],
        )
        compact = [
            {
                "category": finding.get("category"),
                "description": finding.get("description"),
                "required_action": finding.get("required_action"),
            }
            for finding in findings
        ]
        return self.json_call(
            "review_research_plan",
            instruction_text("research_repair_planning"),
            {"topic": topic, "blocking_findings": compact},
            schema,
            max_output_tokens=4000,
        )

    def revise(
        self,
        article: str,
        findings: list[dict[str, Any]],
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        source_labels: dict[str, str],
    ) -> str:
        return self.text_call(
            "revision",
            instruction_text("revision"),
            {
                "article": article,
                "findings": findings,
                "verified_evidence": evidence_rows,
                "argument": argument,
                "source_markers": source_labels,
            },
        )

    def semantic_verify(
        self,
        source: str,
        candidate: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        schema = _object_schema(
            {
                "status": {"type": "string", "enum": ["PASS", "REVIEW", "REJECT"]},
                "reason": {"type": "string"},
                "issues": {"type": "array", "items": {"type": "string"}},
            },
            ["status", "reason", "issues"],
        )
        return self.json_call(
            "semantic_verification",
            instruction_text("semantic_verification"),
            {"source": source, "candidate": candidate, "context": context},
            schema,
            review=True,
            max_output_tokens=4000,
        )
