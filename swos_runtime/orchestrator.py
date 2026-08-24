"""Provider-neutral Autonomous SWOS core orchestrator.

The core owns the scholarly state machine and deterministic governance. It knows
SWOS capabilities, contracts and canonical instructions; it does not know vendor
SDKs, model product names or provider-specific prompt behaviour.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable

from .broker import CapabilityBroker, CapabilityBrokerError
from .capabilities import CAPABILITY_CONTRACT_SET, CAPABILITY_CONTRACTS
from .finalizer import finalize_work_order_run
from .models import ResearchRequest, RunOutcome, SourceRecord
from .work_orders import BASE_STAGE_SEQUENCE, WorkOrderRun

RUNTIME_VERSION = "0.2.0"


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
        name: {
            "level": "native",
            "contract": contract,
            "assurance": [],
        }
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
    values = payload.get("sources", [])
    return [SourceRecord(**item) for item in values if isinstance(item, dict)]


def _ranked_sources(run: WorkOrderRun) -> list[SourceRecord]:
    retrieval = run._latest("source_retrieval") or {}
    sources = _sources(retrieval)
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
    # Labels are deterministic from canonical retrieval order, not model ranking.
    retrieval = run._latest("source_retrieval") or {}
    return {
        source.source_id: f"S{index}"
        for index, source in enumerate(_sources(retrieval), start=1)
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
        if support != "directly_supports":
            continue
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

    def _fulfil(self, run: WorkOrderRun) -> None:
        order = run.work_order()
        if order is None:
            return
        stage = str(order["next_stage"])
        request = run.state["request"]

        if stage == "research_planning":
            result = self.broker.research_planning(request, _scope_hint(ResearchRequest(**request)))
            self._submit(run, result, stage)
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
            payload = dict(record)
            payload["ranked_source_ids"] = [source.source_id for source in ranked]
            self._submit(run, payload, stage)
            return

        if stage == "evidence_extraction":
            result = self.broker.evidence_extraction(
                str(request["topic"]), _ranked_sources(run)
            )
            self._submit(run, result, stage)
            return

        if stage == "citation_support_audit":
            candidates = (run._latest("evidence_extraction") or {}).get("claims", [])
            source_map = {source.source_id: source for source in _ranked_sources(run)}
            result = self.broker.citation_support_audit(candidates, source_map)
            self._submit(run, result, stage)
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
            result = self.broker.draft_generation(
                request,
                plan,
                _verified_candidate_rows(run),
                run._latest("argument_construction") or {},
                _source_labels(run),
            )
            self._submit(run, {"article": result}, stage)
            return

        if stage == "revision":
            article = run._latest_revision_or_draft() or ""
            result = self.broker.revision(
                article,
                _blocking_review_findings(run),
                _verified_candidate_rows(run),
                run._latest("argument_construction") or {},
                _source_labels(run),
            )
            self._submit(run, {"article": result}, stage)
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
            article = candidate if verification.get("status") == "PASS" and isinstance(candidate, str) else source
            result = self.broker.hostile_review(
                article,
                _verified_candidate_rows(run),
                run._latest("argument_construction") or {},
                _ranked_sources(run),
                iteration=run.state.get("review_iteration", 0) + 1,
            )
            self._submit(run, result, stage)
            return

        raise RuntimeError(f"unsupported SWOS core stage: {stage}")

    def run(self, request: ResearchRequest, output_dir: str | Path) -> RunOutcome:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="swos-live-") as run_root:
            run = WorkOrderRun.start(
                request=request.to_dict(),
                adapter_manifest=self.adapter_manifest,
                root=run_root,
            )
            while run.status()["status"] == "ACTIVE":
                self._fulfil(run)
            if run.status()["status"] != "READY_TO_FINALISE":
                # The neutral finalizer intentionally requires a completed review gate.
                return RunOutcome(
                    run_id=run.state["run_id"],
                    work_id="work-unfinalised",
                    status=run.status()["status"],
                    output_dir=str(output),
                    article_word_count=0,
                    human_interventions=0,
                    normal_user_questions_asked=0,
                    unresolved_questions=["SWOS work-order run did not reach finalisation."],
                    blocking_reasons=list(run.state.get("blocking_findings") or []),
                )
            # The bundle is a reproducibility artefact, not the execution mechanism.
            run.export_host_bundle(output / "host-bundle.json")
            return finalize_work_order_run(run, output)
