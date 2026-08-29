"""Canonical SWOS host-bundle replay/interchange adapter.

A host bundle is NOT the primary live subscription execution mechanism. Live
hosts use ``swos.work-orders.v1``. SWOS may then emit a canonical host bundle as
a replay, interchange, debugging and reproducibility artefact so a completed run
can be inspected or replayed later without the original host.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .models import SourceRecord

HOST_BUNDLE_ROLE = "replay_interchange_debug_reproducibility"


class HostBundleError(ValueError):
    """Raised when a replay/interchange bundle is incomplete or inconsistent."""


def load_host_bundle(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HostBundleError("host bundle root must be an object")
    if not isinstance(payload.get("host"), dict):
        raise HostBundleError("host bundle must declare host metadata")
    if not isinstance(payload.get("sources"), list):
        raise HostBundleError("host bundle must contain a sources array")
    if not isinstance(payload.get("stages"), dict):
        raise HostBundleError("host bundle must contain a stages object")
    payload.setdefault("bundle_role", HOST_BUNDLE_ROLE)
    return payload


class HostBundleRetriever:
    """Replay stored source snapshots through the retrieval capability seam."""

    def __init__(self, bundle: dict[str, Any]) -> None:
        self.bundle = bundle
        self.events: list[dict[str, Any]] = []

    def retrieve(
        self, topic: str, queries: list[str], *, max_sources: int = 14
    ) -> list[SourceRecord]:
        del topic
        records: list[SourceRecord] = []
        for raw in self.bundle.get("sources", [])[:max_sources]:
            if not isinstance(raw, dict):
                raise HostBundleError("every host-bundle source must be an object")
            records.append(SourceRecord(**copy.deepcopy(raw)))
        self.events.append(
            {
                "provider": "host_bundle_replay",
                "queries": [str(query) for query in queries],
                "source_count": len(records),
                "network_used_by_runtime": False,
                "bundle_role": self.bundle.get("bundle_role", HOST_BUNDLE_ROLE),
            }
        )
        return records


class HostBundleStageProvider:
    """Replay recorded scholarly stage outputs through adapter interfaces."""

    def __init__(self, bundle: dict[str, Any]) -> None:
        self.bundle = bundle
        host = bundle.get("host", {})
        self.model = str(host.get("model") or host.get("model_host") or "recorded-host-model")
        self.review_model = self.model
        self.blind_review_supported = bool(host.get("blind_review_supported", False))
        self.execution_metadata = {
            "execution_mode": "replay",
            "original_execution_mode": str(
                host.get("execution_mode") or "host_native_subscription"
            ),
            "adapter": "replay",
            "original_adapter": str(host.get("adapter") or "unknown-host-adapter"),
            "model_host": str(host.get("model_host") or "unknown-host"),
            "model": self.model,
            "api_key_used": False,
            "paid_api_calls": 0,
            "original_api_key_used": bool(host.get("api_key_used", False)),
            "original_paid_api_calls": int(host.get("paid_api_calls", 0)),
            "review_mode": str(host.get("review_mode") or "recorded"),
            "independence": str(host.get("independence") or "unknown"),
            "independence_limitations": list(host.get("independence_limitations") or []),
            "blind_review_supported": self.blind_review_supported,
            "bundle_role": bundle.get("bundle_role", HOST_BUNDLE_ROLE),
        }
        self.calls: list[dict[str, Any]] = []
        self._review_index = 0
        self._repair_index = 0
        self._revision_index = 0

    def _stage(self, name: str) -> Any:
        stages = self.bundle.get("stages", {})
        if name not in stages:
            raise HostBundleError(f"host bundle is missing required stage: {name}")
        value = copy.deepcopy(stages[name])
        self.calls.append(
            {
                "stage": name,
                "model": self.model,
                "execution_mode": "replay",
                "response_id": None,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "cost_estimate_usd": 0.0,
                "elapsed_seconds": 0.0,
            }
        )
        return value

    def plan(self, request: dict[str, Any], scope_hint: str) -> dict[str, Any]:
        del request, scope_hint
        value = self._stage("research_plan")
        if not isinstance(value, dict):
            raise HostBundleError("research_plan must be an object")
        return value

    def rerank(
        self, topic: str, sources: list[SourceRecord], *, top_k: int = 10
    ) -> tuple[list[SourceRecord], dict[str, Any]]:
        del topic
        raw = self._stage("rerank_scores")
        if not isinstance(raw, list):
            raise HostBundleError("rerank_scores must be an array")
        scores = {
            str(item.get("source_id")): float(item.get("score", 0))
            for item in raw
            if isinstance(item, dict)
        }
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
            "implementation": "host_bundle_replay",
            "capability": "semantic_rerank",
            "contract": "swos.semantic-rerank.v1",
            "contract_passed": True,
            "executed": True,
            "execution_mode": "replay",
            "model": self.model,
            "top_k": top_k,
            "scores": raw,
        }

    def build_evidence(self, topic: str, sources: list[SourceRecord]) -> dict[str, Any]:
        del topic, sources
        value = self._stage("evidence_build")
        if not isinstance(value, dict):
            raise HostBundleError("evidence_build must be an object")
        return value

    def audit_evidence(
        self, candidates: list[dict[str, Any]], sources: dict[str, SourceRecord]
    ) -> dict[str, Any]:
        del candidates, sources
        value = self._stage("evidence_audit")
        if not isinstance(value, dict):
            raise HostBundleError("evidence_audit must be an object")
        return value

    def build_argument(
        self,
        topic: str,
        evidence_rows: list[dict[str, Any]],
        rival_theses: list[str],
    ) -> dict[str, Any]:
        del topic, evidence_rows, rival_theses
        value = self._stage("argument_build")
        if not isinstance(value, dict):
            raise HostBundleError("argument_build must be an object")
        return value

    def draft(
        self,
        request: dict[str, Any],
        plan: dict[str, Any],
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        source_labels: dict[str, str],
    ) -> str:
        del request, plan, evidence_rows, argument, source_labels
        value = self._stage("draft")
        if not isinstance(value, str) or not value.strip():
            raise HostBundleError("draft must be non-empty text")
        return value.strip()

    def review(
        self,
        article: str,
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        sources: list[SourceRecord],
        *,
        iteration: int,
    ) -> dict[str, Any]:
        del article, evidence_rows, argument, sources, iteration
        reviews = self.bundle.get("stages", {}).get("reviews")
        if not isinstance(reviews, list) or self._review_index >= len(reviews):
            raise HostBundleError("host bundle has no review result for this iteration")
        value = copy.deepcopy(reviews[self._review_index])
        self._review_index += 1
        self.calls.append(
            {
                "stage": f"review_{self._review_index}",
                "model": self.model,
                "execution_mode": "replay",
                "response_id": None,
                "cost_estimate_usd": 0.0,
                "elapsed_seconds": 0.0,
            }
        )
        if not isinstance(value, dict):
            raise HostBundleError("each review result must be an object")
        return value

    def plan_review_repair(self, topic: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
        del topic, findings
        plans = self.bundle.get("stages", {}).get("review_repair_plans", [])
        if not isinstance(plans, list) or self._repair_index >= len(plans):
            raise HostBundleError("host bundle has no research-repair plan for this iteration")
        value = copy.deepcopy(plans[self._repair_index])
        self._repair_index += 1
        if not isinstance(value, dict):
            raise HostBundleError("review repair plan must be an object")
        return value

    def revise(
        self,
        article: str,
        findings: list[dict[str, Any]],
        evidence_rows: list[dict[str, Any]],
        argument: dict[str, Any],
        source_labels: dict[str, str],
    ) -> str:
        del article, findings, evidence_rows, argument, source_labels
        revisions = self.bundle.get("stages", {}).get("revisions", [])
        if not isinstance(revisions, list) or self._revision_index >= len(revisions):
            raise HostBundleError("host bundle has no revision text for this iteration")
        value = copy.deepcopy(revisions[self._revision_index])
        self._revision_index += 1
        if not isinstance(value, str) or not value.strip():
            raise HostBundleError("revision must be non-empty text")
        return value.strip()

    def semantic_verify(
        self,
        source: str,
        candidate: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        del source, candidate, context
        value = self._stage("semantic_verification")
        if not isinstance(value, dict):
            raise HostBundleError("semantic_verification must be an object")
        return value


def host_prose_transform(bundle: dict[str, Any]):
    """Build a governed replay prose transform from stored Prose evidence."""

    def transform(article: str, request: Any) -> tuple[str, dict[str, Any]]:
        del request
        prose = copy.deepcopy(bundle.get("prose", {}))
        if not isinstance(prose, dict):
            raise HostBundleError("prose record must be an object")
        safe = bool(prose.get("safe_for_automatic_use", False))
        changed = prose.get("final_text")
        if changed is not None and (not isinstance(changed, str) or not changed.strip()):
            raise HostBundleError("prose final_text must be non-empty when supplied")
        if changed is not None and not safe:
            final_text = article
            used_source_fallback = True
        else:
            final_text = changed.strip() if isinstance(changed, str) else article
            used_source_fallback = False
        return final_text, {
            "invoked": True,
            "adapter_mode": "host_bundle_replay",
            "bundle_role": bundle.get("bundle_role", HOST_BUNDLE_ROLE),
            "all_changed_text_safe": safe or used_source_fallback,
            "chunks": [
                {
                    "safe_for_automatic_use": safe,
                    "used_source_fallback": used_source_fallback,
                    "changed": final_text != article,
                    "model_host": bundle.get("host", {}).get("model_host"),
                }
            ],
        }

    return transform
