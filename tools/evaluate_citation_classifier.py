"""Evaluate a verified citation artifact on a locked split without mutation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_calibration import (  # noqa: E402
    expected_calibration_error,
    metric_confidence_interval,
)
from swos_runtime.citation_classifier import (  # noqa: E402
    LABELS,
    CitationPair,
    CitationSupportClassifier,
    VerifiedCalibration,
    VerifiedModelArtifact,
)
from swos_runtime.models import canonical_digest, utc_timestamp  # noqa: E402

EVALUATOR_VERSION = "2.0.0"
LATENCY_SAMPLE_SIZE = 100
LATENCY_LIMIT_SECONDS = 5.0
LATENCY_LIMIT_MS = LATENCY_LIMIT_SECONDS * 1000.0
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class EvaluationBlocked(RuntimeError):
    """Raised when a locked evaluation cannot produce governed evidence."""


def _load_json(path: Path | str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationBlocked(f"evaluation input is unreadable: {path}") from exc


def _require_sha256(value: Any, field: str) -> str:
    text = str(value or "").lower()
    if not SHA256_RE.fullmatch(text):
        raise EvaluationBlocked(f"{field} must be a lowercase SHA-256 digest")
    return text


def _load_model(path: Path | str) -> tuple[VerifiedModelArtifact, dict[str, Any]]:
    manifest_path = Path(path)
    payload = _load_json(manifest_path)
    if not isinstance(payload, Mapping):
        raise EvaluationBlocked("model manifest must be an object")
    if payload.get("status") != "frozen" or payload.get("verified") is not True:
        raise EvaluationBlocked("verified frozen model manifest is required")
    artifact_path = payload.get("artifact_path")
    if artifact_path and not Path(str(artifact_path)).is_absolute():
        artifact_path = str((manifest_path.parent / str(artifact_path)).resolve())
    try:
        model = VerifiedModelArtifact(
            model_id=str(payload.get("model_id") or payload.get("artifact_id") or ""),
            model_digest=_require_sha256(payload.get("model_digest"), "model_digest"),
            label_order=tuple(payload.get("label_order") or ()),
            version=str(payload.get("version") or "1.0.0"),
            artifact_path=str(artifact_path) if artifact_path else None,
            config_digest=str(payload.get("config_digest") or ""),
            dataset_manifest_digest=_require_sha256(
                payload.get("dataset_manifest_digest"), "dataset_manifest_digest"
            ),
            verified=True,
            metadata=dict(payload),
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise EvaluationBlocked(f"model manifest fields are invalid: {exc}") from exc
    try:
        model.verify()
    except (OSError, ValueError) as exc:
        raise EvaluationBlocked(f"model manifest verification failed: {exc}") from exc
    return model, dict(payload)


def _load_calibration(
    path: Path | str, *, model: VerifiedModelArtifact, ontology_version: str
) -> tuple[VerifiedCalibration, dict[str, Any]]:
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        raise EvaluationBlocked("calibration manifest must be an object")
    if payload.get("status") != "frozen" or payload.get("verified") is not True:
        raise EvaluationBlocked("verified frozen calibration is required")
    if payload.get("locked_test_used") is not False:
        raise EvaluationBlocked("calibration artifact must prove locked-test isolation")
    try:
        calibration = VerifiedCalibration(
            calibration_id=str(payload.get("calibration_id") or ""),
            model_digest=_require_sha256(payload.get("model_digest"), "calibration model_digest"),
            dataset_manifest_digest=_require_sha256(
                payload.get("dataset_manifest_digest"), "calibration dataset_manifest_digest"
            ),
            ontology_digest=_require_sha256(
                payload.get("ontology_digest"), "calibration ontology_digest"
            ),
            label_order=tuple(payload.get("label_order") or ()),
            temperature=float(payload.get("temperature")),
            thresholds=dict(payload.get("thresholds") or {}),
            verified=True,
            calibration_digest=_require_sha256(
                payload.get("calibration_digest"), "calibration_digest"
            ),
            metadata=dict(payload),
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise EvaluationBlocked(f"calibration manifest fields are invalid: {exc}") from exc
    try:
        ece = float(payload["ece"])
        calibration_split_digest = _require_sha256(
            payload["calibration_split_digest"], "calibration_split_digest"
        )
        thresholds = {
            str(label): float(value)
            for label, value in dict(payload["thresholds"]).items()
        }
    except (TypeError, ValueError, KeyError) as exc:
        raise EvaluationBlocked("calibration manifest digest fields are invalid") from exc
    if not math.isfinite(ece) or not 0 <= ece <= 1:
        raise EvaluationBlocked("calibration ECE must be finite and within [0, 1]")
    if set(thresholds) != set(LABELS):
        raise EvaluationBlocked("calibration thresholds must cover the frozen five labels")
    expected_calibration_digest = canonical_digest(
        {
            "calibration_id": calibration.calibration_id,
            "model_digest": calibration.model_digest,
            "dataset_manifest_digest": calibration.dataset_manifest_digest,
            "ontology_digest": calibration.ontology_digest,
            "label_order": list(calibration.label_order),
            "temperature": calibration.temperature,
            "thresholds": dict(sorted(thresholds.items())),
            "ece": ece,
            "calibration_split_digest": calibration_split_digest,
            "locked_test_used": False,
        }
    )
    if calibration.calibration_digest != expected_calibration_digest:
        raise EvaluationBlocked("calibration digest does not match its immutable fields")
    if calibration.dataset_manifest_digest != model.dataset_manifest_digest:
        raise EvaluationBlocked("model/calibration dataset manifest digests do not match")
    model_ontology_digest = _require_sha256(
        model.metadata.get("ontology_digest"), "model ontology_digest"
    )
    if calibration.ontology_digest != model_ontology_digest:
        raise EvaluationBlocked("model/calibration ontology digests do not match")
    try:
        calibration.verify(model=model, ontology_version=ontology_version)
    except (OSError, TypeError, ValueError) as exc:
        raise EvaluationBlocked(f"calibration verification failed: {exc}") from exc
    return calibration, dict(payload)


def _read_rows(path: Path | str) -> list[dict[str, Any]]:
    source = Path(path)
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EvaluationBlocked(f"locked test is unreadable: {source}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvaluationBlocked(f"locked test line {line_number} is invalid JSON") from exc
        if not isinstance(item, Mapping):
            raise EvaluationBlocked(f"locked test line {line_number} is not an object")
        rows.append(dict(item))
    if not rows:
        raise EvaluationBlocked("locked test is empty")
    return rows


def _row_label(row: Mapping[str, Any]) -> str:
    label = row.get("label")
    adjudication = row.get("adjudication")
    if not label and isinstance(adjudication, Mapping):
        label = adjudication.get("label")
    if str(label) not in LABELS:
        raise EvaluationBlocked(f"pair {row.get('pair_id', '<unknown>')} has an invalid label")
    return str(label)


def _pair_from_row(row: Mapping[str, Any]) -> CitationPair:
    pair_id = row.get("pair_id")
    claim = row.get("claim")
    exact_quote = row.get("exact_quote", row.get("passage", ""))
    if not isinstance(pair_id, str) or not pair_id.strip():
        raise EvaluationBlocked("locked-test pair_id must be a non-empty string")
    if not isinstance(claim, str) or not claim:
        raise EvaluationBlocked(f"pair {pair_id} claim must be a non-empty exact string")
    if not isinstance(exact_quote, str):
        raise EvaluationBlocked(f"pair {pair_id} exact_quote must be an exact string")
    passage = row.get("passage", exact_quote)
    if not isinstance(passage, str):
        raise EvaluationBlocked(f"pair {pair_id} passage must be an exact string")
    return CitationPair(
        pair_id=pair_id,
        claim=claim,
        passage=passage,
        context=str(row.get("context") or ""),
        source_id=str(row.get("source_id") or ""),
        exact_quote=exact_quote,
        span_start=row.get("span_start"),
        span_end=row.get("span_end"),
        discipline_iri=str(row.get("discipline_iri") or ""),
        method_iri=str(row.get("method_iri") or ""),
        source_role_iri=str(row.get("source_role_iri") or ""),
        rights_disposition=str(row.get("rights_disposition") or "permitted"),
        source_digest=str(row.get("source_digest") or ""),
    )


def _prediction_mode(rows: Sequence[Mapping[str, Any]]) -> str:
    has_logits = ["logits" in row for row in rows]
    has_probabilities = ["probabilities" in row for row in rows]
    if any(logit and probability for logit, probability in zip(has_logits, has_probabilities)):
        raise EvaluationBlocked("each locked-test row must provide logits or probabilities, not both")
    if len(set(has_logits)) != 1 or len(set(has_probabilities)) != 1:
        raise EvaluationBlocked("locked-test prediction representation must be consistent")
    if has_logits[0]:
        return "logits"
    if has_probabilities[0]:
        return "probabilities"
    raise EvaluationBlocked("verified model predictions are absent from the locked test")


def _abstention_required(row: Mapping[str, Any], ontology_version: str) -> bool:
    declared_version = row.get("ontology_version")
    return (
        row.get("ood") is True
        or row.get("unsupported_version") is True
        or (declared_version is not None and str(declared_version) != ontology_version)
    )


def _code_sha() -> str:
    for candidate in (os.environ.get("SWOS_CODE_SHA"), os.environ.get("GITHUB_SHA")):
        if candidate and GIT_SHA_RE.fullmatch(candidate.lower()):
            return candidate.lower()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvaluationBlocked("evaluation code SHA is unavailable") from exc
    value = result.stdout.strip().lower()
    if not GIT_SHA_RE.fullmatch(value):
        raise EvaluationBlocked("evaluation code SHA is not a 40-character commit identity")
    return value


def _metric(successes: int, total: int) -> dict[str, Any]:
    if total <= 0:
        return {
            "successes": successes,
            "total": total,
            "value": None,
            "lower_95": None,
            "upper_95": None,
        }
    value = successes / total
    lower, upper = metric_confidence_interval(successes, total)
    return {
        "successes": successes,
        "total": total,
        "value": value,
        "lower_95": lower,
        "upper_95": upper,
    }


def _f1(precision: float | None, recall: float | None) -> float:
    if precision is None or recall is None or precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _label_statistics(gold: Sequence[str], predicted: Sequence[str | None]) -> dict[str, dict[str, Any]]:
    statistics: dict[str, dict[str, Any]] = {}
    for label in LABELS:
        true_positive = sum(actual == label and guess == label for actual, guess in zip(gold, predicted))
        false_positive = sum(actual != label and guess == label for actual, guess in zip(gold, predicted))
        false_negative = sum(actual == label and guess != label for actual, guess in zip(gold, predicted))
        precision = _metric(true_positive, true_positive + false_positive)
        recall = _metric(true_positive, true_positive + false_negative)
        statistics[label] = {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": precision,
            "recall": recall,
            "f1": _f1(precision["value"], recall["value"]),
        }
    return statistics


def _metrics(
    rows: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    *,
    abstention_required: Sequence[bool],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(abstention_required) != len(rows):
        raise EvaluationBlocked("abstention safety flags do not match the locked-test size")
    gold = [_row_label(row) for row in rows]
    predicted = [
        record["support_level"] if record.get("status") == "classified" else None
        for record in records
    ]
    label_statistics = _label_statistics(gold, predicted)
    macro_f1 = sum(item["f1"] for item in label_statistics.values()) / len(LABELS)
    direct = label_statistics["directly_supports"]
    contradiction = label_statistics["contradicts"]
    not_supported = label_statistics["not_supported"]
    selected = [index for index, value in enumerate(predicted) if value in LABELS]
    selected_errors = sum(predicted[index] != gold[index] for index in selected)
    probabilities = [record["probabilities"] for record in records]
    ece = expected_calibration_error(probabilities, gold)
    unsupported_auto_admission = _metric(
        sum(actual == "not_supported" and guess == "directly_supports" for actual, guess in zip(gold, predicted)),
        sum(actual == "not_supported" for actual in gold),
    )
    safety_indexes = [
        index for index, required in enumerate(abstention_required) if required
    ]
    safety_abstentions = sum(
        records[index].get("status") == "abstained"
        and records[index].get("support_level") is None
        for index in safety_indexes
    )
    metrics = {
        "sample_count": len(rows),
        "macro_f1": macro_f1,
        "direct_support_precision": direct["precision"],
        "contradiction_recall": contradiction["recall"],
        "not_supported_recall": not_supported["recall"],
        "expected_calibration_error": ece,
        "selective_coverage": _metric(len(selected), len(rows)),
        "selective_error": _metric(selected_errors, len(selected)),
        "unsupported_auto_admission": unsupported_auto_admission,
        "ood_or_unsupported_version_abstention": _metric(
            safety_abstentions, len(safety_indexes)
        ),
        "per_label": label_statistics,
    }

    discipline_slices: dict[str, Any] = {}
    for discipline in sorted({str(row.get("discipline") or "unknown") for row in rows}):
        indexes = [
            index
            for index, row in enumerate(rows)
            if str(row.get("discipline") or "unknown") == discipline
        ]
        slice_gold = [gold[index] for index in indexes]
        slice_predicted = [predicted[index] for index in indexes]
        slice_statistics = _label_statistics(slice_gold, slice_predicted)
        slice_direct = slice_statistics["directly_supports"]["precision"]
        discipline_slices[discipline] = {
            "count": len(indexes),
            "macro_f1": sum(item["f1"] for item in slice_statistics.values()) / len(LABELS),
            "direct_support_precision": slice_direct,
            "contradiction_recall": slice_statistics["contradicts"]["recall"],
        }

    label_slices = {
        label: {
            "count": gold.count(label),
            "recall": label_statistics[label]["recall"],
            "f1": label_statistics[label]["f1"],
        }
        for label in LABELS
    }
    return metrics, {"discipline": discipline_slices, "support_label": label_slices}


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise EvaluationBlocked("latency sample is empty")
    position = (len(ordered) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _latency(
    classifier: CitationSupportClassifier,
    pairs: Sequence[CitationPair],
    rows: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    code_sha: str,
    abstention_required: Sequence[bool],
) -> dict[str, Any]:
    if len(pairs) < LATENCY_SAMPLE_SIZE or len(abstention_required) != len(pairs):
        raise EvaluationBlocked("locked test must contain at least 100 pairs for latency evidence")
    samples: list[float] = []
    for index in range(LATENCY_SAMPLE_SIZE):
        started = time.perf_counter()
        if mode == "logits":
            classifier.classify(
                [pairs[index]], logits=[rows[index]["logits"]], ood=[abstention_required[index]]
            )
        else:
            classifier.classify(
                [pairs[index]],
                probabilities=[rows[index]["probabilities"]],
                ood=[abstention_required[index]],
            )
        samples.append((time.perf_counter() - started) * 1000)
    p95 = _percentile(samples, 95)
    runner = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "code_sha": code_sha,
    }
    return {
        "sample_count": LATENCY_SAMPLE_SIZE,
        "sample_pair_digest": canonical_digest([pairs[index].pair_id for index in range(LATENCY_SAMPLE_SIZE)]),
        "sample_input_digest": canonical_digest(
            [pairs[index].to_dict() for index in range(LATENCY_SAMPLE_SIZE)]
        ),
        "samples_ms": [round(value, 6) for value in samples],
        "p95_ms": round(p95, 6),
        "p95_seconds": round(p95 / 1000.0, 6),
        "threshold_ms": LATENCY_LIMIT_MS,
        "threshold_seconds": LATENCY_LIMIT_SECONDS,
        "gate_pass": p95 <= LATENCY_LIMIT_MS,
        "runner": runner,
        "measurement": "one isolated classifier invocation per pair; linear-interpolated p95",
    }


def _gate_report(metrics: Mapping[str, Any], slices: Mapping[str, Any], latency: Mapping[str, Any]) -> dict[str, Any]:
    direct = metrics["direct_support_precision"]
    contradiction = metrics["contradiction_recall"]
    not_supported = metrics["not_supported_recall"]
    ece = metrics["expected_calibration_error"]
    coverage = metrics["selective_coverage"]
    selective_error = metrics["selective_error"]
    unsupported = metrics["unsupported_auto_admission"]
    safety = metrics["ood_or_unsupported_version_abstention"]
    discipline_values = list(slices["discipline"].values())
    discipline_direct = [item["direct_support_precision"] for item in discipline_values]

    def value_pass(metric: Mapping[str, Any], threshold: float, *, minimum: bool = True) -> bool:
        value = metric.get("value")
        return value is not None and (value >= threshold if minimum else value <= threshold)

    gates = {
        "direct_support_precision": {
            "observed": direct["value"],
            "required": 0.95,
            "pass": value_pass(direct, 0.95)
            and direct["lower_95"] is not None
            and direct["lower_95"] >= 0.98,
            "lower_95_required": 0.98,
            "lower_95_pass": direct["lower_95"] is not None and direct["lower_95"] >= 0.98,
        },
        "contradiction_recall": {
            "observed": contradiction["value"],
            "required": 0.95,
            "pass": value_pass(contradiction, 0.95),
        },
        "not_supported_recall": {
            "observed": not_supported["value"],
            "required": 0.90,
            "pass": value_pass(not_supported, 0.90),
        },
        "macro_f1": {
            "observed": metrics["macro_f1"],
            "required": 0.85,
            "pass": metrics["macro_f1"] >= 0.85,
        },
        "expected_calibration_error": {
            "observed": ece,
            "required": 0.05,
            "pass": ece <= 0.05,
        },
        "selective_error": {
            "observed": selective_error["value"],
            "required": 0.02,
            "pass": value_pass(selective_error, 0.02, minimum=False),
        },
        "selective_coverage": {
            "observed": coverage["value"],
            "required": 0.70,
            "pass": value_pass(coverage, 0.70),
        },
        "unsupported_auto_admission": {
            "observed": unsupported["value"],
            "upper_95": unsupported["upper_95"],
            "required_upper_95": 0.01,
            "pass": unsupported["upper_95"] is not None and unsupported["upper_95"] <= 0.01,
        },
        "ood_or_unsupported_version_abstention": {
            "observed": safety["value"],
            "required": 0.95,
            "applicable": safety["total"] > 0,
            "pass": safety["total"] == 0 or value_pass(safety, 0.95),
        },
        "discipline_macro_f1": {
            "observed_minimum": min(
                (item["macro_f1"] for item in discipline_values), default=None
            ),
            "required": 0.75,
            "pass": bool(discipline_values)
            and all(item["macro_f1"] >= 0.75 for item in discipline_values),
        },
        "discipline_direct_support_precision": {
            "observed_minimum": min((item["value"] or 0.0 for item in discipline_direct), default=None),
            "required": 0.95,
            "pass": bool(discipline_direct)
            and all(value_pass(item, 0.95) for item in discipline_direct),
        },
        "latency": {
            "observed_p95_ms": latency["p95_ms"],
            "required_p95_ms": LATENCY_LIMIT_MS,
            "pass": latency["gate_pass"],
        },
    }
    return {
        "gates": gates,
        "pass": all(item["pass"] for item in gates.values()),
    }


def _decorate_decision(
    decision: Any,
    pair: CitationPair,
    *,
    code_sha: str,
    config_digest: str,
    execution_id: str,
    execution_timestamp: str,
    locked_digest: str,
    model_manifest_digest: str,
) -> dict[str, Any]:
    record = decision.to_dict()
    if (
        record.get("pair_id") != pair.pair_id
        or record.get("input", {}).get("claim") != pair.claim
        or record.get("input", {}).get("exact_quote") != pair.exact_quote
        or record.get("input", {}).get("input_digest") != pair.canonical_input_digest
        or record.get("input_digest") != pair.canonical_input_digest
    ):
        raise EvaluationBlocked(f"classifier changed immutable input identity for pair {pair.pair_id}")
    record["provenance"] = {
        **dict(record.get("provenance") or {}),
        "code_sha": code_sha,
        "config_digest": config_digest,
        "execution_id": execution_id,
        "execution_timestamp": execution_timestamp,
        "evaluator_version": EVALUATOR_VERSION,
        "locked_test_digest": locked_digest,
        "model_manifest_digest": model_manifest_digest,
        "claim_digest": hashlib.sha256(pair.claim.encode("utf-8")).hexdigest(),
        "span_digest": hashlib.sha256((pair.exact_quote or "").encode("utf-8")).hexdigest(),
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "backend": "CitationSupportClassifier/offline-injected",
    }
    return record


def evaluate(
    model_manifest_path: Path | str,
    calibration_path: Path | str,
    locked_test_path: Path | str,
    predictions_path: Path | str,
    report_path: Path | str,
) -> dict[str, Any]:
    predictions_path = Path(predictions_path)
    report_path = Path(report_path)
    if predictions_path.resolve() == report_path.resolve():
        raise RuntimeError("predictions and report outputs must be distinct immutable files")
    for path in (predictions_path, report_path):
        if path.exists():
            raise RuntimeError(f"immutable evaluation output already exists: {path}")
    try:
        model, model_payload = _load_model(model_manifest_path)
        ontology_version = str(model_payload.get("ontology_version") or "2.0.0")
        calibration, calibration_payload = _load_calibration(
            calibration_path, model=model, ontology_version=ontology_version
        )
        rows = _read_rows(locked_test_path)
        pairs = [_pair_from_row(row) for row in rows]
        mode = _prediction_mode(rows)
        abstention_required = [
            _abstention_required(row, ontology_version) for row in rows
        ]
        code_sha = _code_sha()
        locked_digest = canonical_digest(rows)
        model_manifest_digest = canonical_digest(model_payload)
        config_digest = canonical_digest(
            {
                "evaluator_version": EVALUATOR_VERSION,
                "label_order": list(LABELS),
                "mode": mode,
                "model_config_digest": model.config_digest,
                "calibration_digest": calibration.calibration_digest,
                "ontology_version": ontology_version,
                "ontology_digest": calibration.ontology_digest,
            }
        )
        execution_id = "citation-eval-" + canonical_digest(
            {
                "code_sha": code_sha,
                "config_digest": config_digest,
                "locked_digest": locked_digest,
                "model_manifest_digest": model_manifest_digest,
                "calibration_manifest_digest": canonical_digest(calibration_payload),
            }
        )[:24]
        execution_timestamp = utc_timestamp()
        classifier = CitationSupportClassifier(
            model=model,
            calibration=calibration,
            ontology_version=ontology_version,
            ontology_digest=calibration.ontology_digest,
        )
        if mode == "logits":
            decisions = classifier.classify(
                pairs,
                logits=[row["logits"] for row in rows],
                ood=abstention_required,
            )
        else:
            decisions = classifier.classify(
                pairs,
                probabilities=[row["probabilities"] for row in rows],
                ood=abstention_required,
            )
        if len(decisions) != len(pairs):
            raise EvaluationBlocked("classifier returned an incomplete decision set")
        records = [
            _decorate_decision(
                decision,
                pair,
                code_sha=code_sha,
                config_digest=config_digest,
                execution_id=execution_id,
                execution_timestamp=execution_timestamp,
                locked_digest=locked_digest,
                model_manifest_digest=model_manifest_digest,
            )
            for decision, pair in zip(decisions, pairs)
        ]
        metrics, slices = _metrics(
            rows, records, abstention_required=abstention_required
        )
        latency = _latency(
            classifier,
            pairs,
            rows,
            mode=mode,
            code_sha=code_sha,
            abstention_required=abstention_required,
        )
        gates = _gate_report(metrics, slices, latency)
        result = {
            "schema_version": "2.0.0",
            "status": "frozen" if gates["pass"] else "blocked",
            "gate_result": "pass" if gates["pass"] else "fail",
            "locked_test_count": len(rows),
            "model_manifest_digest": model_manifest_digest,
            "model_digest": model.model_digest,
            "calibration_digest": calibration.calibration_digest,
            "dataset_manifest_digest": model.dataset_manifest_digest,
            "ontology_version": ontology_version,
            "ontology_digest": calibration.ontology_digest,
            "locked_test_digest": locked_digest,
            "code_sha": code_sha,
            "config_digest": config_digest,
            "execution_id": execution_id,
            "execution_timestamp": execution_timestamp,
            "inference_mode": mode,
            "metrics": metrics,
            "slices": slices,
            "latency": latency,
            "gates": gates,
        }
    except EvaluationBlocked as exc:
        records = []
        result = {
            "schema_version": "2.0.0",
            "status": "not_run",
            "gate_result": "not_run",
            "reason": str(exc),
            "locked_test_count": 0,
        }

    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    report_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--locked-test", type=Path, required=True)
    parser.add_argument("--predictions-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = evaluate(
            args.model_manifest,
            args.calibration,
            args.locked_test,
            args.predictions_out,
            args.report_out,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "not_run", "reason": str(exc)}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("status") == "frozen" else 2


if __name__ == "__main__":
    raise SystemExit(main())
