"""Provider-neutral Autonomous SWOS core orchestrator.

The core owns the scholarly state machine and deterministic governance. It knows
SWOS capabilities, contracts and canonical instructions; it does not know vendor
SDKs, model product names or provider-specific prompt behaviour.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from .broker import CapabilityBroker, CapabilityBrokerError
from .capabilities import CAPABILITY_CONTRACT_SET, CAPABILITY_CONTRACTS
from .finalizer import finalize_work_order_run
from .governance import detect_prompt_injection, exact_quote_supported
from .models import ResearchRequest, RunOutcome, SourceRecord
from .work_orders import WorkOrderError, WorkOrderRun

RUNTIME_VERSION = "0.2.0"
MAX_RESEARCH_EXPANSIONS = 2
REVIEW_RESEARCH_CATEGORIES = {
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
            "State this scope and its limitations rather than pretending the question has one universal answer."
        )
    return "Governed default: scope the question to the strongest retrievable evidence and state coverage limits."


def _injected_manifest(broker: CapabilityBroker) -> dict[str, Any]:
    """Describe an injected test/local binding without introducing vendor identity."""
    capabilities = {
        name: {"level": "native", "contract": contract, "assurance": []}
        for name, contract in CAPABILITY_CONTRACTS.items()
    }
    for review_capability in ("citation_support_audit", "hostile_review"):
        capabilities[review_capability].update(
            {
                "review_mode": "injected-binding",
                "independence": "limited",
                "blind_review_supported": False,
                "independence_limitations": [
                    "Injected bindings do not prove organisational or model independence."
                ],
            }
        )
    capabilities["semantic_verification"]["assurance"] = [
        "adapter_semantic_judgement_or_deterministic_identity_fallback"
    ]
    return {
        "contract_set": CAPABILITY_CONTRACT_SET,
        "adapter": broker.adapter,
        "model_host": broker.model_host,
        "execution_mode": broker.execution_mode,
        "api_key_used": False,
        "paid_api_calls": 0,
        "capabilities": capabilities,
    }


def _sources(payload: dict[str, Any]) -> list[SourceRecord]:
    return [SourceRecord(**item) for item in payload.get("sources", []) if isinstance(item, dict)]


def _ranked_sources(run: WorkOrderRun) -> list[SourceRecord]:
    sources = _sources(run._latest("source_retrieval") or {})
    rerank = run._latest("semantic_rerank") or {}
    scores = {
        str(item.get("source_id")): float(item.get("score", 0))
        for item in rerank.get("scores", [])
        if isinstance(item, dict)
    }
    for source in sources:
        source.rerank_score = scores.get(source.source_id, 0.0)
    return sorted(
        sources,
        key=lambda source: (
            source.rerank_score or 0.0,
            1 if source.primary else 0,
            1 if source.metadata_verified else 0,
        ),
        reverse=True,
    )


def _source_labels(run: WorkOrderRun) -> dict[str, str]:
    # Citation labels are SWOS-owned and deterministic from retrieval order.
    return {
        source.source_id: f"S{index}"
        for index, source in enumerate(_sources(run._latest("source_retrieval") or {}), start=1)
    }


def _verified_candidate_rows(run: WorkOrderRun) -> list[dict[str, Any]]:
    extraction = run._latest("evidence_extraction") or {}
    audit = run._latest("citation_support_audit") or {}
    audits = {
        int(item["index"]): item
        for item in audit.get("audits", [])
        if isinstance(item, dict) and isinstance(item.get("index"), int)
    }
    rows = []
    for index, candidate in enumerate(extraction.get("claims", [])):
        if not isinstance(candidate, dict):
            continue
        support = str(audits.get(index, {}).get("support_level") or "invalid_citation")
        if support == "directly_supports":
            rows.append(
                {
                    **candidate,
                    "claim_id": f"candidate-{index}",
                    "candidate_index": index,
                    "support_level": support,
                }
            )
    return rows


def _normalize_argument(result: dict[str, Any]) -> dict[str, Any]:
    """Translate adapter-local evidence references to work-order candidate indices."""
    normalized = dict(result)
    nodes = []
    for raw in normalized.get("nodes", []):
        if not isinstance(raw, dict):
            continue
        node = dict(raw)
        if "evidence_indices" not in node:
            indices = []
            for value in node.get("evidence_claim_ids", []):
                text = str(value)
                if text.startswith("candidate-"):
                    try:
                        indices.append(int(text.split("-", 1)[1]))
                    except ValueError:
                        pass
            node["evidence_indices"] = indices
        nodes.append(node)
    normalized["nodes"] = nodes
    return normalized


def _blocking_review_findings(run: WorkOrderRun) -> list[dict[str, Any]]:
    review = run._latest("hostile_review") or {}
    return [
        finding
        for panel in review.get("reviews", [])
        if isinstance(panel, dict)
        for finding in panel.get("findings", [])
        if isinstance(finding, dict) and finding.get("severity") in {"blocker", "major"}
    ]


def _source_key(source: SourceRecord) -> str:
    return (
        str(source.identifiers.get("doi") or source.url or source.title or source.source_id)
        .strip()
        .lower()
    )


def _verified_claims(result: dict[str, Any], sources: list[SourceRecord]) -> list[dict[str, Any]]:
    source_map = {source.source_id: source for source in sources}
    verified: list[dict[str, Any]] = []
    for claim in result.get("claims", []):
        if not isinstance(claim, dict):
            continue
        source = source_map.get(str(claim.get("source_id") or ""))
        quote = claim.get("exact_quote")
        if (
            source is not None
            and source.metadata_verified
            and isinstance(quote, str)
            and exact_quote_supported(quote, source)
        ):
            verified.append(claim)
    return verified


class AutonomousSWOS:
    """Drive one SWOS request through a selected provider-neutral capability broker."""

    def __init__(
        self,
        *,
        broker: CapabilityBroker | None = None,
        adapter_manifest: dict[str, Any] | None = None,
        stage_provider: Any | None = None,
        retriever: Any | None = None,
        prose_transform: Callable[[str, ResearchRequest], tuple[str, dict[str, Any]]] | None = None,
    ) -> None:
        if broker is None:
            if stage_provider is None or retriever is None:
                raise ValueError(
                    "SWOS core requires a CapabilityBroker or injected stage/retrieval bindings; "
                    "vendor selection belongs in the adapter layer"
                )
            broker = CapabilityBroker(
                stage_binding=stage_provider,
                retrieval_binding=retriever,
                prose_binding=prose_transform,
                adapter="injected-adapter",
                model_host="injected-host",
                execution_mode="injected",
                adapter_manifest=adapter_manifest,
            )
        self.broker = broker
        self.adapter_manifest = dict(
            adapter_manifest or broker.adapter_manifest or _injected_manifest(broker)
        )

    def _provenance(self, stage: str, *, model: str | None = None) -> dict[str, Any]:
        del stage
        return {
            "adapter": self.adapter_manifest.get("adapter", self.broker.adapter),
            "model_host": self.adapter_manifest.get("model_host", self.broker.model_host),
            "model": model or self.broker.model or "swos-deterministic",
            "execution_mode": self.adapter_manifest.get(
                "execution_mode", self.broker.execution_mode
            ),
        }

    def _submit(self, run: WorkOrderRun, payload: dict[str, Any], stage: str) -> None:
        result = dict(payload)
        result["provenance"] = self._provenance(stage)
        run.submit(result)

    @staticmethod
    def _review_requires_research(findings: list[dict[str, Any]]) -> bool:
        return any(finding.get("category") in REVIEW_RESEARCH_CATEGORIES for finding in findings)

    @staticmethod
    def _expansion_queries(
        topic: str,
        plan: dict[str, Any],
        *,
        needs_claims: bool,
        needs_counter: bool,
    ) -> list[str]:
        queries: list[str] = []
        if needs_counter:
            queries.extend(
                str(item) for item in plan.get("rival_theses", [])[:3] if str(item).strip()
            )
        if needs_claims:
            queries.extend(
                str(item) for item in plan.get("known_uncertainties", [])[:2] if str(item).strip()
            )
        queries.append(f"{topic} counterexamples exceptions limitations evidence")
        return queries

    def _replace_retrieval_state(
        self,
        run: WorkOrderRun,
        sources: list[SourceRecord],
        ranked: list[SourceRecord],
        rerank_record: dict[str, Any],
    ) -> None:
        retrieval = dict(run._latest("source_retrieval") or {})
        retrieval["sources"] = [source.to_dict(include_text=True) for source in sources]
        retrieval["research_expansions"] = list(run.state.get("research_expansions", []))
        retrieval["provenance"] = (run._latest("source_retrieval") or {}).get("provenance")
        run.replace_latest_submission("source_retrieval", retrieval)

        previous_rerank = run._latest("semantic_rerank") or {}
        rerank = dict(rerank_record)
        rerank["ranked_source_ids"] = [source.source_id for source in ranked]
        rerank["provenance"] = previous_rerank.get("provenance")
        run.replace_latest_submission("semantic_rerank", rerank)

    def _expand_research(
        self,
        run: WorkOrderRun,
        request: dict[str, Any],
        queries: list[str],
        *,
        reason: dict[str, bool] | None = None,
        phase: str | None = None,
        review_iteration: int | None = None,
        trigger_categories: list[str] | None = None,
        research_goal: str | None = None,
    ) -> list[SourceRecord]:
        expansions = list(run.state.get("research_expansions", []))
        if len(expansions) >= MAX_RESEARCH_EXPANSIONS:
            return []

        sources = _sources(run._latest("source_retrieval") or {})
        before_keys = {_source_key(source) for source in sources}
        expanded = self.broker.source_retrieval(str(request["topic"]), queries)
        added: list[SourceRecord] = []
        for source in expanded:
            key = _source_key(source)
            if key in before_keys:
                continue
            before_keys.add(key)
            source.injection_detected = source.injection_detected or detect_prompt_injection(
                source.text
            )
            sources.append(source)
            added.append(source)

        record: dict[str, Any] = {
            "attempt": len(expansions) + 1,
            "queries": list(queries),
            "new_sources": len(added),
        }
        if phase:
            record.update(
                {
                    "phase": phase,
                    "review_iteration": review_iteration,
                    "trigger_categories": sorted(set(trigger_categories or [])),
                    "research_goal": research_goal,
                }
            )
        else:
            record["reason"] = dict(reason or {})
        run.record_research_expansion(record)

        if not added:
            return []

        ranked, rerank_record = self.broker.semantic_rerank(
            str(request["topic"]), sources, top_k=12
        )
        for source in ranked:
            source.injection_detected = source.injection_detected or detect_prompt_injection(
                source.text
            )
        self._replace_retrieval_state(run, sources, ranked, rerank_record)
        return added

    def _rebuild_research_stages(self, run: WorkOrderRun, request: dict[str, Any]) -> None:
        ranked = _ranked_sources(run)
        evidence = self.broker.evidence_extraction(str(request["topic"]), ranked)
        previous_evidence = run._latest("evidence_extraction") or {}
        evidence["provenance"] = previous_evidence.get("provenance")
        run.replace_latest_submission("evidence_extraction", evidence)

        candidates = (run._latest("evidence_extraction") or {}).get("claims", [])
        source_map = {source.source_id: source for source in ranked}
        audit = self.broker.citation_support_audit(candidates, source_map)
        previous_audit = run._latest("citation_support_audit") or {}
        audit["provenance"] = previous_audit.get("provenance")
        run.replace_latest_submission("citation_support_audit", audit)

        plan = run._latest("research_planning") or {}
        argument = self.broker.argument_construction(
            str(request["topic"]),
            _verified_candidate_rows(run),
            list(plan.get("rival_theses") or []),
        )
        argument = _normalize_argument(argument)
        previous_argument = run._latest("argument_construction") or {}
        argument["provenance"] = previous_argument.get("provenance")
        run.replace_latest_submission("argument_construction", argument)

    def _fulfil(self, run: WorkOrderRun) -> None:
        order = run.work_order()
        if order is None:
            return
        stage = str(order["next_stage"])
        request = run.state["request"]

        if stage == "research_planning":
            self._submit(
                run,
                self.broker.research_planning(request, _scope_hint(ResearchRequest(**request))),
                stage,
            )
            return

        if stage == "source_retrieval":
            plan = run._latest("research_planning") or {}
            sources = self.broker.source_retrieval(
                str(request["topic"]), list(plan.get("queries") or [])
            )
            self._submit(
                run,
                {"sources": [source.to_dict(include_text=True) for source in sources]},
                stage,
            )
            return

        if stage == "semantic_rerank":
            ranked, record = self.broker.semantic_rerank(
                str(request["topic"]), _sources(run._latest("source_retrieval") or {})
            )
            self._submit(
                run,
                {**record, "ranked_source_ids": [source.source_id for source in ranked]},
                stage,
            )
            return

        if stage == "evidence_extraction":
            evidence = self.broker.evidence_extraction(str(request["topic"]), _ranked_sources(run))
            while len(run.state.get("research_expansions", [])) < MAX_RESEARCH_EXPANSIONS:
                sources = _sources(run._latest("source_retrieval") or {})
                verified = _verified_claims(evidence, sources)
                needs_claims = len(verified) < 5
                needs_counter = not any(
                    str(claim.get("stance") or "").lower() in {"counter", "limitation"}
                    for claim in verified
                )
                if not needs_claims and not needs_counter:
                    break
                plan = run._latest("research_planning") or {}
                queries = self._expansion_queries(
                    str(request["topic"]),
                    plan,
                    needs_claims=needs_claims,
                    needs_counter=needs_counter,
                )
                added = self._expand_research(
                    run,
                    request,
                    queries,
                    reason={
                        "fewer_than_five_verified_claims": needs_claims,
                        "missing_counter_or_limitation": needs_counter,
                    },
                )
                if not added:
                    break
                evidence = self.broker.evidence_extraction(
                    str(request["topic"]), _ranked_sources(run)
                )
            self._submit(run, evidence, stage)
            return

        if stage == "citation_support_audit":
            candidates = (run._latest("evidence_extraction") or {}).get("claims", [])
            source_map = {source.source_id: source for source in _ranked_sources(run)}
            self._submit(run, self.broker.citation_support_audit(candidates, source_map), stage)
            return

        if stage == "argument_construction":
            plan = run._latest("research_planning") or {}
            result = self.broker.argument_construction(
                str(request["topic"]),
                _verified_candidate_rows(run),
                list(plan.get("rival_theses") or []),
            )
            self._submit(run, _normalize_argument(result), stage)
            return

        if stage == "draft_generation":
            plan = run._latest("research_planning") or {}
            article = self.broker.draft_generation(
                request,
                plan,
                _verified_candidate_rows(run),
                run._latest("argument_construction") or {},
                _source_labels(run),
            )
            self._submit(run, {"article": article}, stage)
            return

        if stage == "revision":
            blocking = _blocking_review_findings(run)
            if self._review_requires_research(blocking):
                repair_plan = self.broker.research_repair_planning(str(request["topic"]), blocking)
                repair_queries = [
                    str(query).strip()
                    for query in repair_plan.get("queries", [])
                    if str(query).strip()
                ][:6]
                added = self._expand_research(
                    run,
                    request,
                    repair_queries,
                    phase="review_repair",
                    review_iteration=int(run.state.get("review_iteration", 0)),
                    trigger_categories=[str(finding.get("category")) for finding in blocking],
                    research_goal=str(repair_plan.get("research_goal") or ""),
                )
                if added:
                    self._rebuild_research_stages(run, request)
                    plan = run._latest("research_planning") or {}
                    article = self.broker.draft_generation(
                        request,
                        plan,
                        _verified_candidate_rows(run),
                        run._latest("argument_construction") or {},
                        _source_labels(run),
                    )
                    self._submit(run, {"article": article}, stage)
                    return
            article = self.broker.revision(
                run._latest_revision_or_draft() or "",
                blocking,
                _verified_candidate_rows(run),
                run._latest("argument_construction") or {},
                _source_labels(run),
            )
            self._submit(run, {"article": article}, stage)
            return

        if stage == "prose_transformation":
            article = run._latest_revision_or_draft() or ""
            final_text, evidence = self.broker.prose_transformation(
                article, ResearchRequest(**request)
            )
            self._submit(run, {**dict(evidence or {}), "candidate": final_text}, stage)
            return

        if stage == "semantic_verification":
            transform = run._latest("prose_transformation") or {}
            source = run._latest_revision_or_draft() or ""
            candidate = str(transform.get("candidate") or transform.get("final_text") or source)
            try:
                result = self.broker.semantic_verification(
                    source,
                    candidate,
                    context={"request": request, "source_markers": _source_labels(run)},
                )
            except CapabilityBrokerError:
                if candidate == source:
                    result = {
                        "status": "PASS",
                        "reason": "Candidate is byte-identical to source text.",
                        "issues": [],
                        "confidence": "high",
                    }
                else:
                    result = {
                        "status": "REVIEW",
                        "reason": "No semantic-verification implementation was available for changed text.",
                        "issues": ["semantic_verification_unavailable"],
                        "confidence": "low",
                    }
            self._submit(run, result, stage)
            return

        if stage == "hostile_review":
            verification = run._latest("semantic_verification") or {}
            transform = run._latest("prose_transformation") or {}
            source = run._latest_revision_or_draft() or ""
            candidate = transform.get("candidate") or transform.get("final_text")
            article = (
                candidate
                if verification.get("status") == "PASS" and isinstance(candidate, str)
                else source
            )
            self._submit(
                run,
                self.broker.hostile_review(
                    article,
                    _verified_candidate_rows(run),
                    run._latest("argument_construction") or {},
                    _ranked_sources(run),
                    iteration=run.state.get("review_iteration", 0) + 1,
                ),
                stage,
            )
            return

        raise RuntimeError(f"unsupported SWOS core stage: {stage}")

    @staticmethod
    def _review_required_outcome(
        run: WorkOrderRun,
        output: Path,
        reason: str,
    ) -> RunOutcome:
        article = output / "article.md"
        if not article.exists():
            article.write_text(
                "# Review required\n\nNo article was drafted or released because a SWOS capability or deterministic governance check failed.\n",
                encoding="utf-8",
            )
        failure = {
            "status": "REVIEW_REQUIRED",
            "run_id": run.state["run_id"],
            "next_stage": run.state.get("stage"),
            "reason": reason,
            "authority_boundary": "Models propose or judge. SWOS decides.",
        }
        (output / "run-failure.json").write_text(
            json.dumps(failure, indent=2) + "\n", encoding="utf-8"
        )
        return RunOutcome(
            run_id=run.state["run_id"],
            work_id="work-unfinalised",
            status="REVIEW_REQUIRED",
            output_dir=str(output),
            article_word_count=0,
            human_interventions=0,
            normal_user_questions_asked=0,
            unresolved_questions=[reason],
            blocking_reasons=[reason],
        )

    def run(self, request: ResearchRequest, output_dir: str | Path) -> RunOutcome:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="swos-live-") as run_root:
            run = WorkOrderRun.start(
                request=request.to_dict(),
                adapter_manifest=self.adapter_manifest,
                root=run_root,
            )
            try:
                while run.status()["status"] == "ACTIVE":
                    self._fulfil(run)
            except (WorkOrderError, CapabilityBrokerError, ValueError, TypeError) as exc:
                return self._review_required_outcome(run, output, str(exc))

            if run.status()["status"] != "READY_TO_FINALISE":
                findings = list(run.state.get("blocking_findings") or [])
                reason = (
                    "; ".join(str(item.get("description") or item) for item in findings)
                    if findings
                    else "SWOS work-order run did not reach the final governance gate."
                )
                return self._review_required_outcome(run, output, reason)

            # The bundle is emitted for replay/reproducibility, not used as the live mechanism.
            run.export_host_bundle(output / "host-bundle.json")
            return finalize_work_order_run(run, output)
