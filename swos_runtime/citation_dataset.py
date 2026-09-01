"""Governed citation-pair corpus validation and deterministic grouped splits."""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .citation_classifier import LABELS
from .models import canonical_digest


class DatasetValidationError(ValueError):
    pass


def validate_pair_record(row: Mapping[str, Any]) -> None:
    required = ("pair_id", "claim", "exact_quote", "source_uri", "source_digest", "licence", "group_id")
    missing = [key for key in required if not str(row.get(key) or "").strip()]
    if missing:
        raise DatasetValidationError("pair is missing " + ", ".join(missing))
    adjudication = row.get("adjudication")
    adjudicated_label = adjudication.get("label") if isinstance(adjudication, Mapping) else None
    if str(row.get("label") or adjudicated_label) not in LABELS:
        raise DatasetValidationError("pair label is not one of the five support labels")
    if str(row.get("licence")).lower() in {"unknown", "denied", "proprietary", "none"}:
        raise DatasetValidationError("pair source licence is not admissible")
    if len(str(row.get("source_digest"))) != 64:
        raise DatasetValidationError("pair source digest is not SHA-256")
    annotations = row.get("annotations")
    if not isinstance(annotations, Sequence) or isinstance(annotations, (str, bytes)) or len(annotations) < 2:
        raise DatasetValidationError("pair requires two independent annotations")
    annotators = {str(item.get("annotator_id")) for item in annotations if isinstance(item, Mapping)}
    if len(annotators) < 2:
        raise DatasetValidationError("pair annotations must have distinct annotators")
    if not isinstance(adjudication, Mapping) or adjudication.get("status") != "adjudicated":
        raise DatasetValidationError("pair lacks adjudication")


def grouped_split(
    rows: Sequence[Mapping[str, Any]],
    *,
    seed: int = 0,
    proportions: Mapping[str, float] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Split by canonical work/claim group, never by individual pair."""

    names = tuple((proportions or {"train": 0.7, "calibration": 0.15, "locked_test": 0.15}).keys())
    if not names:
        raise DatasetValidationError("split requires at least one named partition")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        validate_pair_record(row)
        groups[str(row["group_id"])].append(dict(row))
    ordered = sorted(groups, key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest())
    result = {name: [] for name in names}
    totals = {name: 0.0 for name in names}
    target = {name: float((proportions or {"train": 0.7, "calibration": 0.15, "locked_test": 0.15}).get(name, 0.0)) for name in names}
    for group in ordered:
        chosen = min(names, key=lambda name: (totals[name] / target[name] if target[name] else math.inf, names.index(name)))
        result[chosen].extend(groups[group])
        totals[chosen] += len(groups[group])
    for name in result:
        result[name].sort(key=lambda row: str(row["pair_id"]))
    return result


def check_group_leakage(splits: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[str]:
    seen: dict[str, str] = {}
    errors: list[str] = []
    for split, rows in splits.items():
        for row in rows:
            group = str(row.get("group_id") or "")
            if group in seen and seen[group] != split:
                errors.append(f"group {group} appears in {seen[group]} and {split}")
            seen[group] = str(split)
    return errors


def krippendorff_alpha_nominal(rows: Sequence[Mapping[str, Any]]) -> float:
    """Compute nominal alpha for two-or-more annotation records."""

    annotated = []
    for row in rows:
        values = [str(item.get("label")) for item in row.get("annotations", []) if isinstance(item, Mapping) and item.get("label") in LABELS]
        if len(values) >= 2:
            annotated.append(values)
    if not annotated:
        return 0.0
    observed = sum(sum(value != other for index, value in enumerate(values) for other in values[index + 1:]) for values in annotated)
    pairs = sum(len(values) * (len(values) - 1) / 2 for values in annotated)
    do = observed / pairs if pairs else 0.0
    all_values = [value for values in annotated for value in values]
    counts = Counter(all_values)
    total = len(all_values)
    de = 1 - sum((count / total) ** 2 for count in counts.values()) if total else 0.0
    if de == 0:
        return 1.0
    return max(-1.0, min(1.0, 1 - do / de))


def dataset_manifest(
    splits: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    source_manifest_digest: str,
    code_digest: str,
    status: str = "frozen",
) -> dict[str, Any]:
    leakage = check_group_leakage(splits)
    if leakage:
        raise DatasetValidationError("; ".join(leakage))
    for rows in splits.values():
        for row in rows:
            validate_pair_record(row)
    return {
        "schema_version": "2.0.0",
        "status": status,
        "source_manifest_digest": source_manifest_digest,
        "code_digest": code_digest,
        "split_policy": "canonical group hash with fixed seed; locked_test is write-protected",
        "splits": {
            name: {"count": len(rows), "digest": canonical_digest(list(rows)), "groups": sorted({str(row["group_id"]) for row in rows})}
            for name, rows in sorted(splits.items())
        },
        "agreement": {"alpha_nominal": krippendorff_alpha_nominal([row for rows in splits.values() for row in rows])},
        "locked_test_isolation": True,
    }
