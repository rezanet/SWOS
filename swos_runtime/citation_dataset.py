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


_DATASET_USES = frozenset({"train", "calibration", "locked_test", "ood", "temporal"})


def validate_source_licence_manifest(
    manifest: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Validate and index the immutable source/right records for a corpus."""

    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != "2.0.0":
        raise DatasetValidationError("source licence manifest has an unsupported schema")
    status = str(manifest.get("status") or "")
    sources = manifest.get("sources")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        raise DatasetValidationError("source licence manifest sources must be a list")
    if status == "not_run":
        if sources:
            raise DatasetValidationError("not_run source licence manifest cannot contain sources")
        return {}
    if status not in {"ready", "frozen"} or not sources:
        raise DatasetValidationError("source licence manifest is not ready for corpus admission")
    approval = manifest.get("approval")
    if (
        not isinstance(approval, Mapping)
        or approval.get("status") != "approved"
        or not str(approval.get("reviewer_id") or "").strip()
    ):
        raise DatasetValidationError("source licence manifest lacks independent dataset approval")

    indexed: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, Mapping):
            raise DatasetValidationError("source licence record must be an object")
        source_id = str(source.get("source_id") or "").strip()
        uri = str(source.get("uri") or "").strip()
        digest = str(source.get("digest") or "").strip().lower()
        licence = str(source.get("licence") or "").strip()
        attribution = str(source.get("attribution") or "").strip()
        if not source_id or not uri or not licence or not attribution:
            raise DatasetValidationError("source licence record lacks identity or attribution")
        if source_id in indexed:
            raise DatasetValidationError(f"duplicate source licence ID: {source_id}")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise DatasetValidationError(f"source {source_id} digest is not SHA-256")
        if licence.lower() in {"unknown", "denied", "proprietary", "none", "unlicensed"}:
            raise DatasetValidationError(f"source {source_id} licence is not admissible")
        allowed_use = source.get("allowed_use")
        if (
            not isinstance(allowed_use, Sequence)
            or isinstance(allowed_use, (str, bytes))
            or not allowed_use
            or not all(str(use) in _DATASET_USES for use in allowed_use)
        ):
            raise DatasetValidationError(f"source {source_id} has invalid permitted uses")
        approval = source.get("approval")
        if (
            not isinstance(approval, Mapping)
            or approval.get("status") != "approved"
            or not str(approval.get("reviewer_id") or "").strip()
        ):
            raise DatasetValidationError(f"source {source_id} lacks independent approval")
        indexed[source_id] = dict(source)
        indexed[source_id]["digest"] = digest
    return indexed


def validate_pair_source_binding(
    row: Mapping[str, Any], sources: Mapping[str, Mapping[str, Any]]
) -> None:
    """Require each pair's URI, digest, and licence to match one source record."""

    source_id = str(row.get("source_id") or "").strip()
    source = sources.get(source_id) if source_id else None
    if source is None:
        matches = [
            candidate
            for candidate in sources.values()
            if (
                str(candidate.get("uri") or "").strip() == str(row.get("source_uri") or "").strip()
                and str(candidate.get("digest") or "").lower()
                == str(row.get("source_digest") or "").lower()
                and str(candidate.get("licence") or "").strip()
                == str(row.get("licence") or "").strip()
            )
        ]
        if len(matches) != 1:
            raise DatasetValidationError(
                f"pair {row.get('pair_id', '<unknown>')} has no unique source licence binding"
            )
        source = matches[0]
    if (
        str(source.get("uri") or "").strip() != str(row.get("source_uri") or "").strip()
        or str(source.get("digest") or "").lower() != str(row.get("source_digest") or "").lower()
        or str(source.get("licence") or "").strip() != str(row.get("licence") or "").strip()
    ):
        raise DatasetValidationError(
            f"pair {row.get('pair_id', '<unknown>')} source binding mismatches"
        )
    requested_use = row.get("allowed_use")
    if requested_use is not None:
        if isinstance(requested_use, str) or not isinstance(requested_use, Sequence):
            raise DatasetValidationError("pair permitted uses must be a list")
        if not set(map(str, requested_use)).issubset(set(map(str, source["allowed_use"]))):
            raise DatasetValidationError(
                f"pair {row.get('pair_id', '<unknown>')} exceeds source permitted uses"
            )


def validate_pair_record(row: Mapping[str, Any]) -> None:
    required = (
        "pair_id",
        "claim",
        "exact_quote",
        "source_uri",
        "source_digest",
        "licence",
        "group_id",
    )
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
    if (
        not isinstance(annotations, Sequence)
        or isinstance(annotations, (str, bytes))
        or len(annotations) < 2
    ):
        raise DatasetValidationError("pair requires two independent annotations")
    annotators = {
        str(item.get("annotator_id")) for item in annotations if isinstance(item, Mapping)
    }
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
    ordered = sorted(
        groups, key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()
    )
    result = {name: [] for name in names}
    totals = {name: 0.0 for name in names}
    target = {
        name: float(
            (proportions or {"train": 0.7, "calibration": 0.15, "locked_test": 0.15}).get(name, 0.0)
        )
        for name in names
    }
    for group in ordered:
        chosen = min(
            names,
            key=lambda name: (
                totals[name] / target[name] if target[name] else math.inf,
                names.index(name),
            ),
        )
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
        values = [
            str(item.get("label"))
            for item in row.get("annotations", [])
            if isinstance(item, Mapping) and item.get("label") in LABELS
        ]
        if len(values) >= 2:
            annotated.append(values)
    if not annotated:
        return 0.0
    observed = sum(
        sum(value != other for index, value in enumerate(values) for other in values[index + 1 :])
        for values in annotated
    )
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
            name: {
                "count": len(rows),
                "digest": canonical_digest(list(rows)),
                "groups": sorted({str(row["group_id"]) for row in rows}),
            }
            for name, rows in sorted(splits.items())
        },
        "agreement": {
            "alpha_nominal": krippendorff_alpha_nominal(
                [row for rows in splits.values() for row in rows]
            )
        },
        "locked_test_isolation": True,
    }
