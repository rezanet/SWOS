"""Provider-neutral bounded 2D image analysis and promotion guardrails."""

from __future__ import annotations

import base64
import hashlib
import math
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence

from .media import MediaAssetRecord, RegionSelector, validate_media_asset
from .models import canonical_digest, utc_timestamp

ANALYSIS_STATUSES = frozenset({"complete", "partial", "insufficient", "denied", "error"})
DETERMINISTIC_TIMESTAMP = "1970-01-01T00:00:00+00:00"
PROMOTION_BOOTSTRAP_RESAMPLES = 10_000


def _asset_digest(asset: Any) -> str:
    return str(
        asset.byte_digest
        if hasattr(asset, "byte_digest")
        else _mapping(asset).get("byte_digest") or ""
    )


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(vars(value))


@dataclass(frozen=True)
class ImageAnalysisRequest:
    work_id: str
    run_id: str
    object_id: str
    assets: tuple[MediaAssetRecord, ...]
    target_questions: tuple[str, ...]
    allowed_actions: tuple[str, ...] = ("analyse",)
    discipline: str = "art_history"
    ontology_binding: Mapping[str, Any] = field(default_factory=dict)
    resource_limits: Mapping[str, Any] = field(
        default_factory=lambda: {"max_assets": 8, "max_observations": 64, "max_seconds": 60}
    )
    provider_policy: Mapping[str, Any] = field(default_factory=dict)
    request_digest: str = ""
    captured_bytes: Mapping[str, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "assets", tuple(self.assets))
        object.__setattr__(self, "target_questions", tuple(self.target_questions))
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        object.__setattr__(self, "ontology_binding", dict(self.ontology_binding))
        object.__setattr__(self, "resource_limits", dict(self.resource_limits))
        object.__setattr__(self, "provider_policy", dict(self.provider_policy))
        captured = {}
        for asset_id, value in self.captured_bytes.items():
            if not isinstance(value, (bytes, bytearray)):
                raise ValueError("captured image content must be bytes")
            captured[str(asset_id)] = bytes(value)
        object.__setattr__(self, "captured_bytes", captured)
        if not self.request_digest:
            object.__setattr__(self, "request_digest", canonical_digest(self._unsigned_dict()))

    def _unsigned_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "run_id": self.run_id,
            "object_id": self.object_id,
            "assets": [_asset_digest(asset) for asset in self.assets],
            "asset_rights": {
                str(getattr(asset, "asset_id", index)): canonical_digest(
                    getattr(asset, "rights", {})
                )
                for index, asset in enumerate(self.assets)
            },
            "target_questions": list(self.target_questions),
            "allowed_actions": list(self.allowed_actions),
            "discipline": self.discipline,
            "ontology_binding": dict(self.ontology_binding),
            "resource_limits": dict(self.resource_limits),
            "provider_policy": dict(self.provider_policy),
            "captured_asset_digests": {
                asset_id: hashlib.sha256(value).hexdigest()
                for asset_id, value in sorted(self.captured_bytes.items())
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._unsigned_dict(),
            "asset_ids": [asset.asset_id for asset in self.assets],
            "request_digest": self.request_digest,
        }


