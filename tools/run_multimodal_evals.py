#!/usr/bin/env python3
"""Run the Research Grade multimodal evaluation through production interfaces.

The runner consumes a reviewed, checksummed case manifest.  It never infers a
case result from a fixture filename; expected fields and provider output are
the only inputs to each metric.  A missing locked corpus or live capability is
reported as ``NOT_RUN`` and never converted into a pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.image_analysis import (  # noqa: E402
    DeterministicFakeImageProvider,
    ImageAnalysisRequest,
    ImageAnalysisResult,
    OpenAIImageAnalysisProvider,
    evaluate_cross_modal_support,
)
from swos_runtime.media import AccessibilityRecord, MediaAssetRecord  # noqa: E402
from swos_runtime.models import canonical_digest  # noqa: E402

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


def _json_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _wilson(numerator: int, denominator: int) -> tuple[float | None, float | None]:
    if denominator <= 0:
        return None, None
    z = 1.96
    p = numerator / denominator
    divisor = 1 + (z * z / denominator)
    centre = (p + (z * z / (2 * denominator))) / divisor
    margin = z * math.sqrt((p * (1 - p) / denominator) + (z * z / (4 * denominator * denominator))) / divisor
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _metric(name: str, numerator: int, denominator: int, threshold: float, *, direction: str = "higher_is_better", extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    value = numerator / denominator if denominator else None
    lower, upper = _wilson(numerator, denominator)
    passed = bool(denominator) and ((value >= threshold) if direction == "higher_is_better" else (value <= threshold))
    result = {
        "metric": name,
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "threshold": threshold,
        "direction": direction,
        "confidence_interval": {"lower_95": lower, "upper_95": upper},
        "status": "evaluated" if denominator else "not_run",
        "passed": passed,
    }
    if extra:
        result.update(dict(extra))
    return result


def _asset_from_case(payload: Mapping[str, Any]) -> MediaAssetRecord:
    values = dict(payload)
    accessibility = values.get("accessibility")
    if isinstance(accessibility, Mapping):
        accessibility_values = dict(accessibility)
        accessibility_values.pop("valid", None)
        values["accessibility"] = AccessibilityRecord(**accessibility_values)
    elif accessibility is not None:
        values["accessibility"] = None
    values.pop("bytes", None)
    return MediaAssetRecord(**values)


def _request_from_case(case: Mapping[str, Any], assets: Sequence[MediaAssetRecord]) -> ImageAnalysisRequest:
    payload = dict(case.get("request") or {})
    return ImageAnalysisRequest(
        work_id=str(payload.get("work_id") or case.get("case_id") or "work"),
        run_id=str(payload.get("run_id") or case.get("case_id") or "run"),
        object_id=str(payload.get("object_id") or (assets[0].object_id if assets else "")),
        assets=tuple(assets),
        target_questions=tuple(str(item) for item in payload.get("target_questions") or ()),
        allowed_actions=tuple(str(item) for item in payload.get("allowed_actions") or ("analyse",)),
        discipline=str(payload.get("discipline") or "art_history"),
        ontology_binding=dict(payload.get("ontology_binding") or {}),
        resource_limits=dict(payload.get("resource_limits") or {"max_assets": 8, "max_observations": 64, "max_seconds": 60}),
        provider_policy=dict(payload.get("provider_policy") or {}),
        request_digest=str(payload.get("request_digest") or ""),
    )


def _result_payload(result: Any) -> dict[str, Any]:
    if isinstance(result, ImageAnalysisResult):
        return result.to_dict()
    if hasattr(result, "to_dict"):
        return dict(result.to_dict())
    return dict(result or {})


def _observation_regions(result: Mapping[str, Any]) -> set[tuple[str, tuple[int, ...]]]:
    regions: set[tuple[str, tuple[int, ...]]] = set()
    for observation in result.get("observations", []):
        if not isinstance(observation, Mapping):
            continue
        selector = observation.get("selector")
        if not isinstance(selector, Mapping):
            continue
        normalized = selector.get("normalized")
        if isinstance(normalized, (list, tuple)) and len(normalized) == 4:
            try:
                regions.add((str(observation.get("asset_id") or ""), tuple(int(value) for value in normalized)))
            except (TypeError, ValueError):
                continue
    return regions


def _expected_regions(expected: Mapping[str, Any]) -> set[tuple[str, tuple[int, ...]]]:
    values = expected.get("regions") or expected.get("expected_regions") or []
    regions: set[tuple[str, tuple[int, ...]]] = set()
    for item in values:
        if not isinstance(item, Mapping):
            continue
        normalized = item.get("normalized") or item.get("pixel_bounds")
        if isinstance(normalized, (list, tuple)) and len(normalized) == 4:
            try:
                regions.add((str(item.get("asset_id") or ""), tuple(int(value) for value in normalized)))
            except (TypeError, ValueError):
                continue
    return regions


def _cross_modal_counts(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, int]:
    expected = dict(case.get("expected") or {})
    pairs = expected.get("cross_modal_pairs") or case.get("cross_modal_pairs") or []
    counts = {"tp": 0, "fp": 0, "fn": 0}
    observations = result.get("observations", [])
    textual = case.get("textual_evidence") or []
    for pair in pairs:
        if not isinstance(pair, Mapping):
            continue
        claim = dict(pair.get("claim") or pair)
        support = evaluate_cross_modal_support(claim, observations, textual)
        expected_supported = bool(pair.get("expected_supported", pair.get("supported", pair.get("expected_status") == "supported")))
        predicted_supported = support.status == "supported"
        if predicted_supported and expected_supported:
            counts["tp"] += 1
        elif predicted_supported and not expected_supported:
            counts["fp"] += 1
        elif not predicted_supported and expected_supported:
            counts["fn"] += 1
    return counts


def _grounding_counts(case: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[int, int]:
    expected = dict(case.get("expected") or {})
    interpretations = expected.get("interpretations") or case.get("interpretations") or []
    if not interpretations:
        return 0, 0
    actual_ids = {
        str(item.get("observation_id") or "")
        for item in result.get("observations", [])
        if isinstance(item, Mapping)
    }
    grounded = 0
    for item in interpretations:
        if not isinstance(item, Mapping):
            continue
        observation_ids = {str(value) for value in item.get("observation_ids") or []}
        if observation_ids and observation_ids.issubset(actual_ids):
            grounded += 1
    return grounded, len([item for item in interpretations if isinstance(item, Mapping)])


def _safety_counts(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, int]:
    expected = dict(case.get("expected") or {})
    cases = expected.get("safety_cases") or case.get("safety_cases") or []
    counts = {"false_originality_detected": 0, "false_originality_total": 0, "over_association_detected": 0, "over_association_total": 0}
    observations = result.get("observations", [])
    textual = case.get("textual_evidence") or []
    for item in cases:
        if not isinstance(item, Mapping):
            continue
        claim = dict(item.get("claim") or item)
        support = evaluate_cross_modal_support(claim, observations, textual)
        unsafe = bool(item.get("unsafe", item.get("adversarial", True)))
        if not unsafe:
            continue
        kind = str(item.get("kind") or item.get("category") or "false_originality").lower()
        key = "over_association" if "over" in kind else "false_originality"
        counts[key + "_total"] += 1
        if support.status in {"blocked", "limited"}:
            counts[key + "_detected"] += 1
    return counts


def _case_evaluation(case: Mapping[str, Any], provider: Any, repetitions: int) -> tuple[dict[str, Any], dict[str, int]]:
    assets = tuple(_asset_from_case(item) for item in case.get("assets", []) if isinstance(item, Mapping))
    request = _request_from_case(case, assets)
    outputs: list[dict[str, Any]] = []
    errors: list[str] = []
    for _ in range(max(1, repetitions)):
        try:
            outputs.append(_result_payload(provider.analyze(request)))
        except Exception as exc:  # provider failures are an explicit case result
            errors.append(type(exc).__name__)
            outputs.append({"status": "error", "contract_status": "error", "limitations": [f"provider_error:{type(exc).__name__}"]})
    actual = outputs[0]
    expected = dict(case.get("expected") or {})
    actual_status = str(actual.get("status") or "error")
    expected_status = str(expected.get("status") or "")
    agreement = bool(expected_status) and actual_status == expected_status
    expected_regions = _expected_regions(expected)
    actual_regions = _observation_regions(actual)
    region_hits = len(expected_regions & actual_regions)
    cross_counts = _cross_modal_counts(case, actual)
    grounding_numerator, grounding_denominator = _grounding_counts(case, actual)
    safety_counts = _safety_counts(case, actual)
    required_accessibility = 0
    valid_accessibility = 0
    for index, asset in enumerate(assets):
        required = bool(expected.get("accessibility_required", False))
        asset_expectations = expected.get("asset_expectations") or []
        if index < len(asset_expectations) and isinstance(asset_expectations[index], Mapping):
            required = bool(asset_expectations[index].get("accessibility_required", required))
        if required and asset.role != "generated":
            required_accessibility += 1
            if asset.accessibility is not None and asset.accessibility.valid:
                valid_accessibility += 1
    result = {
        "case_id": str(case.get("case_id") or ""),
        "request_digest": request.request_digest,
        "expected": expected,
        "result": actual,
        "repeated_results": outputs,
        "provider_errors": errors,
        "checks": {
            "agreement": agreement,
            "region_hits": region_hits,
            "region_expected": len(expected_regions),
            "stability": all(output == outputs[0] for output in outputs[1:]),
            "valid_accessibility": valid_accessibility,
            "required_accessibility": required_accessibility,
        },
    }
    return result, {
        "agreement_numerator": int(agreement),
        "agreement_denominator": int(bool(expected_status)),
        "region_numerator": region_hits,
        "region_denominator": len(expected_regions),
        "grounding_numerator": grounding_numerator,
        "grounding_denominator": grounding_denominator,
        "false_region_numerator": len(actual_regions - expected_regions),
        "false_region_denominator": len(actual_regions),
        "stability_numerator": int(all(output == outputs[0] for output in outputs[1:])),
        "stability_denominator": 1,
        "cross_tp": cross_counts["tp"],
        "cross_fp": cross_counts["fp"],
        "cross_fn": cross_counts["fn"],
        "false_originality_detected": safety_counts["false_originality_detected"],
        "false_originality_total": safety_counts["false_originality_total"],
        "over_association_detected": safety_counts["over_association_detected"],
        "over_association_total": safety_counts["over_association_total"],
        "valid_accessibility": valid_accessibility,
        "required_accessibility": required_accessibility,
    }


def _head_sha(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unreported"


def evaluate_multimodal_cases(cases: Sequence[Mapping[str, Any]], *, provider: Any, repetitions: int = 3, source_sha: str | None = None, minimums: Mapping[str, int] | None = None) -> dict[str, Any]:
    raw_results: list[dict[str, Any]] = []
    totals = {"agreement_numerator": 0, "agreement_denominator": 0, "region_numerator": 0, "region_denominator": 0, "grounding_numerator": 0, "grounding_denominator": 0, "false_region_numerator": 0, "false_region_denominator": 0, "stability_numerator": 0, "stability_denominator": 0, "cross_tp": 0, "cross_fp": 0, "cross_fn": 0, "false_originality_detected": 0, "false_originality_total": 0, "over_association_detected": 0, "over_association_total": 0, "valid_accessibility": 0, "required_accessibility": 0}
    for case in cases:
        result, counts = _case_evaluation(case, provider, repetitions)
        raw_results.append(result)
        for key in totals:
            totals[key] += counts[key]
    precision_denominator = totals["cross_tp"] + totals["cross_fp"]
    recall_denominator = totals["cross_tp"] + totals["cross_fn"]
    f1_denominator = 2 * totals["cross_tp"] + totals["cross_fp"] + totals["cross_fn"]
    metrics: dict[str, Any] = {
        "agreement": _metric("agreement", totals["agreement_numerator"], totals["agreement_denominator"], 1.0),
        "region_hit": _metric("region_hit", totals["region_numerator"], totals["region_denominator"], 0.90),
        "visual_grounding_coverage": _metric("visual_grounding_coverage", totals["grounding_numerator"], totals["grounding_denominator"], 1.0),
        "false_region": _metric("false_region", totals["false_region_numerator"], totals["false_region_denominator"], 0.02, direction="lower_is_better"),
        "cross_modal_precision": _metric("cross_modal_precision", totals["cross_tp"], precision_denominator, 0.98),
        "cross_modal_recall": _metric("cross_modal_recall", totals["cross_tp"], recall_denominator, 0.90),
        "cross_modal_f1": _metric("cross_modal_f1", 2 * totals["cross_tp"], f1_denominator, 0.94, extra={"true_positive": totals["cross_tp"], "false_positive": totals["cross_fp"], "false_negative": totals["cross_fn"]}),
        "false_originality_detection": _metric("false_originality_detection", totals["false_originality_detected"], totals["false_originality_total"], 1.0),
        "over_association_detection": _metric("over_association_detection", totals["over_association_detected"], totals["over_association_total"], 1.0),
        "valid_reviewed_accessibility_completeness": _metric("valid_reviewed_accessibility_completeness", totals["valid_accessibility"], totals["required_accessibility"], 1.0),
        "stability": _metric("stability", totals["stability_numerator"], totals["stability_denominator"], 1.0),
    }
    object_ids = {str(case.get("object", {}).get("object_id") or asset.get("object_id") or "") for case in cases for asset in case.get("assets", []) if isinstance(asset, Mapping)}
    asset_ids = {str(asset.get("asset_id") or "") for case in cases for asset in case.get("assets", []) if isinstance(asset, Mapping)}
    minimums = dict(minimums or {})
    required_objects = int(minimums.get("objects", 0))
    required_renditions = int(minimums.get("renditions", 0))
    metrics["object_minimum"] = _metric("object_minimum", len(object_ids), required_objects, 1.0) if required_objects else {"metric": "object_minimum", "numerator": len(object_ids), "denominator": 0, "value": None, "threshold": 0, "status": "not_applicable", "passed": True}
    metrics["rendition_minimum"] = _metric("rendition_minimum", len(asset_ids), required_renditions, 1.0) if required_renditions else {"metric": "rendition_minimum", "numerator": len(asset_ids), "denominator": 0, "value": None, "threshold": 0, "status": "not_applicable", "passed": True}
    metrics["regression"] = {"metric": "regression", "numerator": 0, "denominator": 0, "value": None, "threshold": 0, "status": "not_run", "passed": False, "reason": "no_baseline_supplied"}
    blocking_metrics = [name for name, value in metrics.items() if value.get("status") != "not_applicable" and not value.get("passed")]
    return {
        "schema_version": "2.0.0",
        "status": "evaluated",
        "gate_result": "pass" if not blocking_metrics and raw_results else "fail",
        "source_sha": _head_sha(source_sha),
        "provider": type(provider).__name__,
        "case_count": len(raw_results),
        "raw_case_results": raw_results,
        "metrics": metrics,
        "blocking_metrics": blocking_metrics,
        "limitations": ["regression baseline not supplied"] if "regression" in blocking_metrics else [],
        "input_digest": canonical_digest({"cases": list(cases), "repetitions": repetitions, "minimums": minimums}),
    }


def _not_run_report(manifest: Mapping[str, Any], *, reason: str, source_sha: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "2.0.0",
        "status": "NOT_RUN",
        "gate_result": "NOT_RUN",
        "source_sha": _head_sha(source_sha),
        "manifest_digest": canonical_digest(manifest),
        "reason": reason,
        "raw_case_results": [],
        "metrics": {"stability": {"metric": "stability", "numerator": 0, "denominator": 0, "value": None, "threshold": 1.0, "status": "not_run", "passed": False}},
        "blocking_metrics": ["locked_multimodal_corpus"],
        "limitations": [reason],
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run_evals(manifest_path: str | Path, artifact_dir: str | Path, *, provider: Any | None = None, repetitions: int = 3, source_sha: str | None = None, require_live: bool = False) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    artifact_root = Path(artifact_dir)
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = _not_run_report({}, reason=f"NOT_RUN: manifest unavailable: {exc}", source_sha=source_sha)
        _write_json(artifact_root / "multimodal-evaluation-report.json", report)
        return report
    if str(manifest.get("status") or "").lower() != "ready" or not manifest.get("cases"):
        report = _not_run_report(manifest, reason=str(manifest.get("reason") or "NOT_RUN: a locked reviewed corpus is required"), source_sha=source_sha)
        _write_json(artifact_root / "multimodal-evaluation-report.json", report)
        return report
    if require_live and provider is None:
        report = _not_run_report(manifest, reason="NOT_RUN: live provider capability is not supplied", source_sha=source_sha)
        _write_json(artifact_root / "multimodal-evaluation-report.json", report)
        return report
    selected_provider = provider or DeterministicFakeImageProvider()
    report = evaluate_multimodal_cases(manifest.get("cases") or [], provider=selected_provider, repetitions=repetitions, source_sha=source_sha, minimums=manifest.get("required_counts"))
    _write_json(artifact_root / "raw-case-results.json", {"schema_version": "2.0.0", "source_sha": report["source_sha"], "cases": report["raw_case_results"]})
    report["artifact_identities"] = {"raw-case-results.json": _json_digest({"schema_version": "2.0.0", "source_sha": report["source_sha"], "cases": report["raw_case_results"]}), "manifest": _json_digest(manifest)}
    _write_json(artifact_root / "multimodal-evaluation-report.json", report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts/multimodal"))
    parser.add_argument("--provider", choices=("fake", "openai"), default="fake")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args(argv)
    provider = None
    if args.provider == "fake" and not args.live:
        provider = DeterministicFakeImageProvider()
    elif args.provider == "openai":
        provider = OpenAIImageAnalysisProvider(enabled=args.live)
    report = run_evals(args.manifest, args.artifact_dir, provider=provider, repetitions=args.repetitions, require_live=args.live and args.provider == "openai")
    return 0 if report.get("gate_result") == "pass" else (2 if report.get("status") == "NOT_RUN" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
