"""Rights-aware object, media, inspection, accessibility, and selector models."""

from __future__ import annotations

import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from .models import canonical_digest, utc_timestamp

RIGHTS_ACTIONS = (
    "view",
    "analyse",
    "transform",
    "create_derivative",
    "quote",
    "cache",
    "export",
    "redistribute",
)
MEDIA_ROLES = frozenset(
    {"surrogate", "documentary", "technical", "installation", "detail", "diagram", "generated"}
)
RIGHTS_STATES = frozenset({"allowed", "denied", "unknown"})


def _absolute_uri(value: Any) -> bool:
    parsed = urlparse(str(value or ""))
    return bool(parsed.scheme and parsed.netloc)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(vars(value))


def _status(grant: Any) -> str:
    if isinstance(grant, Mapping):
        value = grant.get("status", grant.get("state", "unknown"))
    else:
        value = grant
    return str(value or "unknown").lower()


def _not_expired(grant: Any) -> bool:
    if not isinstance(grant, Mapping) or not grant.get("expires_at"):
        return True
    try:
        value = datetime.fromisoformat(str(grant["expires_at"]).replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc) > datetime.now(timezone.utc)
    except ValueError:
        return False


@dataclass(frozen=True)
class MediaRightsPolicy:
    policy_id: str = "swos.media-rights"
    version: str = "2.0.0"
    actions: tuple[str, ...] = RIGHTS_ACTIONS
    unknown_effect: str = "deny"

    def __post_init__(self) -> None:
        object.__setattr__(self, "actions", tuple(self.actions))
        if tuple(self.actions) != RIGHTS_ACTIONS:
            raise ValueError("media rights policy must retain all eight purpose-specific actions")
        if self.unknown_effect != "deny":
            raise ValueError("unknown media rights must deny")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "MediaRightsPolicy":
        return cls(
            policy_id=str(payload.get("policy_id") or cls.policy_id),
            version=str(payload.get("version") or cls.version),
            actions=tuple(payload.get("rights_actions") or RIGHTS_ACTIONS),
            unknown_effect=str(payload.get("unknown_rights_effect") or "deny"),
        )


@dataclass(frozen=True)
class ObjectRecord:
    object_id: str
    object_type: str
    label: str
    creator: str | None = None
    date_or_period: str | None = None
    culture: str | None = None
    materials: tuple[str, ...] = ()
    dimensions: Mapping[str, Any] = field(default_factory=dict)
    collection: str | None = None
    current_location: str | None = None
    identifiers: Mapping[str, str] = field(default_factory=dict)
    identity_confidence: str = "unknown"
    source_rights: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    competing_attributions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "materials", tuple(self.materials))
        object.__setattr__(self, "dimensions", dict(self.dimensions))
        object.__setattr__(self, "identifiers", dict(self.identifiers))
        object.__setattr__(self, "source_rights", dict(self.source_rights))
        object.__setattr__(self, "provenance", dict(self.provenance))
        object.__setattr__(self, "competing_attributions", tuple(self.competing_attributions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "label": self.label,
            "creator": self.creator,
            "date_or_period": self.date_or_period,
            "culture": self.culture,
            "materials": list(self.materials),
            "dimensions": dict(self.dimensions),
            "collection": self.collection,
            "current_location": self.current_location,
            "identifiers": dict(self.identifiers),
            "identity_confidence": self.identity_confidence,
            "source_rights": dict(self.source_rights),
            "provenance": dict(self.provenance),
            "competing_attributions": list(self.competing_attributions),
        }


@dataclass(frozen=True)
class ObjectInspectionActivity:
    inspection_id: str
    object_id: str
    actor_id: str
    observed_scope: str
    timestamp: str = field(default_factory=utc_timestamp)
    role: str = "inspector"
    location: str | None = None
    access_method: str | None = None
    conditions: Mapping[str, Any] = field(default_factory=dict)
    instruments: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    notes_digest: str | None = None
    epg_activity_id: str | None = None
    sdl_decision_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "conditions", dict(self.conditions))
        object.__setattr__(self, "instruments", tuple(self.instruments))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def to_dict(self) -> dict[str, Any]:
        return {
            "inspection_id": self.inspection_id,
            "object_id": self.object_id,
            "actor_id": self.actor_id,
            "role": self.role,
            "timestamp": self.timestamp,
            "location": self.location,
            "access_method": self.access_method,
            "conditions": dict(self.conditions),
            "instruments": list(self.instruments),
            "observed_scope": self.observed_scope,
            "limitations": list(self.limitations),
            "notes_digest": self.notes_digest,
            "epg_activity_id": self.epg_activity_id,
            "sdl_decision_id": self.sdl_decision_id,
        }


