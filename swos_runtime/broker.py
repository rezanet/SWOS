"""SWOS capability broker.

The broker is the migration boundary between SWOS core capability names and
adapter/provider implementations. Core code asks for a SWOS capability; the
broker delegates to the selected adapter and records the frozen contract that
was satisfied. Vendor identity is provenance, never scholarly validity.
"""

from __future__ import annotations

from typing import Any, Callable

from .capabilities import CAPABILITY_CONTRACTS, CAPABILITY_CONTRACT_SET


class CapabilityBrokerError(RuntimeError):
    """Raised when a selected binding cannot fulfil a SWOS capability."""


class CapabilityBroker:
    """Provider-neutral facade over stage, retrieval and prose bindings."""

    def __init__(
        self,
        *,
        stage_binding: Any,
        retrieval_binding: Any,
        prose_binding: Callable[[str, Any], tuple[str, dict[str, Any]]] | None = None,
        adapter: str = "injected-adapter",
        model_host: str = "unknown-host",
        execution_mode: str = "injected",
    ) -> None:
        self.stage_binding = stage_binding
        self.retrieval_binding = retrieval_binding
        self.prose_binding = prose_binding
        self.adapter = adapter
        self.model_host = model_host
        self.execution_mode = execution_mode
        self.events: list[dict[str, Any]] = []

    def _event(self, capability: str, **extra: Any) -> dict[str, Any]:
        record = {
            "capability": capability,
            "contract": CAPABILITY_CONTRACTS[capability],
            "contract_set": CAPABILITY_CONTRACT_SET,
            "executed": True,
            "adapter": self.adapter,
            "model_host": self.model_host,
            "execution_mode": self.execution_mode,
        }
        record.update(extra)
        self.events.append(record)
        return record

    def research_planning(self, request: dict[str, Any], scope_hint: str) -> dict[str, Any]:
        result = self.stage_binding.plan(request, scope_hint)
        self._event("research_planning")
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
        ranked, raw = self.stage_binding.rerank(topic, sources, top_k=top_k)
        record = dict(raw or {})
        record.update(
            self._event(
                "semantic_rerank",
                model=getattr(self.stage_binding, "model", None),
                top_k=top_k,
            )
        )
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
        method = getattr(self.stage_binding, "plan_review_repair", None)
        if method is None:
            raise CapabilityBrokerError(
                "selected adapter cannot perform review-driven research planning"
            )
        result = method(topic, findings)
        self._event("research_planning", phase="review_repair")
        return result

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
        record.setdefault("capability", "prose_transformation")
        record.setdefault("contract", CAPABILITY_CONTRACTS["prose_transformation"])
        record.setdefault("contract_set", CAPABILITY_CONTRACT_SET)
        record.setdefault("executed", True)
        record.setdefault("adapter", self.adapter)
        record.setdefault("model_host", self.model_host)
        record.setdefault("execution_mode", self.execution_mode)
        self.events.append(dict(record))
        return final_text, record
