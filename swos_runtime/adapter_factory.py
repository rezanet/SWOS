"""Adapter-layer factories for selecting concrete SWOS capability workers.

Vendor SDKs and replay transports belong here, outside SWOS core. The factory
returns a CapabilityBroker plus the effective capability manifest for the
composed execution stack.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .broker import CapabilityBroker
from .host_bundle import (
    HostBundleRetriever,
    HostBundleStageProvider,
    host_prose_transform,
    load_host_bundle,
)
from .llm import OpenAIStageProvider
from .retrieval import PublicWebRetriever


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"adapter manifest must be an object: {path}")
    return payload


def _openai_prose_binding():
    """Build the OpenAI-backed SWOS Prose transport outside core orchestration."""
    from swos_prose.modes import SUPPORTED_PRESETS
    from swos_prose.providers.openai_responses import OpenAIResponsesSemanticVerifierProvider
    from swos_prose.providers.openai_rewrite import OpenAIResponsesRewriteProvider
    from swos_prose.rewrite import edit_text

    rewrite_provider = OpenAIResponsesRewriteProvider()
    verifier = OpenAIResponsesSemanticVerifierProvider()

    def transform(article: str, request: Any) -> tuple[str, dict[str, Any]]:
        preset = request.style if getattr(request, "style", None) in SUPPORTED_PRESETS else None
        try:
            result = edit_text(
                source=article,
                rewrite_provider=rewrite_provider,
                verifier_provider=verifier,
                assurance="strict",
                mode="polish",
                preset=preset,
                run_diagnostics=True,
            )
            record = result.to_dict()
            safe = bool(record.get("safe_for_automatic_use", False))
            final_text = result.final_text if safe else article
            return final_text, {
                "invoked": True,
                "safe_for_automatic_use": safe,
                "used_source_fallback": not safe,
                "all_changed_text_safe": safe or final_text == article,
                "prose_record": record,
            }
        except Exception as exc:
            return article, {
                "invoked": True,
                "safe_for_automatic_use": False,
                "used_source_fallback": True,
                "all_changed_text_safe": True,
                "error": str(exc),
            }

    return transform


def build_openai_api_broker() -> tuple[CapabilityBroker, dict[str, Any]]:
    """Compose OpenAI model capabilities with SWOS public-web retrieval."""
    manifest = _load_manifest(_repo_root() / "adapters" / "openai-api" / "capabilities-v1.json")
    manifest = copy.deepcopy(manifest)
    # The selected execution stack includes a retrieval binding, so the effective
    # adapter presented to SWOS satisfies source_retrieval even though the model
    # API alone does not.
    manifest["adapter"] = "openai-api+public-web"
    manifest["capabilities"]["source_retrieval"] = {
        "level": "full",
        "contract": "swos.source-retrieval.v1",
        "assurance": ["network_retrieval", "source_identity", "metadata_provenance"],
    }
    stage = OpenAIStageProvider()
    retriever = PublicWebRetriever()
    broker = CapabilityBroker(
        stage_binding=stage,
        retrieval_binding=retriever,
        prose_binding=_openai_prose_binding(),
        adapter_manifest=manifest,
    )
    return broker, manifest


def build_replay_broker(path: str | Path) -> tuple[CapabilityBroker, dict[str, Any]]:
    """Build a replay-only broker from a canonical host bundle."""
    bundle = load_host_bundle(path)
    stage = HostBundleStageProvider(bundle)
    retriever = HostBundleRetriever(bundle)
    review = {
        "review_mode": stage.execution_metadata.get("review_mode", "recorded"),
        "independence": stage.execution_metadata.get("independence", "unknown"),
        "blind_review_supported": stage.execution_metadata.get("blind_review_supported", False),
        "independence_limitations": stage.execution_metadata.get("independence_limitations", []),
    }
    capabilities = {
        "research_planning": {"level": "native", "contract": "swos.research-planning.v1"},
        "source_retrieval": {"level": "native", "contract": "swos.source-retrieval.v1"},
        "semantic_rerank": {"level": "native", "contract": "swos.semantic-rerank.v1"},
        "evidence_extraction": {"level": "native", "contract": "swos.evidence-extraction.v1"},
        "citation_support_audit": {
            "level": "native",
            "contract": "swos.citation-support-audit.v1",
            **review,
        },
        "argument_construction": {
            "level": "native",
            "contract": "swos.argument-construction.v1",
        },
        "draft_generation": {"level": "native", "contract": "swos.draft-generation.v1"},
        "semantic_verification": {
            "level": "native",
            "contract": "swos.semantic-verification.v1",
        },
        "hostile_review": {
            "level": "native",
            "contract": "swos.hostile-review.v1",
            **review,
        },
        "revision": {"level": "native", "contract": "swos.revision.v1"},
        "prose_transformation": {
            "level": "native",
            "contract": "swos.prose-transformation.v1",
        },
    }
    manifest = {
        "contract_set": "swos.capabilities.v1",
        "adapter": "replay",
        "model_host": stage.execution_metadata.get("model_host", "recorded-host"),
        "execution_mode": "replay",
        "api_key_used": False,
        "paid_api_calls": 0,
        "capabilities": capabilities,
        "replay_provenance": stage.execution_metadata,
    }
    broker = CapabilityBroker(
        stage_binding=stage,
        retrieval_binding=retriever,
        prose_binding=host_prose_transform(bundle),
        adapter_manifest=manifest,
    )
    return broker, manifest
