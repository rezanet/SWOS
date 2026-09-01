"""SWOS capability broker.

SWOS core asks for named capabilities and frozen contracts. Adapters implement
those capabilities for a particular host, API, replay bundle or local model.
Vendor identity is provenance, never scholarly validity.
"""

from __future__ import annotations

from typing import Any, Callable

from .capabilities import CAPABILITY_CONTRACT_SET, CAPABILITY_CONTRACTS
from .instructions import instruction_record


class CapabilityBrokerError(RuntimeError):
    """Raised when a selected binding cannot fulfil a SWOS capability."""


JUDGEMENT_TYPES = {
    "semantic_rerank": "relevance_ranking",
    "citation_support_audit": "citation_support",
    "argument_construction": "argument_proposal",
    "semantic_verification": "semantic_preservation",
    "hostile_review": "scholarly_review",
}


class CapabilityBroker:
    """Provider-neutral facade over stage, retrieval and prose bindings."""

    def __init__(
        self,
        *,
        stage_binding: Any,
        retrieval_binding: Any,
        rerank_binding: Any | None = None,
        prose_binding: Callable[[str, Any], tuple[str, dict[str, Any]]] | None = None,
        adapter: str = "injected-adapter",
        model_host: str = "unknown-host",
        execution_mode: str = "injected",
        adapter_manifest: dict[str, Any] | None = None,
        discipline_critic: Any | None = None,
    ) -> None:
        self.stage_binding = stage_binding
        self.retrieval_binding = retrieval_binding
        self.rerank_binding = rerank_binding or stage_binding
        self.prose_binding = prose_binding
        self.adapter_manifest = dict(adapter_manifest or {})
        self.adapter = str(self.adapter_manifest.get("adapter") or adapter)
        self.model_host = str(self.adapter_manifest.get("model_host") or model_host)
        self.execution_mode = str(self.adapter_manifest.get("execution_mode") or execution_mode)
        self.discipline_critic = discipline_critic
        self.events: list[dict[str, Any]] = []

    @property
    def model(self) -> str | None:
        value = getattr(self.stage_binding, "model", None)
        return str(value) if value is not None else None

    @property
    def provider_calls(self) -> list[Any]:
        return list(getattr(self.stage_binding, "calls", []))

    @property
    def retrieval_events(self) -> list[dict[str, Any]]:
        return list(getattr(self.retrieval_binding, "events", []))

    def capability_declaration(self, capability: str) -> dict[str, Any]:
        declared = self.adapter_manifest.get("capabilities", {}).get(capability)
        return dict(declared) if isinstance(declared, dict) else {}

    def review_assurance(self, capability: str = "hostile_review") -> dict[str, Any]:
        declaration = self.capability_declaration(capability)
        independence = str(declaration.get("independence") or "unknown")
        return {
            "review_mode": str(declaration.get("review_mode") or "unspecified"),
            "independence": independence,
            "blind_review_supported": bool(declaration.get("blind_review_supported", False)),
            "independence_limitations": list(declaration.get("independence_limitations") or []),
        }

    def provenance(
        self, capability: str, *, instruction_stage: str | None = None
    ) -> dict[str, Any]:
        instruction = instruction_record(instruction_stage or capability)
        declaration = self.capability_declaration(capability)
        return {
            "adapter": self.adapter,
            "model_host": self.model_host,
            "model": self.model or "unreported-model",
            "execution_mode": self.execution_mode,
            "capability": capability,
            "contract": CAPABILITY_CONTRACTS[capability],
            "instruction_id": instruction["instruction_id"],
            "instruction_sha256": instruction["sha256"],
            "assurance": list(declaration.get("assurance") or []),
        }

    def _event(
        self,
        capability: str,
        *,
        instruction_stage: str | None = None,
        confidence: str = "unreported",
        **extra: Any,
    ) -> dict[str, Any]:
        declaration = self.capability_declaration(capability)
        instruction = instruction_record(instruction_stage or capability)
        record = {
            "capability": capability,
            "contract": CAPABILITY_CONTRACTS[capability],
            "contract_set": CAPABILITY_CONTRACT_SET,
            "contract_passed": True,
            "executed": True,
            "adapter": self.adapter,
            "model_host": self.model_host,
            "model": self.model,
            "execution_mode": self.execution_mode,
            "instruction_id": instruction["instruction_id"],
            "instruction_sha256": instruction["sha256"],
        }
        judgement_type = JUDGEMENT_TYPES.get(capability)
        if judgement_type:
            assurance = self.review_assurance(capability)
            record["judgement"] = {
                "judgement_type": judgement_type,
                "adapter": self.adapter,
                "host": self.model_host,
                "model": self.model or "unreported-model",
                "confidence": confidence,
                "assurance": list(declaration.get("assurance") or []),
                "independence": assurance["independence"],
                "independence_limitations": assurance["independence_limitations"],
                "review_mode": assurance["review_mode"],
                "blind_review_supported": assurance["blind_review_supported"],
            }
        record.update(extra)
        self.events.append(record)
        return record

    def research_planning(
        self,
        request: dict[str, Any],
        scope_hint: str,
        *,
        repair_findings: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if repair_findings is None:
            result = self.stage_binding.plan(request, scope_hint)
            self._event("research_planning")
            return result
        method = getattr(self.stage_binding, "plan_review_repair", None)
        if method is None:
            raise CapabilityBrokerError(
                "selected adapter cannot perform review-driven research planning"
            )
        topic = str(request.get("topic") or "")
        result = method(topic, repair_findings)
        self._event(
            "research_planning",
            instruction_stage="research_repair_planning",
            phase="review_repair",
        )
        return result

    def source_retrieval(
        self, topic: str, queries: list[str], *, max_sources: int | None = None
    ) -> list[Any]:
        if max_sources is None:
            result = self.retrieval_binding.retrieve(topic, queries)
        else:
            try:
                result = self.retrieval_binding.retrieve(topic, queries, max_sources=max_sources)
            except TypeError:
                result = self.retrieval_binding.retrieve(topic, queries)
        self._event("source_retrieval", source_count=len(result))
        return result

    def semantic_rerank(
        self, topic: str, sources: list[Any], *, top_k: int = 10
    ) -> tuple[list[Any], dict[str, Any]]:
        ranked, raw = self.rerank_binding.rerank(topic, sources, top_k=top_k)
        record = dict(raw or {})
        # Adapter implementation details may remain for debugging, but SWOS validity
        # keys are capability + frozen contract, never method/provider identity.
        event = self._event("semantic_rerank", top_k=top_k)
        reranker_model = record.get("reranker_model")
        if reranker_model:
            event["model"] = str(reranker_model)
            if isinstance(event.get("judgement"), dict):
                event["judgement"]["model"] = str(reranker_model)
        record.update(event)
        return ranked, record

    def evidence_extraction(self, topic: str, sources: list[Any]) -> dict[str, Any]:
        result = self.stage_binding.build_evidence(topic, sources)
        self._event("evidence_extraction")
        return result

    def citation_support_audit(
        self, candidates: list[dict[str, Any]], sources: dict[str, Any]
    ) -> dict[str, Any]:
        result = self.stage_binding.audit_evidence(candidates, sources)
        self._event("citation_support_audit")
        return result

    def argument_construction(
        self,
        topic: str,
        evidence_rows: list[dict[str, Any]],
        rival_theses: list[str],
    ) -> dict[str, Any]:
        result = self.stage_binding.build_argument(topic, evidence_rows, rival_theses)
        self._event("argument_construction")
        return result

    def draft_generation(
        self,
        request: dict[str, Any],
        plan: dict[str, Any],
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        source_labels: dict[str, str],
    ) -> str:
        result = self.stage_binding.draft(request, plan, evidence_rows, argument, source_labels)
        self._event("draft_generation")
        return result

    def hostile_review(
        self,
        article: str,
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        sources: list[Any],
        *,
        iteration: int,
    ) -> dict[str, Any]:
        result = self.stage_binding.review(
            article,
            evidence_rows,
            argument,
            sources,
            iteration=iteration,
        )
        self._event("hostile_review", iteration=iteration)
        return result

    def research_repair_planning(
        self, topic: str, findings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self.research_planning(
            {"topic": topic},
            "review-driven repair",
            repair_findings=findings,
        )

    def revision(
        self,
        article: str,
        findings: list[dict[str, Any]],
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        source_labels: dict[str, str],
    ) -> str:
        result = self.stage_binding.revise(
            article, findings, evidence_rows, argument, source_labels
        )
        self._event("revision")
        return result

    def prose_transformation(self, article: str, request: Any) -> tuple[str, dict[str, Any]]:
        if self.prose_binding is None:
            raise CapabilityBrokerError("selected adapter does not provide prose_transformation")
        final_text, evidence = self.prose_binding(article, request)
        record = dict(evidence or {})
        record.update(self._event("prose_transformation"))
        return final_text, record

    def semantic_verification(
        self,
        source: str,
        candidate: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        method = getattr(self.stage_binding, "semantic_verify", None)
        if method is None:
            raise CapabilityBrokerError("selected adapter does not provide semantic_verification")
        result = method(source, candidate, context or {})
        if not isinstance(result, dict):
            raise CapabilityBrokerError("semantic_verification must return an object")
        self._event("semantic_verification")
        return result

    def discipline_critique(
        self,
        *,
        discipline: Any,
        research_plan: dict[str, Any],
        evidence_matrix: dict[str, Any],
        draft: dict[str, Any],
        critic: Any | None = None,
    ) -> Any:
        """Run a SWOS-owned critic; a provider cannot supply the admission verdict."""

        selected = critic or self.discipline_critic
        if selected is None or not hasattr(selected, "critique"):
            raise CapabilityBrokerError("a governed discipline critic is required")
        result = selected.critique(
            discipline=discipline,
            research_plan=research_plan,
            evidence_matrix=evidence_matrix,
            draft=draft,
        )
        self.events.append(
            {
                "capability": "discipline_critique",
                "contract": "swos.discipline-critique.v2",
                "contract_passed": True,
                "executed": True,
                "provider_owned_admission": False,
                "mandatory_failures": list(getattr(result, "mandatory_failures", [])),
                "review_state": getattr(result, "review_state", "machine_proposed"),
            }
        )
        return result