@dataclass(frozen=True)
class AccessibilityRecord:
    asset_digest: str
    purpose: str
    short_alternative: str
    long_description: str | None = None
    region_labels: tuple[Mapping[str, Any], ...] = ()
    text_fallback: str | None = None
    origin: str = "machine_assisted"
    review_status: str = "machine_only"
    reviewer_id: str | None = None
    language: str = "en"
    invalidation_reason: str | None = None
    created_at: str = field(default_factory=utc_timestamp)
    reviewed_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "region_labels", tuple(dict(value) for value in self.region_labels)
        )

    @property
    def valid(self) -> bool:
        return bool(
            re.fullmatch(r"[0-9a-f]{64}", self.asset_digest or "")
            and self.purpose in {"decorative", "functional", "evidentiary"}
            and self.short_alternative.strip()
            and (self.purpose != "evidentiary" or self.long_description or self.text_fallback)
            and self.review_status == "reviewed"
            and not self.invalidation_reason
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_digest": self.asset_digest,
            "purpose": self.purpose,
            "short_alternative": self.short_alternative,
            "long_description": self.long_description,
            "region_labels": [dict(value) for value in self.region_labels],
            "text_fallback": self.text_fallback,
            "origin": self.origin,
            "review_status": self.review_status,
            "reviewer_id": self.reviewer_id,
            "language": self.language,
            "invalidation_reason": self.invalidation_reason,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "valid": self.valid,
        }


@dataclass(frozen=True)
class MediaAssetRecord:
    asset_id: str
    object_id: str
    role: str
    mime_type: str
    byte_size: int
    width: int
    height: int
    byte_digest: str
    acquisition_uri: str
    rights: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    source_uri: str | None = None
    iiif_manifest_id: str | None = None
    canvas_id: str | None = None
    view_conditions: Mapping[str, Any] = field(default_factory=dict)
    capture_conditions: Mapping[str, Any] = field(default_factory=dict)
    colour_profile: str | None = None
    inspection_activity_ids: tuple[str, ...] = ()
    transformations: tuple[Mapping[str, Any], ...] = ()
    parent_asset_ids: tuple[str, ...] = ()
    parent_digests: tuple[str, ...] = ()
    content_credentials: Mapping[str, Any] = field(default_factory=dict)
    accessibility: AccessibilityRecord | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    generated: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "rights", {str(key): dict(value) for key, value in self.rights.items()}
        )
        object.__setattr__(self, "view_conditions", dict(self.view_conditions))
        object.__setattr__(self, "capture_conditions", dict(self.capture_conditions))
        object.__setattr__(self, "inspection_activity_ids", tuple(self.inspection_activity_ids))
        object.__setattr__(
            self, "transformations", tuple(dict(value) for value in self.transformations)
        )
        object.__setattr__(self, "parent_asset_ids", tuple(self.parent_asset_ids))
        object.__setattr__(self, "parent_digests", tuple(self.parent_digests))
        object.__setattr__(self, "content_credentials", dict(self.content_credentials))
        object.__setattr__(self, "provenance", dict(self.provenance))

    def action_status(self, action: str) -> str:
        grant = self.rights.get(action)
        value = _status(grant)
        if value not in RIGHTS_STATES or not _not_expired(grant):
            return "unknown"
        return value

    def action_allowed(self, action: str) -> bool:
        return action in RIGHTS_ACTIONS and self.action_status(action) == "allowed"

    def to_dict(self, *, include_bytes: bool = False) -> dict[str, Any]:
        value = {
            "asset_id": self.asset_id,
            "object_id": self.object_id,
            "role": self.role,
            "mime_type": self.mime_type,
            "byte_size": self.byte_size,
            "width": self.width,
            "height": self.height,
            "byte_digest": self.byte_digest,
            "acquisition_uri": self.acquisition_uri,
            "source_uri": self.source_uri,
            "iiif_manifest_id": self.iiif_manifest_id,
            "canvas_id": self.canvas_id,
            "rights": {key: dict(item) for key, item in sorted(self.rights.items())},
            "view_conditions": dict(self.view_conditions),
            "capture_conditions": dict(self.capture_conditions),
            "colour_profile": self.colour_profile,
            "inspection_activity_ids": list(self.inspection_activity_ids),
            "transformations": [dict(item) for item in self.transformations],
            "parent_asset_ids": list(self.parent_asset_ids),
            "parent_digests": list(self.parent_digests),
            "content_credentials": dict(self.content_credentials),
            "accessibility": self.accessibility.to_dict() if self.accessibility else None,
            "provenance": dict(self.provenance),
            "generated": self.generated,
        }
        if include_bytes:
            value["bytes"] = None
        return value


