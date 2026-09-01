"""Fail-closed citation-support classification and core admission boundary."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .models import canonical_digest, utc_timestamp

LABELS = (
    "directly_supports",
    "partially_supports",
    "context_only",
    "contradicts",
    "not_supported",
)
SUPPORTED_ONTOLOGY_VERSION = "2.0.0"


class CitationClassifierError(ValueError):
    """Raised for an invalid classifier invocation or artifact."""


@dataclass(frozen=True)
class CitationPair:
    pair_id: str
    claim: str
    passage: str = ""
    context: str = ""
    source_id: str = ""
    exact_quote: str | None = None
    span_start: int | None = None
    span_end: int | None = None
    discipline_iri: str = ""
    method_iri: str = ""
    source_role_iri: str = ""
    rights_disposition: str = "permitted"
    source_digest: str = ""

    def __post_init__(self) -> None:
        if not str(self.pair_id).strip() or not str(self.claim).strip():
            raise CitationClassifierError("citation pair requires pair_id and claim")
        if not self.passage and self.exact_quote:
            object.__setattr__(self, "passage", str(self.exact_quote))
        if self.exact_quote is None:
            object.__setattr__(self, "exact_quote", self.passage)

    @property
    def canonical_input_digest(self) -> str:
        return canonical_digest(
            {
                "claim": self.claim,
                "passage": self.passage,
                "context": self.context,
                "source_id": self.source_id,
                "exact_quote": self.exact_quote,
                "span_start": self.span_start,
                "span_end": self.span_end,
                "discipline_iri": self.discipline_iri,
                "method_iri": self.method_iri,
                "source_role_iri": self.source_role_iri,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "claim": self.claim,
            "passage": self.passage,
            "context": self.context,
            "source_id": self.source_id,
            "exact_quote": self.exact_quote,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "discipline_iri": self.discipline_iri,
            "method_iri": self.method_iri,
            "source_role_iri": self.source_role_iri,
            "rights_disposition": self.rights_disposition,
            "source_digest": self.source_digest,
            "canonical_input_digest": self.canonical_input_digest,
        }


@dataclass(frozen=True)
class VerifiedModelArtifact:
    model_id: str = ""
    model_digest: str = ""
    label_order: tuple[str, ...] = LABELS
    version: str = "1.0.0"
    artifact_path: str | None = None
    config_digest: str = ""
    dataset_manifest_digest: str = ""
    verified: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "label_order", tuple(self.label_order))

    @classmethod
    def from_manifest(cls, path: str | Path) -> "VerifiedModelArtifact":
        import json

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        artifact = cls(
            model_id=str(data.get("model_id") or data.get("artifact_id") or ""),
            model_digest=str(data.get("model_digest") or data.get("sha256") or ""),
            label_order=tuple(data.get("label_order") or LABELS),
            version=str(data.get("version") or "1.0.0"),
            artifact_path=str(data.get("artifact_path")) if data.get("artifact_path") else None,
            config_digest=str(data.get("config_digest") or ""),
            dataset_manifest_digest=str(data.get("dataset_manifest_digest") or ""),
            verified=bool(data.get("verified", False)),
            metadata=dict(data),
        )
        artifact.verify()
        return artifact

    def verify(self) -> None:
        if not self.model_id or not self.model_digest or len(self.model_digest) != 64:
            raise CitationClassifierError("model artifact identity is incomplete")
        if tuple(self.label_order) != LABELS:
            raise CitationClassifierError(
                "model label order does not match the frozen five-label contract"
            )
        if self.artifact_path:
            path = Path(self.artifact_path)
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != self.model_digest
            ):
                raise CitationClassifierError("model artifact digest verification failed")
        if not self.verified:
            raise CitationClassifierError("model artifact has not been verified")

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_digest": self.model_digest,
            "label_order": list(self.label_order),
            "version": self.version,
            "artifact_path": self.artifact_path,
            "config_digest": self.config_digest,
            "dataset_manifest_digest": self.dataset_manifest_digest,
            "verified": self.verified,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class VerifiedCalibration:
    calibration_id: str = ""
    model_digest: str = ""
    dataset_manifest_digest: str = ""
    ontology_digest: str = ""
    label_order: tuple[str, ...] = LABELS
    temperature: float = 1.0
    thresholds: Mapping[str, float] = field(default_factory=dict)
    verified: bool = False
    calibration_digest: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "label_order", tuple(self.label_order))
        object.__setattr__(self, "thresholds", dict(self.thresholds))

    @classmethod
    def from_manifest(cls, path: str | Path) -> "VerifiedCalibration":
        import json

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        artifact = cls(
            calibration_id=str(data.get("calibration_id") or ""),
            model_digest=str(data.get("model_digest") or ""),
            dataset_manifest_digest=str(data.get("dataset_manifest_digest") or ""),
            ontology_digest=str(data.get("ontology_digest") or ""),
            label_order=tuple(data.get("label_order") or LABELS),
            temperature=float(data.get("temperature") or 1.0),
            thresholds=dict(data.get("thresholds") or {}),
            verified=bool(data.get("verified", False)),
            calibration_digest=str(data.get("calibration_digest") or ""),
            metadata=dict(data),
        )
        artifact.verify()
        return artifact

    def verify(
        self,
        *,
        model: VerifiedModelArtifact | None = None,
        ontology_version: str = SUPPORTED_ONTOLOGY_VERSION,
    ) -> None:
        if (
            not self.calibration_id
            or len(self.model_digest) != 64
            or len(self.dataset_manifest_digest) != 64
        ):
            raise CitationClassifierError("calibration artifact identity is incomplete")
        if len(self.ontology_digest) != 64 or tuple(self.label_order) != LABELS:
            raise CitationClassifierError("calibration ontology or label binding is invalid")
        if ontology_version != SUPPORTED_ONTOLOGY_VERSION:
            raise CitationClassifierError(
                "calibration is not valid for the selected ontology version"
            )
        if not math.isfinite(float(self.temperature)) or float(self.temperature) <= 0:
            raise CitationClassifierError("calibration temperature must be finite and positive")
        if any(
            not math.isfinite(float(value)) or not 0 <= float(value) <= 1
            for value in self.thresholds.values()
        ):
            raise CitationClassifierError("calibration threshold is outside [0, 1]")
        if model is not None and self.model_digest != model.model_digest:
            raise CitationClassifierError("calibration/model digest mismatch")
        if not self.verified:
            raise CitationClassifierError("calibration artifact has not been verified")

    def to_dict(self) -> dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "model_digest": self.model_digest,
            "dataset_manifest_digest": self.dataset_manifest_digest,
            "ontology_digest": self.ontology_digest,
            "label_order": list(self.label_order),
            "temperature": self.temperature,
            "thresholds": dict(sorted(self.thresholds.items())),
            "verified": self.verified,
            "calibration_digest": self.calibration_digest,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class DeterministicCitationChecks:
    source_exists: bool = False
    metadata_verified: bool = False
    rights_allowed: bool = False
    quote_contained: bool = False
    provenance_valid: bool = False
    retraction_clear: bool = True
    span_valid: bool = True
    rule_rejection: str | None = None
    errors: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return (
            all(
                (
                    self.source_exists,
                    self.metadata_verified,
                    self.rights_allowed,
                    self.quote_contained,
                    self.provenance_valid,
                    self.retraction_clear,
                    self.span_valid,
                )
            )
            and not self.rule_rejection
            and not self.errors
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_exists": self.source_exists,
            "metadata_verified": self.metadata_verified,
            "rights_allowed": self.rights_allowed,
            "quote_contained": self.quote_contained,
            "provenance_valid": self.provenance_valid,
            "retraction_clear": self.retraction_clear,
            "span_valid": self.span_valid,
            "rule_rejection": self.rule_rejection,
            "errors": list(self.errors),
            "passed": self.passed,
        }


@dataclass(frozen=True)
class CitationSupportDecision:
    pair_id: str
    status: str
    support_level: str | None
    probabilities: Mapping[str, float]
    confidence: float
    input: Mapping[str, Any] = field(default_factory=dict)
    selected_threshold: float = 0.0
    abstention_reason: str | None = None
    uncertainty: tuple[str, ...] = ()
    model_digest: str = ""
    calibration_digest: str = ""
    dataset_manifest_digest: str = ""
    ontology_version: str = SUPPORTED_ONTOLOGY_VERSION
    ontology_digest: str = ""
    label_order: tuple[str, ...] = LABELS
    input_digest: str = ""
    deterministic_checks: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_timestamp)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "probabilities",
            {label: float(self.probabilities.get(label, 0.0)) for label in LABELS},
        )
        object.__setattr__(self, "label_order", tuple(self.label_order))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "2.0.0",
            "pair_id": self.pair_id,
            "input": dict(self.input),
            "status": self.status,
            "support_level": self.support_level,
            "probabilities": dict(self.probabilities),
            "confidence": self.confidence,
            "selected_threshold": self.selected_threshold,
            "abstention_reason": self.abstention_reason,
            "uncertainty": list(self.uncertainty),
            "model_digest": self.model_digest,
            "calibration_digest": self.calibration_digest,
            "dataset_manifest_digest": self.dataset_manifest_digest,
            "ontology_version": self.ontology_version,
            "ontology_digest": self.ontology_digest,
            "label_order": list(self.label_order),
            "input_digest": self.input_digest,
            "deterministic_checks": dict(self.deterministic_checks),
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    state: str
    support_level: str | None
    reason: str
    pair_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "state": self.state,
            "support_level": self.support_level,
            "reason": self.reason,
            "pair_id": self.pair_id,
        }


def _uniform() -> dict[str, float]:
    return {label: 1.0 / len(LABELS) for label in LABELS}


def _softmax(values: Sequence[float], temperature: float) -> dict[str, float]:
    if len(values) != len(LABELS) or not all(math.isfinite(float(value)) for value in values):
        raise CitationClassifierError("logits must contain five finite values")
    scaled = [float(value) / temperature for value in values]
    maximum = max(scaled)
    exponentials = [math.exp(value - maximum) for value in scaled]
    total = sum(exponentials)
    return {label: exponentials[index] / total for index, label in enumerate(LABELS)}


class CitationSupportClassifier:
    """Deterministic inference facade around a verified injected model."""

    def __init__(
        self,
        *,
        model: VerifiedModelArtifact,
        calibration: VerifiedCalibration,
        ontology_version: str = SUPPORTED_ONTOLOGY_VERSION,
        ontology_digest: str = "o" * 64,
        backend: Callable[..., Any] | None = None,
    ) -> None:
        self.model = model
        self.calibration = calibration
        self.ontology_version = ontology_version
        self.ontology_digest = ontology_digest
        self.backend = backend

    def _failed(
        self, pair: CitationPair, reason: str, *, status: str = "abstained"
    ) -> CitationSupportDecision:
        return CitationSupportDecision(
            pair_id=pair.pair_id,
            status=status,
            support_level=None,
            probabilities=_uniform(),
            confidence=0.0,
            input=self._input_record(pair),
            abstention_reason=reason,
            uncertainty=(reason,),
            model_digest=self.model.model_digest,
            calibration_digest=self.calibration.calibration_digest,
            dataset_manifest_digest=self.calibration.dataset_manifest_digest,
            ontology_version=self.ontology_version,
            ontology_digest=self.ontology_digest,
            input_digest=pair.canonical_input_digest,
            provenance={
                "execution_mode": "offline-injected",
                "authority": "advisory-classifier-evidence",
            },
        )

    @staticmethod
    def _input_record(pair: CitationPair) -> dict[str, Any]:
        return {
            "claim": pair.claim,
            "exact_quote": pair.exact_quote or "",
            "context": pair.context,
            "source_id": pair.source_id,
            "input_digest": pair.canonical_input_digest,
        }

    def _backend_logits(self, pairs: Sequence[CitationPair]) -> list[Any] | None:
        backend = self.backend
        if backend is None:
            for name in ("predict_logits", "logits", "predict"):
                candidate = getattr(self.model, name, None)
                if callable(candidate):
                    backend = candidate
                    break
        if backend is None:
            return None
        payload = [pair.to_dict() for pair in pairs]
        try:
            result = backend(payload)
        except TypeError:
            result = [backend(item) for item in payload]
        return list(result)

    def classify(
        self,
        inputs: Sequence[CitationPair],
        *,
        logits: Sequence[Sequence[float]] | None = None,
        probabilities: Sequence[Mapping[str, float] | Sequence[float]] | None = None,
        ood: Sequence[bool] | None = None,
        batch_size: int | None = None,
    ) -> list[CitationSupportDecision]:
        pairs = list(inputs)
        if not pairs:
            return []
        try:
            self.model.verify()
            self.calibration.verify(model=self.model, ontology_version=self.ontology_version)
            if len(self.ontology_digest) != 64:
                raise CitationClassifierError("ontology digest is incomplete")
        except CitationClassifierError as exc:
            return [self._failed(pair, str(exc)) for pair in pairs]
        raw_logits: list[Any] | None = list(logits) if logits is not None else None
        raw_probabilities: list[Any] | None = (
            list(probabilities) if probabilities is not None else None
        )
        if raw_logits is None and raw_probabilities is None:
            raw_logits = self._backend_logits(pairs)
        if raw_logits is not None and len(raw_logits) != len(pairs):
            return [
                self._failed(pair, "model_output_length_mismatch", status="error") for pair in pairs
            ]
        if raw_probabilities is not None and len(raw_probabilities) != len(pairs):
            return [
                self._failed(pair, "model_output_length_mismatch", status="error") for pair in pairs
            ]
        output: list[CitationSupportDecision] = []
        for index, pair in enumerate(pairs):
            if ood is not None and index < len(ood) and ood[index]:
                output.append(self._failed(pair, "out_of_distribution"))
                continue
            try:
                if raw_probabilities is not None:
                    row = raw_probabilities[index]
                    if isinstance(row, Mapping):
                        values = [float(row[label]) for label in LABELS]
                    else:
                        values = [float(value) for value in row]
                    if len(values) != len(LABELS) or not all(
                        math.isfinite(value) and value >= 0 for value in values
                    ):
                        raise CitationClassifierError(
                            "probabilities must be finite nonnegative five-label values"
                        )
                    total = sum(values)
                    if total <= 0:
                        raise CitationClassifierError("probabilities must have a positive sum")
                    probs = {label: value / total for label, value in zip(LABELS, values)}
                else:
                    row = raw_logits[index] if raw_logits is not None else None
                    if isinstance(row, Mapping):
                        row = [row[label] for label in LABELS]
                    probs = _softmax(list(row), float(self.calibration.temperature))
                selected = max(LABELS, key=lambda label: probs[label])
                confidence = float(probs[selected])
                threshold = float(
                    self.calibration.thresholds.get(
                        selected, 0.0 if selected != "directly_supports" else 0.95
                    )
                )
                if confidence < threshold:
                    output.append(
                        CitationSupportDecision(
                            pair_id=pair.pair_id,
                            status="abstained",
                            support_level=None,
                            probabilities=probs,
                            confidence=confidence,
                            selected_threshold=threshold,
                            input=self._input_record(pair),
                            abstention_reason="below_selective_threshold",
                            uncertainty=("low_confidence",),
                            model_digest=self.model.model_digest,
                            calibration_digest=self.calibration.calibration_digest,
                            dataset_manifest_digest=self.calibration.dataset_manifest_digest,
                            ontology_version=self.ontology_version,
                            ontology_digest=self.ontology_digest,
                            input_digest=pair.canonical_input_digest,
                            provenance={
                                "execution_mode": "offline-injected",
                                "authority": "advisory-classifier-evidence",
                            },
                        )
                    )
                else:
                    output.append(
                        CitationSupportDecision(
                            pair_id=pair.pair_id,
                            status="classified",
                            support_level=selected,
                            probabilities=probs,
                            confidence=confidence,
                            selected_threshold=threshold,
                            input=self._input_record(pair),
                            model_digest=self.model.model_digest,
                            calibration_digest=self.calibration.calibration_digest,
                            dataset_manifest_digest=self.calibration.dataset_manifest_digest,
                            ontology_version=self.ontology_version,
                            ontology_digest=self.ontology_digest,
                            input_digest=pair.canonical_input_digest,
                            provenance={
                                "execution_mode": "offline-injected",
                                "authority": "advisory-classifier-evidence",
                            },
                        )
                    )
            except (TypeError, ValueError, KeyError, CitationClassifierError) as exc:
                output.append(self._failed(pair, f"invalid_model_output:{exc}"))
        return output


def deterministic_precheck(
    pair: CitationPair, source: Any | None = None, *, rule_rejection: str | None = None
) -> DeterministicCitationChecks:
    """Perform deterministic source/quote/rights checks before model inference."""

    source_data = (
        source.to_dict(include_text=True) if hasattr(source, "to_dict") else dict(source or {})
    )
    text = str(source_data.get("text") or source_data.get("passage") or "")
    quote = str(pair.exact_quote or pair.passage or "")
    source_exists = bool(source_data) and (
        not pair.source_id or str(source_data.get("source_id")) == pair.source_id
    )
    metadata_verified = bool(
        source_data.get(
            "metadata_verified", source_data.get("metadata_status") not in (None, "unknown")
        )
    )
    rights_allowed = bool(
        source_data.get("redistribution_allowed", True)
    ) and pair.rights_disposition not in {"denied", "restricted"}
    quote_contained = bool(quote and quote in text)
    retraction_clear = str(source_data.get("retraction_status") or "not_checked") not in {
        "retracted",
        "withdrawn",
    }
    span_valid = (
        pair.span_start is None
        or pair.span_end is None
        or 0 <= pair.span_start <= pair.span_end <= len(text)
    )
    errors = []
    if not source_exists:
        errors.append("source_missing")
    if not metadata_verified:
        errors.append("metadata_unverified")
    if not rights_allowed:
        errors.append("rights_denied")
    if not quote_contained:
        errors.append("quote_not_contained")
    if not retraction_clear:
        errors.append("source_retracted")
    return DeterministicCitationChecks(
        source_exists=source_exists,
        metadata_verified=metadata_verified,
        rights_allowed=rights_allowed,
        quote_contained=quote_contained,
        provenance_valid=bool(
            pair.source_digest or source_data.get("source_id") or source_data.get("url")
        ),
        retraction_clear=retraction_clear,
        span_valid=span_valid,
        rule_rejection=rule_rejection,
        errors=tuple(errors),
    )


def admission_eligibility(
    pair: CitationPair,
    deterministic_checks: DeterministicCitationChecks | Mapping[str, Any],
    decision: CitationSupportDecision,
) -> Eligibility:
    checks = (
        deterministic_checks
        if isinstance(deterministic_checks, DeterministicCitationChecks)
        else DeterministicCitationChecks(
            **{
                key: value
                for key, value in deterministic_checks.items()
                if key in DeterministicCitationChecks.__dataclass_fields__
            }
        )
    )
    if checks.rule_rejection or checks.errors or not checks.passed:
        reason = checks.rule_rejection or (
            checks.errors[0] if checks.errors else "deterministic_precheck_failed"
        )
        return Eligibility(False, "rule_rejected", None, reason, pair.pair_id)
    if decision.status != "classified" or decision.support_level is None:
        return Eligibility(
            False,
            "unresolved",
            None,
            decision.abstention_reason or "classifier_not_admission_eligible",
            pair.pair_id,
        )
    if decision.support_level != "directly_supports":
        return Eligibility(False, "unresolved", None, "support_label_is_not_direct", pair.pair_id)
    if decision.confidence < decision.selected_threshold:
        return Eligibility(False, "unresolved", None, "confidence_below_threshold", pair.pair_id)
    return Eligibility(
        True, "eligible", "directly_supports", "all_core_checks_passed", pair.pair_id
    )


run_deterministic_checks = deterministic_precheck
ProductionCitationClassifier = CitationSupportClassifier