@dataclass(frozen=True)
class VisualObservation:
    observation_id: str
    object_id: str
    asset_id: str
    asset_digest: str
    description: str
    origin: str
    selector: RegionSelector | None = None
    supports_claim_ids: tuple[str, ...] = ()
    provider: str = ""
    model: str = ""
    confidence: float | None = None
    uncertainty: tuple[str, ...] = ()
    view_limitations: tuple[str, ...] = ()
    review_status: str = "machine_only"
    epg_activity_id: str | None = None
    modality: str = "image"
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "supports_claim_ids", tuple(self.supports_claim_ids))
        object.__setattr__(self, "uncertainty", tuple(self.uncertainty))
        object.__setattr__(self, "view_limitations", tuple(self.view_limitations))
        object.__setattr__(self, "provenance", dict(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        selector = (
            self.selector.to_dict()
            if hasattr(self.selector, "to_dict")
            else (dict(self.selector) if isinstance(self.selector, Mapping) else None)
        )
        return {
            "observation_id": self.observation_id,
            "object_id": self.object_id,
            "asset_id": self.asset_id,
            "asset_digest": self.asset_digest,
            "description": self.description,
            "origin": self.origin,
            "selector": selector,
            "supports_claim_ids": list(self.supports_claim_ids),
            "provider": self.provider,
            "model": self.model,
            "confidence": self.confidence,
            "uncertainty": list(self.uncertainty),
            "view_limitations": list(self.view_limitations),
            "review_status": self.review_status,
            "epg_activity_id": self.epg_activity_id,
            "modality": self.modality,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class VisualInterpretation:
    interpretation_id: str
    object_id: str
    observation_ids: tuple[str, ...]
    statement: str
    discipline_iri: str = ""
    criterion_iri: str = ""
    textual_evidence_ids: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    confidence: str = "unreported"
    limitations: tuple[str, ...] = ()
    review_status: str = "machine_proposed"
    attribution_or_originality: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "observation_ids", tuple(self.observation_ids))
        object.__setattr__(self, "textual_evidence_ids", tuple(self.textual_evidence_ids))
        object.__setattr__(self, "alternatives", tuple(self.alternatives))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def to_dict(self) -> dict[str, Any]:
        return {
            "interpretation_id": self.interpretation_id,
            "object_id": self.object_id,
            "observation_ids": list(self.observation_ids),
            "statement": self.statement,
            "discipline_iri": self.discipline_iri,
            "criterion_iri": self.criterion_iri,
            "textual_evidence_ids": list(self.textual_evidence_ids),
            "alternatives": list(self.alternatives),
            "confidence": self.confidence,
            "limitations": list(self.limitations),
            "review_status": self.review_status,
            "attribution_or_originality": self.attribution_or_originality,
        }


@dataclass(frozen=True)
class CrossModalSupport:
    support_id: str
    claim_id: str
    asset_id: str | None
    observation_ids: tuple[str, ...]
    leg_status: Mapping[str, str]
    status: str
    weakest_leg: str
    limitations: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "observation_ids", tuple(self.observation_ids))
        object.__setattr__(self, "leg_status", dict(self.leg_status))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(self, "provenance", dict(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        return {
            "support_id": self.support_id,
            "claim_id": self.claim_id,
            "asset_id": self.asset_id,
            "observation_ids": list(self.observation_ids),
            "leg_status": dict(self.leg_status),
            "status": self.status,
            "weakest_leg": self.weakest_leg,
            "limitations": list(self.limitations),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class ImageAnalysisResult:
    status: str
    request_digest: str
    provider: str
    model: str
    config_digest: str
    observations: tuple[VisualObservation, ...] = ()
    interpretations: tuple[VisualInterpretation, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    rights_outcomes: Mapping[str, str] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    resource_use: Mapping[str, Any] = field(default_factory=dict)
    epg_links: tuple[str, ...] = ()
    contract_status: str = "executed"
    created_at: str = field(default_factory=utc_timestamp)
    response_digest: str = ""
    runtime: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in ANALYSIS_STATUSES:
            raise ValueError(f"invalid image analysis status: {self.status}")
        object.__setattr__(self, "runtime", dict(self.runtime))
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "interpretations", tuple(self.interpretations))
        object.__setattr__(self, "unresolved_questions", tuple(self.unresolved_questions))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(self, "rights_outcomes", dict(self.rights_outcomes))
        object.__setattr__(self, "resource_use", dict(self.resource_use))
        object.__setattr__(self, "epg_links", tuple(self.epg_links))
        interpretation_limitations = [
            "interpretation_without_observation_or_textual_evidence:" + str(item.interpretation_id)
            for item in self.interpretations
            if not item.observation_ids and not item.textual_evidence_ids
        ]
        if interpretation_limitations:
            object.__setattr__(
                self,
                "limitations",
                tuple(dict.fromkeys([*self.limitations, *interpretation_limitations])),
            )
        if not self.response_digest:
            object.__setattr__(
                self,
                "response_digest",
                canonical_digest(
                    {
                        "status": self.status,
                        "request_digest": self.request_digest,
                        "provider": self.provider,
                        "model": self.model,
                        "observations": [item.to_dict() for item in self.observations],
                        "interpretations": [item.to_dict() for item in self.interpretations],
                        "limitations": list(self.limitations),
                    }
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "contract_status": self.contract_status,
            "request_digest": self.request_digest,
            "provider": self.provider,
            "model": self.model,
            "config_digest": self.config_digest,
            "response_digest": self.response_digest,
            "runtime": dict(self.runtime),
            "observations": [item.to_dict() for item in self.observations],
            "interpretations": [item.to_dict() for item in self.interpretations],
            "unresolved_questions": list(self.unresolved_questions),
            "limitations": list(self.limitations),
            "rights_outcomes": dict(self.rights_outcomes),
            "elapsed_seconds": self.elapsed_seconds,
            "resource_use": dict(self.resource_use),
            "epg_links": list(self.epg_links),
            "created_at": self.created_at,
        }


class ImageAnalysisProvider(Protocol):
    def analyze(self, request: ImageAnalysisRequest) -> ImageAnalysisResult: ...


class DeterministicFakeImageProvider:
    """Offline provider used by ordinary CI; no image bytes or network calls."""

    def __init__(
        self,
        *,
        status: str = "complete",
        provider: str = "deterministic-fake",
        model: str = "fake-2d-v1",
    ) -> None:
        if status not in ANALYSIS_STATUSES:
            raise ValueError(f"invalid fake status: {status}")
        self.status = status
        self.provider = provider
        self.model = model

    def analyze(self, request: ImageAnalysisRequest) -> ImageAnalysisResult:
        assets, request_limit = _bounded_request_assets(request)
        if self.status == "error":
            return ImageAnalysisResult(
                "error",
                request.request_digest,
                self.provider,
                self.model,
                canonical_digest({"model": self.model}),
                limitations=("deterministic_fake_error",),
                runtime={"implementation": "swos_runtime.image_analysis", "mode": "offline"},
                created_at=DETERMINISTIC_TIMESTAMP,
            )
        if request_limit == "no_assets":
            return ImageAnalysisResult(
                "insufficient",
                request.request_digest,
                self.provider,
                self.model,
                canonical_digest({"model": self.model}),
                limitations=("no_assets",),
                runtime={"implementation": "swos_runtime.image_analysis", "mode": "offline"},
                created_at=DETERMINISTIC_TIMESTAMP,
            )
        if request_limit == "resource_limit":
            return ImageAnalysisResult(
                "insufficient",
                request.request_digest,
                self.provider,
                self.model,
                canonical_digest({"model": self.model}),
                limitations=("resource_limit",),
                runtime={"implementation": "swos_runtime.image_analysis", "mode": "offline"},
                created_at=DETERMINISTIC_TIMESTAMP,
            )
        if request_limit == "rights_denied":
            return ImageAnalysisResult(
                "denied",
                request.request_digest,
                self.provider,
                self.model,
                canonical_digest({"model": self.model}),
                limitations=("view_or_analyse_right_not_granted",),
                rights_outcomes={asset.asset_id: "denied" for asset in assets},
                runtime={"implementation": "swos_runtime.image_analysis", "mode": "offline"},
                created_at=DETERMINISTIC_TIMESTAMP,
            )
        if "analyse" not in request.allowed_actions:
            return ImageAnalysisResult(
                "denied",
                request.request_digest,
                self.provider,
                self.model,
                canonical_digest({"model": self.model}),
                limitations=("analyse_right_not_granted",),
                rights_outcomes={asset.asset_id: "denied" for asset in assets},
                runtime={"implementation": "swos_runtime.image_analysis", "mode": "offline"},
                created_at=DETERMINISTIC_TIMESTAMP,
            )
        limitations = []
        if len(assets) < len(request.assets):
            limitations.append("asset_limit_reached")
        maximum_observations = _bounded_limit(
            request.resource_limits.get("max_observations", 64), default=64
        )
        observations = tuple(
            VisualObservation(
                observation_id="observation-"
                + hashlib.sha256(asset.asset_id.encode()).hexdigest()[:24],
                object_id=asset.object_id,
                asset_id=asset.asset_id,
                asset_digest=asset.byte_digest,
                description=f"Visible evidence from asset {asset.asset_id}; no identity or attribution inferred.",
                origin="machine",
                selector=_full_asset_selector(asset),
                provider=self.provider,
                model=self.model,
                provenance={
                    "request_digest": request.request_digest,
                    "asset_digest": asset.byte_digest,
                },
                uncertainty=("machine_observation_requires_review",),
            )
            for asset in assets
        )[:maximum_observations]
        if len(observations) < len(assets):
            limitations.append("observation_limit_reached")
        status = self.status
        if limitations and status == "complete":
            status = "partial"
        return ImageAnalysisResult(
            status,
            request.request_digest,
            self.provider,
            self.model,
            canonical_digest({"model": self.model}),
            observations=observations,
            limitations=tuple(limitations),
            rights_outcomes={asset.asset_id: "allowed" for asset in assets},
            elapsed_seconds=0.0,
            resource_use={
                "assets": len(assets),
                "observations": len(observations),
                "max_seconds": request.resource_limits.get("max_seconds", 60),
            },
            runtime={"implementation": "swos_runtime.image_analysis", "mode": "offline"},
            created_at=DETERMINISTIC_TIMESTAMP,
        )


def _bounded_limit(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return -1
    return parsed if parsed >= 0 else -1


def _bounded_request_assets(
    request: ImageAnalysisRequest,
) -> tuple[tuple[MediaAssetRecord, ...], str | None]:
    if not request.assets:
        return (), "no_assets"
    maximum = _bounded_limit(request.resource_limits.get("max_assets", 8), default=8)
    if maximum < 1:
        return (), "resource_limit"
    assets = tuple(request.assets[:maximum])
    if any(
        not validate_media_asset(asset, required_actions=("view", "analyse")).valid
        for asset in assets
    ):
        return assets, "rights_denied"
    return assets, None


def _full_asset_selector(asset: MediaAssetRecord) -> RegionSelector:
    return RegionSelector(
        "iiif_pixel",
        f"0,0,{asset.width},{asset.height}",
        asset.byte_digest,
        asset_width=asset.width,
        asset_height=asset.height,
        normalized=(0, 0, asset.width, asset.height),
        validation_status="valid",
    )


class OpenAIImageAnalysisProvider:
    """Opt-in OpenAI image-input adapter behind the provider-neutral contract."""

    def __init__(
        self, *, api_key: str | None = None, model: str = "gpt-4.1-mini", enabled: bool = False
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.enabled = enabled

    def analyze(self, request: ImageAnalysisRequest) -> ImageAnalysisResult:
        config_digest = canonical_digest(
            {"provider": "openai", "model": self.model, "enabled": self.enabled}
        )
        if not self.enabled or not self.api_key:
            return ImageAnalysisResult(
                "error",
                request.request_digest,
                "openai",
                self.model,
                config_digest,
                limitations=("NOT_RUN: explicit live enablement and OPENAI_API_KEY are required",),
                runtime={"adapter": "swos_runtime.image_analysis_openai", "sdk": "openai-python"},
                contract_status="not_run",
            )
        if "analyse" not in request.allowed_actions:
            return ImageAnalysisResult(
                "denied",
                request.request_digest,
                "openai",
                self.model,
                config_digest,
                limitations=("analyse_right_not_granted",),
                contract_status="denied",
            )
        assets, request_limit = _bounded_request_assets(request)
        if request_limit == "no_assets":
            return ImageAnalysisResult(
                "insufficient",
                request.request_digest,
                "openai",
                self.model,
                config_digest,
                limitations=("no_assets",),
                contract_status="executed",
            )
        if request_limit == "resource_limit":
            return ImageAnalysisResult(
                "insufficient",
                request.request_digest,
                "openai",
                self.model,
                config_digest,
                limitations=("resource_limit",),
                contract_status="denied",
            )
        if request_limit == "rights_denied":
            return ImageAnalysisResult(
                "denied",
                request.request_digest,
                "openai",
                self.model,
                config_digest,
                limitations=("view_or_analyse_right_not_granted",),
                contract_status="denied",
            )
        try:
            verified_assets = []
            for asset in assets:
                content = request.captured_bytes.get(asset.asset_id)
                if content is None:
                    raise ValueError(
                        f"asset_content_digest_unverified:{asset.asset_id}:captured content is required"
                    )
                if hashlib.sha256(content).hexdigest() != asset.byte_digest:
                    raise ValueError(
                        f"asset_content_digest_unverified:{asset.asset_id}:digest mismatch"
                    )
                if len(content) != asset.byte_size:
                    raise ValueError(
                        f"asset_content_digest_unverified:{asset.asset_id}:byte size mismatch"
                    )
                encoded = base64.b64encode(content).decode("ascii")
                verified_assets.append((asset, f"data:{asset.mime_type};base64,{encoded}"))
        except ValueError as exc:
            return ImageAnalysisResult(
                "error",
                request.request_digest,
                "openai",
                self.model,
                config_digest,
                limitations=(str(exc),),
                runtime={
                    "adapter": "swos_runtime.image_analysis_openai",
                    "input_binding": "digest_verified_captured_bytes_required",
                },
                contract_status="error",
            )
        try:
            from openai import OpenAI

            try:
                from importlib.metadata import version as package_version

                sdk_version = package_version("openai")
            except Exception:  # pragma: no cover - optional dependency metadata
                sdk_version = "unreported"

            client = OpenAI(api_key=self.api_key)
            content = [
                {
                    "type": "input_text",
                    "text": "Describe only bounded visible observations. Do not infer identity, attribution, originality, or provenance.",
                }
            ]
            for _, image_url in verified_assets:
                content.append({"type": "input_image", "image_url": image_url})
            response = client.responses.create(
                model=self.model,
                input=[{"role": "user", "content": content}],
                timeout=float(request.resource_limits.get("max_seconds", 60)),
            )
            text = str(getattr(response, "output_text", "") or "")
            runtime = {
                "adapter": "swos_runtime.image_analysis_openai",
                "sdk": "openai-python",
                "sdk_version": sdk_version,
                "request_config": {
                    "model": self.model,
                    "max_seconds": request.resource_limits.get("max_seconds", 60),
                },
                "input_binding": "digest_verified_captured_bytes",
                "captured_asset_digests": {
                    asset.asset_id: asset.byte_digest for asset, _ in verified_assets
                },
            }
            if not text:
                return ImageAnalysisResult(
                    "insufficient",
                    request.request_digest,
                    "openai",
                    self.model,
                    config_digest,
                    limitations=("provider_returned_no_observation_text",),
                    runtime=runtime,
                    contract_status="executed",
                )
            maximum_observations = _bounded_limit(
                request.resource_limits.get("max_observations", 64), default=64
            )
            observations = tuple(
                VisualObservation(
                    observation_id=f"openai-observation-{index}",
                    object_id=asset.object_id,
                    asset_id=asset.asset_id,
                    asset_digest=asset.byte_digest,
                    description=text,
                    origin="machine",
                    selector=_full_asset_selector(asset),
                    provider="openai",
                    model=self.model,
                    provenance={
                        "request_digest": request.request_digest,
                        "asset_digest": asset.byte_digest,
                        "response_digest": canonical_digest({"output_text": text}),
                    },
                    uncertainty=("provider_observation_requires_review",),
                )
                for index, (asset, _) in enumerate(verified_assets, 1)
            )[:maximum_observations]
            limitations = ("observation_limit_reached",) if len(observations) < len(assets) else ()
            return ImageAnalysisResult(
                "partial" if limitations else "complete",
                request.request_digest,
                "openai",
                self.model,
                config_digest,
                observations=observations,
                limitations=limitations,
                runtime=runtime,
                contract_status="executed",
                response_digest=canonical_digest({"output_text": text}),
            )
        except Exception as exc:  # provider failures are explicit, never silent success
            return ImageAnalysisResult(
                "error",
                request.request_digest,
                "openai",
                self.model,
                config_digest,
                limitations=(f"provider_error:{type(exc).__name__}",),
                runtime={"adapter": "swos_runtime.image_analysis_openai", "sdk": "openai-python"},
                contract_status="error",
            )


def evaluate_cross_modal_support(
    claim: Mapping[str, Any],
    observations: Sequence[VisualObservation],
    textual_evidence: Sequence[Mapping[str, Any]],
) -> CrossModalSupport:
    claim_id = str(claim.get("claim_id") or claim.get("id") or "")
    object_id = str(claim.get("object_id") or "")
    asset_id = str(claim.get("asset_id") or "") or None
    normalized_observations = [
        item
        if isinstance(item, VisualObservation)
        else VisualObservation(
            observation_id=str(
                _mapping(item).get("observation_id") or _mapping(item).get("id") or ""
            ),
            object_id=str(_mapping(item).get("object_id") or ""),
            asset_id=str(_mapping(item).get("asset_id") or ""),
            asset_digest=str(_mapping(item).get("asset_digest") or ""),
            description=str(_mapping(item).get("description") or ""),
            origin=str(_mapping(item).get("origin") or "unknown"),
            selector=_mapping(item).get("selector"),
            supports_claim_ids=tuple(_mapping(item).get("supports_claim_ids") or ()),
            provider=str(_mapping(item).get("provider") or ""),
            model=str(_mapping(item).get("model") or ""),
            review_status=str(_mapping(item).get("review_status") or "machine_only"),
        )
        for item in observations
    ]
    relevant = [
        item
        for item in normalized_observations
        if (not object_id or item.object_id == object_id)
        and (not asset_id or item.asset_id == asset_id)
    ]
    asset_leg = (
        "supported"
        if relevant and (not asset_id or any(item.asset_id == asset_id for item in relevant))
        else "blocked"
    )
    observation_leg = (
        "supported" if any(claim_id in item.supports_claim_ids for item in relevant) else "blocked"
    )
    source_leg = (
        "supported"
        if any(
            str(_mapping(item).get("claim_id") or "") == claim_id
            and str(_mapping(item).get("support_level")) == "directly_supports"
            for item in textual_evidence
        )
        else "blocked"
    )
    legs = {
        "asset_to_object": asset_leg,
        "observation_to_claim": observation_leg,
        "source_to_claim": source_leg,
    }
    limitations: list[str] = []
    claim_type = str(claim.get("claim_type") or "").lower()
    if claim_type in {"attribution", "originality", "identity"}:
        limitations.append("visual_evidence_cannot_establish_attribution_or_originality")
        if not any(item.review_status == "human_reviewed" for item in relevant):
            limitations.append("attribution_or_originality_requires_human_review")
        if not any(
            str(_mapping(item).get("support_level") or "") == "directly_supports"
            and str(_mapping(item).get("claim_id") or "") == claim_id
            for item in textual_evidence
        ):
            limitations.append("attribution_or_originality_requires_external_evidence")
        legs["observation_to_claim"] = "blocked"
    if len({item.asset_id for item in relevant}) > 8:
        limitations.append("multi_view_limit_exceeded")
        legs["observation_to_claim"] = "limited"
    statuses = list(legs.values())
    status = (
        "supported"
        if all(value == "supported" for value in statuses) and not limitations
        else ("limited" if "limited" in statuses else "blocked")
    )
    weakest = (
        "blocked"
        if "blocked" in statuses
        else ("limited" if "limited" in statuses else "supported")
    )
    return CrossModalSupport(
        support_id="cross-modal-"
        + canonical_digest(
            {
                "claim": claim,
                "observations": [item.observation_id for item in normalized_observations],
            }
        )[:24],
        claim_id=claim_id,
        asset_id=asset_id,
        observation_ids=tuple(item.observation_id for item in relevant),
        leg_status=legs,
        status=status,
        weakest_leg=weakest,
        limitations=tuple(dict.fromkeys(limitations)),
        provenance={
            "authority": "swos-core",
            "observation_origin": sorted({item.origin for item in relevant}),
        },
    )


@dataclass(frozen=True)
class PromotionAssessment:
    capability: str
    pack: str
    stage: str
    status: str
    eligible: bool
    reasons: tuple[str, ...]
    improvement: float
    lower_confidence_bound: float
    source_sha: str
    baseline_digest: str
    candidate_digest: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "pack": self.pack,
            "stage": self.stage,
            "status": self.status,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "improvement": self.improvement,
            "lower_confidence_bound": self.lower_confidence_bound,
            "source_sha": self.source_sha,
            "baseline_digest": self.baseline_digest,
            "candidate_digest": self.candidate_digest,
            "evidence": dict(self.evidence),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class CapabilityPromotionDecision:
    status: str
    enabled: bool
    capability: str
    pack: str
    stage: str
    assessment_digest: str
    approval: Mapping[str, Any]
    rollback_trigger: str
    effective_at: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "enabled": self.enabled,
            "capability": self.capability,
            "pack": self.pack,
            "stage": self.stage,
            "assessment_digest": self.assessment_digest,
            "approval": dict(self.approval),
            "rollback_trigger": self.rollback_trigger,
            "effective_at": self.effective_at,
            "expires_at": self.expires_at,
        }


def _metric(value: Any, default: float = 0.0) -> float:
    if isinstance(value, Mapping):
        for key in ("value", "score", "metric"):
            if key in value:
                value = value[key]
                break
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _finite_metric(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _safe_canonical_digest(value: Any) -> str:
    """Digest invalid evidence without allowing non-finite JSON to escape."""

    try:
        return canonical_digest(value)
    except (TypeError, ValueError, OverflowError):

        def normalize(item: Any) -> Any:
            if isinstance(item, float) and not math.isfinite(item):
                return repr(item)
            if isinstance(item, Mapping):
                return {str(key): normalize(child) for key, child in item.items()}
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
                return [normalize(child) for child in item]
            return item

        return canonical_digest(normalize(value))


def _promotion_metric_id(
    capability: str,
    pack: str,
    stage: str,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> str:
    description = " ".join((capability, pack, stage)).lower().replace("-", "_")
    if "specialist" in description or "routing" in description:
        return "discipline_weighted_score"
    if any(token in description for token in ("multimodal", "multi_modal", "multi_view", "image")):
        return "cross_modal_f1"
    explicit = (
        policy.get("primary_metric")
        or candidate.get("primary_metric")
        or baseline.get("primary_metric")
        or candidate.get("metric_id")
        or baseline.get("metric_id")
    )
    if explicit:
        return str(explicit)
    return "independent"


def _metric_value(value: Any, metric_id: str) -> Any:
    if isinstance(value, Mapping):
        if metric_id != "independent" and metric_id in value:
            return value[metric_id]
        metrics = value.get("metrics")
        if isinstance(metrics, Mapping):
            if metric_id != "independent" and metric_id in metrics:
                return metrics[metric_id]
            if metric_id == "independent" and "primary" in metrics:
                return metrics["primary"]
        for key in ("metric", "score", "value"):
            if key in value:
                return value[key]
        return None
    return value


def _scalar_promotion_metric(data: Mapping[str, Any], metric_id: str) -> float | None:
    value = _metric_value(data, metric_id)
    return _finite_metric(_metric(value, float("nan")))


def _case_records(data: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    for key in ("case_results", "case_scores", "cases", "results"):
        if key not in data:
            continue
        raw = data[key]
        records: list[dict[str, Any]] = []
        if isinstance(raw, Mapping):
            for case_id, value in raw.items():
                record = dict(value) if isinstance(value, Mapping) else {"score": value}
                record.setdefault("case_id", str(case_id))
                records.append(record)
        elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            for value in raw:
                if isinstance(value, Mapping):
                    records.append(dict(value))
        return tuple(records)
    return ()


def _case_ids(data: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    declared = data.get("case_ids")
    if declared is not None:
        if isinstance(declared, (str, bytes, bytearray)):
            return ()
        return tuple(str(value) for value in declared)
    return tuple(str(record.get("case_id") or "") for record in records)


def _case_has_human_truth(data: Mapping[str, Any], record: Mapping[str, Any], case_id: str) -> bool:
    for key in ("human_truth", "gold", "truth", "reference", "reviewer_score"):
        if key in record and record[key] is not None:
            return True
    for key in ("human_review", "human_reviewed"):
        if key in record:
            return bool(record[key])
    if str(record.get("review_status") or "").lower() in {"reviewed", "approved", "adjudicated"}:
        return True
    for key in ("human_truth", "human_review", "reviewed_case_ids"):
        value = data.get(key)
        if isinstance(value, Mapping) and case_id in value:
            return value[case_id] is not None
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            if case_id in {str(item) for item in value}:
                return True
    return False


def _case_level_scores(
    data: Mapping[str, Any], metric_id: str
) -> tuple[tuple[str, ...], tuple[float, ...], tuple[str, ...], bool]:
    has_case_data = any(key in data for key in ("case_results", "case_scores", "cases", "results"))
    if not has_case_data:
        return (), (), (), False
    records = _case_records(data)
    declared_ids = _case_ids(data, records)
    if not declared_ids or len(set(declared_ids)) != len(declared_ids):
        return (), (), ("case_ids_missing_or_duplicate",), True
    by_id: dict[str, Mapping[str, Any]] = {}
    for record in records:
        case_id = str(record.get("case_id") or "")
        if not case_id or case_id in by_id:
            return (), (), ("case_results_missing_or_duplicate",), True
        by_id[case_id] = record
    if set(by_id) != set(declared_ids):
        return (), (), ("case_results_denominator_mismatch",), True
    scores: list[float] = []
    for case_id in declared_ids:
        record = by_id[case_id]
        if not _case_has_human_truth(data, record, case_id):
            return (), (), (f"human_truth_missing:{case_id}",), True
        raw_draws = record.get("draws", record.get("repeated_draws"))
        if raw_draws is None:
            raw_value = _metric_value(record, metric_id)
            raw_draws = (
                raw_value
                if isinstance(raw_value, Sequence)
                and not isinstance(raw_value, (str, bytes, bytearray))
                else [raw_value]
            )
        if isinstance(raw_draws, (str, bytes, bytearray)) or not isinstance(raw_draws, Sequence):
            raw_draws = [raw_draws]
        draws = [
            _finite_metric(_metric(_metric_value(draw, metric_id), float("nan")))
            for draw in raw_draws
        ]
        if not draws or any(draw is None for draw in draws):
            return (), (), (f"case_score_missing_or_nonfinite:{case_id}",), True
        scores.append(sum(draw for draw in draws if draw is not None) / len(draws))
    if len(scores) < 2:
        return (), (), ("insufficient_case_count",), True
    return tuple(declared_ids), tuple(scores), (), True


def _evaluation_manifest_digest(data: Mapping[str, Any]) -> str | None:
    for key in ("evaluation_manifest_digest", "eval_manifest_digest", "manifest_digest"):
        value = data.get(key)
        if value:
            return str(value)
    for key in ("evaluation_manifest", "eval_manifest"):
        value = data.get(key)
        if value is not None:
            return canonical_digest(value)
    return None


def _paired_bootstrap(
    differences: Sequence[float], manifest_digest: str
) -> tuple[float, float, float, int]:
    try:
        seed = int(str(manifest_digest)[:16], 16)
    except ValueError:
        seed = int(canonical_digest(manifest_digest)[:16], 16)
    randomizer = random.Random(seed)
    count = len(differences)
    means: list[float] = []
    for _ in range(PROMOTION_BOOTSTRAP_RESAMPLES):
        total = sum(differences[randomizer.randrange(count)] for _ in range(count))
        means.append(total / count)
    means.sort()
    position = (len(means) - 1) * 0.025
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(means) - 1)
    fraction = position - lower_index
    lower = means[lower_index] + (means[upper_index] - means[lower_index]) * fraction
    upper_position = (len(means) - 1) * 0.975
    upper_index = int(upper_position)
    upper_next_index = min(upper_index + 1, len(means) - 1)
    upper_fraction = upper_position - upper_index
    upper = means[upper_index] + (means[upper_next_index] - means[upper_index]) * upper_fraction
    return sum(differences) / count, lower, upper, seed


def assess_promotion(
    *,
    capability: str,
    pack: str,
    stage: str,
    baseline: Any,
    candidate: Any,
    policy: Mapping[str, Any] | None = None,
) -> PromotionAssessment:
    baseline_data = _mapping(baseline)
    candidate_data = _mapping(candidate)
    policy = dict(policy or {})
    minimum = float(policy.get("minimum_improvement", 0.08))
    lower_minimum = float(policy.get("lower_confidence_bound_minimum", 0.0))
    primary_metric = _promotion_metric_id(
        capability, pack, stage, baseline_data, candidate_data, policy
    )
    baseline_metric = _scalar_promotion_metric(baseline_data, primary_metric)
    candidate_metric = _scalar_promotion_metric(candidate_data, primary_metric)
    evaluation_not_run: list[str] = []
    baseline_case_ids, baseline_case_scores, baseline_case_reasons, baseline_has_cases = (
        _case_level_scores(baseline_data, primary_metric)
    )
    candidate_case_ids, candidate_case_scores, candidate_case_reasons, candidate_has_cases = (
        _case_level_scores(candidate_data, primary_metric)
    )
    case_level = baseline_has_cases or candidate_has_cases
    case_id_digest = ""
    bootstrap_seed: int | None = None
    upper_confidence_bound: float | None = None
    case_differences: list[float] = []
    if case_level:
        if not baseline_has_cases or not candidate_has_cases:
            evaluation_not_run.append("case_level_pair_missing")
        evaluation_not_run.extend(baseline_case_reasons)
        evaluation_not_run.extend(candidate_case_reasons)
        if not evaluation_not_run and set(baseline_case_ids) != set(candidate_case_ids):
            evaluation_not_run.append("case_results_denominator_mismatch")
        if not baseline_data.get("draw_digest") or not candidate_data.get("draw_digest"):
            evaluation_not_run.append("draw_digest_missing")
        manifest_digest = _evaluation_manifest_digest(candidate_data)
        baseline_manifest_digest = _evaluation_manifest_digest(baseline_data)
        if manifest_digest is None or baseline_manifest_digest is None:
            evaluation_not_run.append("evaluation_manifest_digest_missing")
        elif manifest_digest != baseline_manifest_digest:
            evaluation_not_run.append("paired_evidence_mismatch:evaluation_manifest_digest")
        if not evaluation_not_run:
            ordered_case_ids = tuple(sorted(baseline_case_ids))
            baseline_by_id = dict(zip(baseline_case_ids, baseline_case_scores))
            candidate_by_id = dict(zip(candidate_case_ids, candidate_case_scores))
            baseline_case_ids = ordered_case_ids
            candidate_case_ids = ordered_case_ids
            baseline_case_scores = tuple(baseline_by_id[case_id] for case_id in ordered_case_ids)
            candidate_case_scores = tuple(candidate_by_id[case_id] for case_id in ordered_case_ids)
            case_id_digest = canonical_digest(ordered_case_ids)
            baseline_metric = sum(baseline_case_scores) / len(baseline_case_scores)
            candidate_metric = sum(candidate_case_scores) / len(candidate_case_scores)
            case_differences = [
                candidate_score - baseline_score
                for baseline_score, candidate_score in zip(
                    baseline_case_scores, candidate_case_scores
                )
            ]
            improvement, lower, upper_confidence_bound, bootstrap_seed = _paired_bootstrap(
                case_differences, manifest_digest or ""
            )
        else:
            improvement = 0.0
            lower = -1.0
            baseline_metric = baseline_metric if baseline_metric is not None else 0.0
            candidate_metric = candidate_metric if candidate_metric is not None else 0.0
    else:
        if baseline_metric is None or candidate_metric is None:
            evaluation_not_run.append("primary_metric_missing_or_nonfinite")
            baseline_metric = baseline_metric if baseline_metric is not None else 0.0
            candidate_metric = candidate_metric if candidate_metric is not None else 0.0
        improvement = candidate_metric - baseline_metric
        lower = _finite_metric(
            candidate_data.get("lower_95_ci", candidate_data.get("lower_confidence_bound", -1.0))
        )
        if lower is None:
            evaluation_not_run.append("lower_confidence_bound_missing_or_nonfinite")
            lower = -1.0
        upper_confidence_bound = _finite_metric(
            candidate_data.get("upper_95_ci", candidate_data.get("upper_confidence_bound"))
        )
        case_ids = _case_ids(candidate_data, ())
        case_id_digest = canonical_digest(sorted(case_ids)) if case_ids else ""
        manifest_digest = _evaluation_manifest_digest(candidate_data)
    reasons: list[str] = []
    if baseline_data.get("source_sha") != candidate_data.get("source_sha"):
        reasons.append("exact_head_mismatch")
    for key in (
        "case_ids",
        "provider",
        "model",
        "config_digest",
        "prompt_digest",
        "seed",
        "draw_digest",
        "artifact_digest",
    ):
        if key == "case_ids" and case_level:
            baseline_case_ids_for_pair = set(_case_ids(baseline_data, _case_records(baseline_data)))
            candidate_case_ids_for_pair = set(
                _case_ids(candidate_data, _case_records(candidate_data))
            )
            if baseline_case_ids_for_pair != candidate_case_ids_for_pair:
                reasons.append(f"paired_evidence_mismatch:{key}")
        elif baseline_data.get(key) != candidate_data.get(key):
            reasons.append(f"paired_evidence_mismatch:{key}")
    for key in ("evaluation_manifest_digest", "eval_manifest_digest", "manifest_digest"):
        if baseline_data.get(key) is not None or candidate_data.get(key) is not None:
            if baseline_data.get(key) != candidate_data.get(key):
                reasons.append(f"paired_evidence_mismatch:{key}")
    if evaluation_not_run:
        reasons.append("evaluation_not_run")
    if improvement < minimum:
        reasons.append("improvement_below_threshold")
    if lower <= lower_minimum:
        reasons.append("paired_lower_confidence_bound_not_positive")
    if not candidate_data.get("live_exact_head"):
        reasons.append("live_exact_head_evidence_missing")
    if not candidate_data.get("human_quorum") or not candidate_data.get("role_separation"):
        reasons.append("human_or_role_quorum_missing")
    if candidate_data.get("safety_regressions"):
        reasons.append("safety_regression")
    if not candidate_data.get("rollback_tested") or not candidate_data.get("pack_only_fallback"):
        reasons.append("rollback_or_pack_fallback_missing")
    if candidate_data.get("status") in {"not_run", "blocked", "disabled"}:
        reasons.append("candidate_evidence_not_run")
    if candidate_data.get("expired") or candidate_data.get("status") == "expired":
        reasons.append("candidate_evidence_expired")
    expires_at = candidate_data.get("expires_at")
    if expires_at:
        try:
            parsed_expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if parsed_expiry.tzinfo is None:
                parsed_expiry = parsed_expiry.replace(tzinfo=timezone.utc)
            if parsed_expiry.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                reasons.append("candidate_evidence_expired")
        except ValueError:
            reasons.append("candidate_evidence_expiry_invalid")
    blocking_metrics = candidate_data.get("blocking_metrics")
    baseline_blocking_metrics = baseline_data.get("blocking_metrics")
    if isinstance(blocking_metrics, Mapping) or isinstance(baseline_blocking_metrics, Mapping):
        candidate_blocking = (
            dict(blocking_metrics or {}) if isinstance(blocking_metrics, Mapping) else {}
        )
        baseline_blocking = (
            dict(baseline_blocking_metrics or {})
            if isinstance(baseline_blocking_metrics, Mapping)
            else {}
        )
        if set(candidate_blocking) != set(baseline_blocking):
            reasons.append("blocking_metric_set_mismatch")
        for metric_name in set(candidate_blocking) | set(baseline_blocking):
            if (
                _finite_metric(candidate_blocking.get(metric_name)) is None
                or _finite_metric(baseline_blocking.get(metric_name)) is None
            ):
                evaluation_not_run.append(f"blocking_metric_not_run:{metric_name}")
        minimums = policy.get("blocking_metric_minimums", {})
        if isinstance(minimums, Mapping):
            for metric_name, threshold in minimums.items():
                value = _finite_metric(candidate_blocking.get(metric_name))
                if value is None:
                    reasons.append(f"blocking_metric_not_run:{metric_name}")
                elif value < float(threshold):
                    reasons.append(f"blocking_metric_below_threshold:{metric_name}")
    manifest_digest = _evaluation_manifest_digest(candidate_data)
    if evaluation_not_run and "evaluation_not_run" not in reasons:
        reasons.append("evaluation_not_run")
    evaluation_status = "not_run" if evaluation_not_run else "evaluated"
    return PromotionAssessment(
        capability,
        pack,
        stage,
        "eligible" if not reasons else "disabled",
        not reasons,
        tuple(dict.fromkeys(reasons)),
        improvement,
        lower,
        str(candidate_data.get("source_sha") or ""),
        _safe_canonical_digest(baseline_data),
        _safe_canonical_digest(candidate_data),
        {
            "primary_metric": primary_metric,
            "evaluation_status": evaluation_status,
            "case_level_evaluation": case_level,
            "case_count": len(case_differences)
            if case_level
            else len(_case_ids(candidate_data, ())),
            "case_id_digest": case_id_digest,
            "case_differences": list(case_differences),
            "per_case_scores": [
                {
                    "case_id": case_id,
                    "baseline": baseline_score,
                    "candidate": candidate_score,
                    "difference": candidate_score - baseline_score,
                }
                for case_id, baseline_score, candidate_score in zip(
                    baseline_case_ids, baseline_case_scores, candidate_case_scores
                )
            ],
            "evaluation_manifest_digest": manifest_digest,
            "bootstrap_resamples": PROMOTION_BOOTSTRAP_RESAMPLES if case_level else 0,
            "bootstrap_seed": bootstrap_seed,
            "confidence_interval": {
                "lower": lower,
                "upper": upper_confidence_bound,
                "method": "paired_case_bootstrap_percentile_95",
            },
            "upper_confidence_bound": upper_confidence_bound,
            "minimum_improvement": minimum,
            "lower_confidence_bound_minimum": lower_minimum,
            "baseline_metric": baseline_metric,
            "candidate_metric": candidate_metric,
            "expires_at": expires_at,
        },
    )


def commit_promotion(assessment: PromotionAssessment, approval: Any) -> CapabilityPromotionDecision:
    approval_data = _mapping(approval)
    reasons = [] if assessment.eligible else list(assessment.reasons)
    if approval_data.get("disposition") != "approved" or not approval_data.get("approver_id"):
        reasons.append("approval_missing")
    assessment_digest = canonical_digest(assessment.to_dict())
    if approval_data.get("assessment_digest") != assessment_digest:
        reasons.append("approval_assessment_mismatch")
    if reasons:
        return CapabilityPromotionDecision(
            "disabled",
            False,
            assessment.capability,
            assessment.pack,
            assessment.stage,
            assessment_digest,
            approval_data,
            "rollback_on_safety_or_evidence_regression",
        )
    return CapabilityPromotionDecision(
        "enabled",
        True,
        assessment.capability,
        assessment.pack,
        assessment.stage,
        assessment_digest,
        approval_data,
        "rollback_on_safety_or_evidence_regression",
        effective_at=utc_timestamp(),
        expires_at=str(
            approval_data.get("expires_at") or assessment.evidence.get("expires_at") or ""
        )
        or None,
    )


def rollback_promotion(
    decision: CapabilityPromotionDecision, *, reason: str
) -> CapabilityPromotionDecision:
    return CapabilityPromotionDecision(
        "rolled_back",
        False,
        decision.capability,
        decision.pack,
        decision.stage,
        decision.assessment_digest,
        {**dict(decision.approval), "rollback_reason": reason},
        decision.rollback_trigger,
    )