@dataclass(frozen=True)
class AssetValidation:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    action_states: Mapping[str, str] = field(default_factory=dict)

    def allowed(self, action: str) -> bool:
        return self.valid and self.action_states.get(action) == "allowed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "action_states": dict(self.action_states),
        }


def validate_media_asset(
    asset: MediaAssetRecord,
    policy: MediaRightsPolicy | None = None,
    *,
    required_actions: Sequence[str] = (),
) -> AssetValidation:
    policy = policy or MediaRightsPolicy()
    errors: list[str] = []
    warnings: list[str] = []
    if not asset.asset_id or not asset.object_id:
        errors.append("asset and object identity are required")
    if asset.role not in MEDIA_ROLES:
        errors.append(f"unsupported media role: {asset.role}")
    if not re.fullmatch(r"[0-9a-f]{64}", asset.byte_digest or ""):
        errors.append("asset byte_digest must be a lowercase SHA-256 digest")
    if asset.byte_size < 0 or asset.width <= 0 or asset.height <= 0:
        errors.append("asset byte size and dimensions must be positive")
    if not _absolute_uri(asset.acquisition_uri):
        errors.append("asset acquisition_uri must be absolute")
    action_states = {action: asset.action_status(action) for action in policy.actions}
    for action in required_actions:
        if action not in RIGHTS_ACTIONS or action_states.get(action) != "allowed":
            errors.append(f"rights do not allow required action: {action}")
    if asset.accessibility and asset.accessibility.asset_digest != asset.byte_digest:
        warnings.append("accessibility record digest does not match asset")
    if asset.generated and asset.role != "generated":
        errors.append("generated asset must be explicitly labelled generated")
    return AssetValidation(
        not errors, tuple(dict.fromkeys(errors)), tuple(dict.fromkeys(warnings)), action_states
    )


def inherit_rights(
    parent: MediaAssetRecord, grants: Mapping[str, Mapping[str, Any]] | None = None
) -> dict[str, dict[str, Any]]:
    grants = grants or {}
    inherited: dict[str, dict[str, Any]] = {}
    for action in RIGHTS_ACTIONS:
        parent_grant = dict(parent.rights.get(action) or {"status": "unknown"})
        grant = dict(grants.get(action) or {})
        if _status(parent_grant) == "denied" and not (
            _status(grant) == "allowed" and grant.get("evidence") and grant.get("grant_id")
        ):
            inherited[action] = {
                **parent_grant,
                "status": "denied",
                "inherited_from": parent.asset_id,
            }
        elif _status(parent_grant) != "allowed" and not (
            _status(grant) == "allowed" and grant.get("evidence") and grant.get("grant_id")
        ):
            inherited[action] = {
                **parent_grant,
                "status": "unknown",
                "inherited_from": parent.asset_id,
            }
        else:
            inherited[action] = {**parent_grant, **grant, "inherited_from": parent.asset_id}
    return inherited


def _evidenced_grant_allows(grants: Mapping[str, Mapping[str, Any]], action: str) -> bool:
    grant = grants.get(action) or {}
    return (
        _status(grant) == "allowed" and bool(grant.get("evidence")) and bool(grant.get("grant_id"))
    )


