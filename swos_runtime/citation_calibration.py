"""Deterministic calibration and selective-prediction utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .citation_classifier import LABELS
from .models import canonical_digest, utc_timestamp


class CalibrationBindingError(ValueError):
    """Raised when a calibration artifact is used with different inputs."""


def _label_index(value: Any) -> int:
    if isinstance(value, int):
        if 0 <= value < len(LABELS):
            return value
    if str(value) in LABELS:
        return LABELS.index(str(value))
    raise CalibrationBindingError(f"unknown support label {value!r}")


def _probability_rows(probabilities: Sequence[Mapping[str, float] | Sequence[float]]) -> list[list[float]]:
    rows: list[list[float]] = []
    for row in probabilities:
        if isinstance(row, Mapping):
            values = [float(row.get(label, 0.0)) for label in LABELS]
        else:
            values = [float(value) for value in row]
        if len(values) != len(LABELS) or not all(math.isfinite(value) and value >= 0 for value in values):
            raise CalibrationBindingError("probability rows must contain five finite nonnegative values")
        total = sum(values)
        if total <= 0:
            raise CalibrationBindingError("probability row has no mass")
        rows.append([value / total for value in values])
    return rows


def expected_calibration_error(
    probabilities: Sequence[Mapping[str, float] | Sequence[float]],
    labels: Sequence[Any],
    *,
    bins: int = 10,
) -> float:
    rows = _probability_rows(probabilities)
    if len(rows) != len(labels) or bins <= 0:
        raise CalibrationBindingError("ECE inputs are malformed")
    total = len(rows)
    error = 0.0
    for bucket in range(bins):
        lower = bucket / bins
        upper = (bucket + 1) / bins
        selected = [index for index, row in enumerate(rows) if lower <= max(row) < upper or (bucket == bins - 1 and max(row) == upper)]
        if not selected:
            continue
        accuracy = sum(max(row) == row[_label_index(labels[index])] for index, row in ((index, rows[index]) for index in selected)) / len(selected)
        confidence = sum(max(rows[index]) for index in selected) / len(selected)
        error += len(selected) / total * abs(accuracy - confidence)
    return error


def metric_confidence_interval(successes: int, total: int, *, confidence: float = 0.95) -> tuple[float, float]:
    if total <= 0 or not 0 <= successes <= total or not 0 < confidence < 1:
        raise CalibrationBindingError("invalid binomial confidence interval inputs")
    z = 1.959963984540054 if confidence == 0.95 else 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


@dataclass(frozen=True)
class SelectiveThreshold:
    threshold: float
    target_error: float
    coverage: float
    selective_error: float
    model_digest: str
    dataset_manifest_digest: str
    ontology_digest: str
    label_order: tuple[str, ...] = LABELS
    created_at: str = field(default_factory=utc_timestamp)

    def __post_init__(self) -> None:
        object.__setattr__(self, "label_order", tuple(self.label_order))

    def assert_bound(
        self,
        *,
        model_digest: str,
        dataset_manifest_digest: str,
        ontology_digest: str,
        label_order: Sequence[str],
    ) -> None:
        if (model_digest, dataset_manifest_digest, ontology_digest, tuple(label_order)) != (
            self.model_digest, self.dataset_manifest_digest, self.ontology_digest, self.label_order
        ):
            raise CalibrationBindingError("selective threshold is bound to different model/data/ontology/labels")

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "target_error": self.target_error,
            "coverage": self.coverage,
            "selective_error": self.selective_error,
            "model_digest": self.model_digest,
            "dataset_manifest_digest": self.dataset_manifest_digest,
            "ontology_digest": self.ontology_digest,
            "label_order": list(self.label_order),
            "created_at": self.created_at,
        }


def selective_threshold(
    *,
    probabilities: Sequence[Mapping[str, float] | Sequence[float]],
    labels: Sequence[Any],
    target_error: float,
    model_digest: str,
    dataset_manifest_digest: str,
    ontology_digest: str,
    label_order: Sequence[str] = LABELS,
) -> SelectiveThreshold:
    if tuple(label_order) != LABELS or not 0 <= target_error <= 1:
        raise CalibrationBindingError("selective threshold label order or target is invalid")
    rows = _probability_rows(probabilities)
    if len(rows) != len(labels) or not model_digest or not dataset_manifest_digest or not ontology_digest:
        raise CalibrationBindingError("selective threshold binding is incomplete")
    best: tuple[float, float, float] | None = None
    for step in range(1001):
        threshold = step / 1000
        selected = [index for index, row in enumerate(rows) if max(row) >= threshold]
        if not selected:
            continue
        errors = sum(max(row) != row[_label_index(labels[index])] for index, row in ((index, rows[index]) for index in selected))
        coverage = len(selected) / len(rows)
        error = errors / len(selected)
        if error <= target_error and (best is None or coverage > best[1] or (coverage == best[1] and threshold < best[0])):
            best = (threshold, coverage, error)
    threshold, coverage, error = best or (1.0, 0.0, 0.0)
    return SelectiveThreshold(
        threshold=threshold,
        target_error=target_error,
        coverage=coverage,
        selective_error=error,
        model_digest=model_digest,
        dataset_manifest_digest=dataset_manifest_digest,
        ontology_digest=ontology_digest,
        label_order=tuple(label_order),
    )


@dataclass(frozen=True)
class CalibrationArtifact:
    calibration_id: str
    model_digest: str
    dataset_manifest_digest: str
    ontology_digest: str
    label_order: tuple[str, ...]
    temperature: float
    thresholds: Mapping[str, float]
    ece: float
    calibration_split_digest: str
    locked_test_used: bool = False
    verified: bool = True
    created_at: str = field(default_factory=utc_timestamp)

    @property
    def calibration_digest(self) -> str:
        return canonical_digest(
            {
                "calibration_id": self.calibration_id,
                "model_digest": self.model_digest,
                "dataset_manifest_digest": self.dataset_manifest_digest,
                "ontology_digest": self.ontology_digest,
                "label_order": list(self.label_order),
                "temperature": self.temperature,
                "thresholds": dict(sorted(self.thresholds.items())),
                "ece": self.ece,
                "calibration_split_digest": self.calibration_split_digest,
                "locked_test_used": self.locked_test_used,
            }
        )

    def as_verified(self) -> Any:
        """Return the classifier-facing immutable binding for this artifact."""

        from .citation_classifier import VerifiedCalibration

        binding = VerifiedCalibration(
            calibration_id=self.calibration_id,
            model_digest=self.model_digest,
            dataset_manifest_digest=self.dataset_manifest_digest,
            ontology_digest=self.ontology_digest,
            label_order=self.label_order,
            temperature=self.temperature,
            thresholds=self.thresholds,
            verified=self.verified and not self.locked_test_used,
            calibration_digest=self.calibration_digest,
            metadata=self.to_dict(),
        )
        binding.verify()
        return binding

    def to_dict(self) -> dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "model_digest": self.model_digest,
            "dataset_manifest_digest": self.dataset_manifest_digest,
            "ontology_digest": self.ontology_digest,
            "label_order": list(self.label_order),
            "temperature": self.temperature,
            "thresholds": dict(sorted(self.thresholds.items())),
            "ece": self.ece,
            "calibration_split_digest": self.calibration_split_digest,
            "locked_test_used": self.locked_test_used,
            "verified": self.verified,
            "calibration_digest": self.calibration_digest,
            "created_at": self.created_at,
        }


def _softmax(values: Sequence[float], temperature: float) -> list[float]:
    scaled = [float(value) / temperature for value in values]
    maximum = max(scaled)
    exp_values = [math.exp(value - maximum) for value in scaled]
    total = sum(exp_values)
    return [value / total for value in exp_values]


def fit_temperature(
    logits: Sequence[Sequence[float]],
    labels: Sequence[Any],
    *,
    label_order: Sequence[str] = LABELS,
    model_digest: str,
    dataset_manifest_digest: str,
    ontology_digest: str,
    locked_test: Sequence[Any] | None = None,
) -> CalibrationArtifact:
    if tuple(label_order) != LABELS or len(logits) != len(labels) or not logits:
        raise CalibrationBindingError("calibration split is malformed")
    if locked_test:
        raise CalibrationBindingError("locked-test labels are not permitted during calibration")
    numeric_labels = [_label_index(value) for value in labels]
    candidates = [0.05 + step * 0.05 for step in range(200)]
    best_temperature = 1.0
    best_loss = float("inf")
    for temperature in candidates:
        loss = 0.0
        for row, target in zip(logits, numeric_labels):
            if len(row) != len(LABELS) or not all(math.isfinite(float(value)) for value in row):
                raise CalibrationBindingError("calibration logits are not finite five-label rows")
            loss -= math.log(max(_softmax(row, temperature)[target], 1e-15))
        if loss < best_loss:
            best_loss = loss
            best_temperature = temperature
    probs = [_softmax(row, best_temperature) for row in logits]
    thresholds = {label: 0.95 if label == "directly_supports" else 0.0 for label in LABELS}
    calibration_id = "cal-" + canonical_digest({"model": model_digest, "data": dataset_manifest_digest, "ontology": ontology_digest, "temperature": best_temperature})[:24]
    return CalibrationArtifact(
        calibration_id=calibration_id,
        model_digest=model_digest,
        dataset_manifest_digest=dataset_manifest_digest,
        ontology_digest=ontology_digest,
        label_order=tuple(label_order),
        temperature=best_temperature,
        thresholds=thresholds,
        ece=expected_calibration_error(probs, numeric_labels),
        calibration_split_digest=canonical_digest({"logits": logits, "labels": numeric_labels}),
    )


fit_calibration = fit_temperature