def derive_asset(
    parent: MediaAssetRecord,
    *,
    asset_id: str,
    byte_digest: str,
    transform: str,
    rights_grant: Mapping[str, Mapping[str, Any]] | None = None,
) -> MediaAssetRecord:
    rights_grant = rights_grant or {}
    if not parent.action_allowed("view") or not parent.action_allowed("analyse"):
        raise PermissionError("derivative creation requires view and analyse rights")
    if not (
        parent.action_allowed("transform")
        or parent.action_allowed("create_derivative")
        or _evidenced_grant_allows(rights_grant, "transform")
        or _evidenced_grant_allows(rights_grant, "create_derivative")
    ):
        raise PermissionError("derivative creation requires transform or create_derivative rights")
    accessibility = parent.accessibility
    if accessibility:
        accessibility = replace(
            accessibility, invalidation_reason="invalidated_derivative", review_status="stale"
        )
    content_credentials = dict(parent.content_credentials)
    if content_credentials:
        content_credentials = {
            **content_credentials,
            "parent_status": str(content_credentials.get("status") or "unknown"),
            "parent_digest": content_credentials.get("credential_digest"),
            "status": "invalidated_derivative",
        }
    return MediaAssetRecord(
        asset_id=asset_id,
        object_id=parent.object_id,
        role="generated",
        mime_type=parent.mime_type,
        byte_size=0,
        width=parent.width,
        height=parent.height,
        byte_digest=byte_digest,
        acquisition_uri=parent.acquisition_uri,
        rights=inherit_rights(parent, rights_grant),
        source_uri=parent.source_uri,
        parent_asset_ids=(parent.asset_id,),
        parent_digests=(parent.byte_digest,),
        transformations=(
            *parent.transformations,
            {"operation": transform, "parent_digest": parent.byte_digest},
        ),
        content_credentials=content_credentials,
        accessibility=accessibility,
        provenance={"derived_from": parent.asset_id, "parent_digest": parent.byte_digest},
        generated=True,
    )


def redact_asset_for_export(asset: MediaAssetRecord) -> dict[str, Any]:
    if not asset.action_allowed("export"):
        return {
            "asset_id": asset.asset_id,
            "object_id": asset.object_id,
            "byte_digest": asset.byte_digest,
            "redacted": True,
            "limitations": ["export_right_denied", "media_bytes_omitted"],
            "rights": {key: dict(value) for key, value in sorted(asset.rights.items())},
        }
    return {**asset.to_dict(include_bytes=True), "redacted": False, "limitations": []}


@dataclass(frozen=True)
class RegionSelector:
    selector_type: str
    original: str | Mapping[str, Any]
    asset_digest: str
    asset_width: int | None = None
    asset_height: int | None = None
    normalized: tuple[int, int, int, int] | None = None
    validation_status: str = "unvalidated"
    selector_digest: str = ""

    def __post_init__(self) -> None:
        if not self.selector_digest:
            object.__setattr__(
                self,
                "selector_digest",
                canonical_digest(
                    {
                        "type": self.selector_type,
                        "original": self.original,
                        "asset_digest": self.asset_digest,
                        "normalized": self.normalized,
                    }
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "selector_type": self.selector_type,
            "original": self.original,
            "asset_digest": self.asset_digest,
            "asset_width": self.asset_width,
            "asset_height": self.asset_height,
            "normalized": list(self.normalized) if self.normalized else None,
            "validation_status": self.validation_status,
            "selector_digest": self.selector_digest,
        }


def _selector_text(original: str | Mapping[str, Any]) -> str:
    return (
        json.dumps(dict(original), sort_keys=True, separators=(",", ":"))
        if isinstance(original, Mapping)
        else str(original).strip()
    )


def _bounded_geometry(
    values: Sequence[float], width: int, height: int
) -> tuple[int, int, int, int]:
    if len(values) != 4 or not all(math.isfinite(float(value)) for value in values):
        raise ValueError("selector geometry requires four finite values")
    x, y, w, h = (float(value) for value in values)
    if min(x, y, w, h) < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
        raise ValueError("selector geometry is out of bounds")
    normalized = (int(round(x)), int(round(y)), int(round(w)), int(round(h)))
    if (
        normalized[2] <= 0
        or normalized[3] <= 0
        or normalized[0] < 0
        or normalized[1] < 0
        or normalized[0] + normalized[2] > width
        or normalized[1] + normalized[3] > height
    ):
        raise ValueError("selector geometry rounds outside asset bounds")
    return normalized


def normalize_selector(selector: RegionSelector, asset: MediaAssetRecord) -> RegionSelector:
    if selector.asset_digest != asset.byte_digest:
        raise ValueError("selector asset digest does not match media bytes")
    original_mapping = dict(selector.original) if isinstance(selector.original, Mapping) else None
    text = _selector_text(selector.original)
    selector_type = str(selector.selector_type).lower().replace("_", "")
    if selector_type in {"svgselector", "webannotationsvg"}:
        selector_type = "svg"
    elif selector_type in {"iiifpixel", "pixel"}:
        selector_type = "iiifpixel"
    elif selector_type in {"iiifpercent", "percent"}:
        selector_type = "iiifpercent"
    if len(text) > 100_000:
        raise ValueError("selector exceeds bounded complexity")
    if selector_type == "iiifpixel":
        if original_mapping and {"x", "y", "w", "h"}.issubset(original_mapping):
            text = ",".join(str(original_mapping[key]) for key in ("x", "y", "w", "h"))
        if text.startswith("xywh="):
            text = text[5:]
        try:
            values = [float(item.strip()) for item in text.split(",")]
        except ValueError as exc:
            raise ValueError("invalid IIIF pixel selector") from exc
        normalized = _bounded_geometry(values, asset.width, asset.height)
    elif selector_type == "iiifpercent":
        if not text.startswith("pct:"):
            raise ValueError("IIIF percentage selector must start with pct:")
        try:
            x, y, w, h = (float(item.strip()) for item in text[4:].split(","))
        except ValueError as exc:
            raise ValueError("invalid IIIF percentage selector") from exc
        normalized = _bounded_geometry(
            (
                asset.width * x / 100,
                asset.height * y / 100,
                asset.width * w / 100,
                asset.height * h / 100,
            ),
            asset.width,
            asset.height,
        )
    elif selector_type == "svg":
        if original_mapping:
            text = str(original_mapping.get("value") or original_mapping.get("svg") or "")
        if "<script" in text.lower() or "javascript:" in text.lower():
            raise ValueError("SVG selector contains executable content")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise ValueError("SVG selector is not well formed") from exc
        elements = list(root.iter())
        if len(elements) > 100:
            raise ValueError("SVG selector exceeds element limit")
        rects = [element for element in elements if element.tag.rsplit("}", 1)[-1] == "rect"]
        if len(rects) != 1:
            raise ValueError("SVG selector must contain exactly one unambiguous rect")
        rect = rects[0]
        try:
            values = [float(rect.attrib[name]) for name in ("x", "y", "width", "height")]
        except (KeyError, ValueError) as exc:
            raise ValueError("SVG selector rect geometry is incomplete") from exc
        normalized = _bounded_geometry(values, asset.width, asset.height)
    else:
        raise ValueError(f"unsupported selector type: {selector.selector_type}")
    return replace(
        selector,
        asset_width=asset.width,
        asset_height=asset.height,
        normalized=normalized,
        validation_status="valid",
        selector_digest=canonical_digest(
            {
                "type": selector.selector_type,
                "original": selector.original,
                "asset_digest": asset.byte_digest,
                "dimensions": [asset.width, asset.height],
                "normalized": normalized,
            }
        ),
    )


def ingest_iiif3(
    manifest: Mapping[str, Any],
    *,
    object_id: str,
    rights: Mapping[str, Mapping[str, Any]],
    source_uri: str,
) -> tuple[MediaAssetRecord, ...]:
    """Ingest IIIF Presentation 3 canvases as separate, digest-bound assets."""

    if manifest.get("type") not in {"Manifest", "Collection"}:
        raise ValueError("IIIF Presentation 3 manifest type is required")
    assets: list[MediaAssetRecord] = []
    for index, canvas in enumerate(manifest.get("items", []), start=1):
        if not isinstance(canvas, Mapping):
            continue
        width = int(canvas.get("width") or 0)
        height = int(canvas.get("height") or 0)
        if width <= 0 or height <= 0:
            raise ValueError("IIIF canvas dimensions are required")
        canvas_id = str(canvas.get("id") or f"{source_uri}#canvas-{index}")
        asset_id = "asset-" + hashlib.sha256(canvas_id.encode("utf-8")).hexdigest()[:24]
        digest = str(canvas.get("byte_digest") or "")
        assets.append(
            MediaAssetRecord(
                asset_id=asset_id,
                object_id=object_id,
                role="surrogate",
                mime_type=str(canvas.get("mime_type") or "image/jpeg"),
                byte_size=int(canvas.get("byte_size") or 0),
                width=width,
                height=height,
                byte_digest=digest,
                acquisition_uri=str(canvas.get("service_id") or canvas_id),
                source_uri=source_uri,
                iiif_manifest_id=str(manifest.get("id") or source_uri),
                canvas_id=canvas_id,
                rights=rights,
            )
        )
    return tuple(assets)
