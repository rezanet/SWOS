"""Build a licensed, adjudicated, leakage-checked citation corpus offline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_classifier import LABELS  # noqa: E402
from swos_runtime.citation_dataset import (  # noqa: E402
    DatasetValidationError,
    dataset_manifest,
    grouped_split,
    validate_pair_source_binding,
    validate_source_licence_manifest,
)
from swos_runtime.models import canonical_digest  # noqa: E402

RELEASE_FLOORS: dict[str, int] = {
    "total_pairs": 6000,
    "per_label": 600,
    "per_discipline": 300,
    "locked_test": 1500,
    "locked_per_label": 150,
    "locked_per_discipline": 75,
    "locked_adversarial_non_direct": 300,
}

SUPPORTED_DISCIPLINES = (
    "art_history",
    "art_criticism",
    "engineering",
    "humanities",
    "interdisciplinary",
    "materials_science",
    "philosophy",
    "psychology",
    "technical_writing",
)

SPLIT_NAMES = ("train", "calibration", "locked_test", "temporal", "ood")


class DatasetBuildBlocked(RuntimeError):
    pass


def _resolve_reference(manifest_path: Path, reference: Any, label: str) -> Path:
    if not isinstance(reference, str) or not reference.strip():
        raise DatasetBuildBlocked(f"{label} reference must be a non-empty relative path")
    root = manifest_path.parent.resolve()
    path = (root / reference).resolve()
    if not path.is_relative_to(root):
        raise DatasetBuildBlocked(f"{label} escapes its manifest directory: {reference}")
    if not path.is_file():
        raise DatasetBuildBlocked(f"{label} is missing: {path}")
    return path


def _normalise_rows(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DatasetBuildBlocked(f"{label} must be a JSON array")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise DatasetBuildBlocked(f"{label} entry {index} must be a JSON object")
        rows.append(dict(row))
    return rows


def _row_label(row: Mapping[str, Any]) -> str:
    adjudication = row.get("adjudication")
    adjudicated_label = adjudication.get("label") if isinstance(adjudication, Mapping) else None
    return str(row.get("label") or adjudicated_label or "")


def release_floor_gaps(
    rows: Sequence[Mapping[str, Any]],
    splits: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    supported_disciplines: Sequence[str],
    floors: Mapping[str, int] | None = None,
) -> list[dict[str, int | str]]:
    """Return every unmet frozen citation-corpus release floor."""

    required = dict(floors or RELEASE_FLOORS)
    missing = sorted(set(RELEASE_FLOORS) - set(required))
    if missing:
        raise DatasetValidationError("release floor is missing " + ", ".join(missing))
    if any(not isinstance(value, int) or value < 0 for value in required.values()):
        raise DatasetValidationError("release floor values must be non-negative integers")

    all_rows = list(rows)
    locked_rows = list(splits.get("locked_test", ()))
    labels = Counter(_row_label(row) for row in all_rows)
    locked_labels = Counter(_row_label(row) for row in locked_rows)
    disciplines = Counter(str(row.get("discipline") or "") for row in all_rows)
    locked_disciplines = Counter(str(row.get("discipline") or "") for row in locked_rows)
    gaps: list[dict[str, int | str]] = []

    def require(metric: str, observed: int, floor_key: str) -> None:
        minimum = required[floor_key]
        if observed < minimum:
            gaps.append({"metric": metric, "required": minimum, "observed": observed})

    require("total_pairs", len(all_rows), "total_pairs")
    for label in LABELS:
        require(f"label:{label}", labels[label], "per_label")
    for discipline in supported_disciplines:
        require(
            f"discipline:{discipline}",
            disciplines[str(discipline)],
            "per_discipline",
        )
    require("locked_test", len(locked_rows), "locked_test")
    for label in LABELS:
        require(f"locked_label:{label}", locked_labels[label], "locked_per_label")
    for discipline in supported_disciplines:
        require(
            f"locked_discipline:{discipline}",
            locked_disciplines[str(discipline)],
            "locked_per_discipline",
        )
    adversarial_non_direct = sum(
        row.get("adversarial") is True and _row_label(row) != "directly_supports"
        for row in locked_rows
    )
    require(
        "locked_adversarial_non_direct",
        adversarial_non_direct,
        "locked_adversarial_non_direct",
    )
    return gaps


def _read_rows(manifest: Mapping[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    if "pairs" in manifest and "pairs_path" in manifest:
        raise DatasetBuildBlocked("citation manifest must not define both pairs and pairs_path")
    if "pairs" in manifest:
        return _normalise_rows(manifest["pairs"], "citation pairs")
    if "pairs_path" in manifest:
        path = _resolve_reference(manifest_path, manifest["pairs_path"], "citation pair source")
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise DatasetBuildBlocked(f"citation pair source is unreadable: {path}") from exc
        if path.suffix.lower() == ".jsonl":
            rows: list[Any] = []
            for line_number, line in enumerate(raw.splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise DatasetBuildBlocked(
                        f"citation pair source line {line_number} is invalid JSON"
                    ) from exc
            return _normalise_rows(rows, "citation pair source")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DatasetBuildBlocked(f"citation pair source is invalid JSON: {path}") from exc
        if isinstance(payload, list):
            return _normalise_rows(payload, "citation pair source")
        if isinstance(payload, Mapping) and "pairs" in payload:
            return _normalise_rows(payload["pairs"], "citation pair source pairs")
        raise DatasetBuildBlocked("citation pair source must be a JSON array or pairs object")
    raise DatasetBuildBlocked("no licensed pair source was provided; acquisition is NOT_RUN")


def _read_split_proportions(manifest: Mapping[str, Any]) -> dict[str, float]:
    raw = manifest.get("split_proportions")
    if not isinstance(raw, Mapping) or set(raw) != set(SPLIT_NAMES):
        raise DatasetBuildBlocked(
            "citation manifest must declare train, calibration, locked_test, temporal, and ood split proportions"
        )
    if any(
        isinstance(raw[name], bool) or not isinstance(raw[name], (int, float))
        for name in SPLIT_NAMES
    ):
        raise DatasetBuildBlocked("citation manifest split proportions must be numeric")
    try:
        proportions = {name: float(raw[name]) for name in SPLIT_NAMES}
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        raise DatasetBuildBlocked("citation manifest split proportions must be numeric") from exc
    if any(not math.isfinite(value) or value <= 0 for value in proportions.values()):
        raise DatasetBuildBlocked("citation manifest split proportions must be finite and positive")
    if not math.isclose(sum(proportions.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise DatasetBuildBlocked("citation manifest split proportions must sum to one")
    return proportions


def _read_source_licence_manifest(
    manifest: dict[str, Any], manifest_path: Path
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    reference = manifest.get("source_licence_manifest")
    if reference is None:
        raise DatasetBuildBlocked("source licence manifest is required; acquisition is NOT_RUN")
    path = _resolve_reference(manifest_path, reference, "source licence manifest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DatasetBuildBlocked(f"source licence manifest is unreadable: {path}") from exc
    try:
        return payload, validate_source_licence_manifest(payload)
    except DatasetValidationError as exc:
        raise DatasetBuildBlocked(f"source licence manifest is invalid: {exc}") from exc


def build_dataset(
    manifest_path: Path | str, output_dir: Path | str, *, seed: int = 0
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise DatasetBuildBlocked(f"immutable dataset output already exists: {output_dir}")
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(source_manifest, Mapping):
        raise DatasetBuildBlocked("citation manifest must be an object")
    declared_floors = source_manifest.get("required_floors")
    if declared_floors != RELEASE_FLOORS:
        raise DatasetBuildBlocked(
            "citation manifest release floors do not match the frozen contract"
        )
    declared_disciplines = source_manifest.get("supported_disciplines")
    if (
        not isinstance(declared_disciplines, Sequence)
        or isinstance(declared_disciplines, (str, bytes))
        or len(declared_disciplines) != len(SUPPORTED_DISCIPLINES)
        or any(not isinstance(item, str) or not item.strip() for item in declared_disciplines)
        or len(set(declared_disciplines)) != len(declared_disciplines)
        or set(map(str, declared_disciplines)) != set(SUPPORTED_DISCIPLINES)
    ):
        raise DatasetBuildBlocked(
            "citation manifest disciplines do not match the frozen v2 profiles"
        )
    source_licence_manifest, source_licences = _read_source_licence_manifest(
        source_manifest, manifest_path
    )
    rows = _read_rows(source_manifest, manifest_path)
    for row in rows:
        validate_pair_source_binding(row, source_licences)
    split_proportions = _read_split_proportions(source_manifest)
    splits = grouped_split(rows, seed=seed, proportions=split_proportions)
    report = dataset_manifest(
        splits,
        source_manifest_digest=canonical_digest(source_manifest),
        code_digest=canonical_digest({"tool": "build_citation_dataset", "version": "2.0.0"}),
    )
    counts = {
        str(label): sum(_row_label(row) == label for row in rows)
        for label in (
            "directly_supports",
            "partially_supports",
            "context_only",
            "contradicts",
            "not_supported",
        )
    }
    disciplines = {
        str(discipline): sum(row.get("discipline") == discipline for row in rows)
        for discipline in sorted({str(row.get("discipline")) for row in rows})
    }
    report["release_floor"] = {
        "total": RELEASE_FLOORS["total_pairs"],
        "per_label": RELEASE_FLOORS["per_label"],
        "per_discipline": RELEASE_FLOORS["per_discipline"],
        "locked_test": RELEASE_FLOORS["locked_test"],
        "locked_per_label": RELEASE_FLOORS["locked_per_label"],
        "locked_per_discipline": RELEASE_FLOORS["locked_per_discipline"],
        "locked_adversarial_non_direct": RELEASE_FLOORS["locked_adversarial_non_direct"],
    }
    report["source_licence_manifest_digest"] = canonical_digest(source_licence_manifest)
    report["split_proportions"] = split_proportions
    report["counts"] = {"total": len(rows), "per_label": counts, "per_discipline": disciplines}
    report["release_floor_gaps"] = release_floor_gaps(
        rows,
        splits,
        supported_disciplines=SUPPORTED_DISCIPLINES,
    )
    report["status"] = (
        "frozen" if not report["release_floor_gaps"] else "blocked_below_release_floor"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, values in splits.items():
        (output_dir / f"{name}.jsonl").write_text(
            "".join(json.dumps(value, sort_keys=True) + "\n" for value in values), encoding="utf-8"
        )
    (output_dir / "manifest.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    licence_lines = [
        "# Data licence",
        "",
        "This corpus is admitted only from the explicitly approved source records below.",
        f"Source licence manifest canonical SHA-256: `{canonical_digest(source_licence_manifest)}`",
        "",
        "## Admitted sources",
        "",
    ]
    for source_id in sorted(source_licences):
        source = source_licences[source_id]
        allowed_use = ", ".join(str(item) for item in source["allowed_use"])
        approval = source.get("approval")
        approval_text = (
            f"{approval.get('status')} by {approval.get('reviewer_id')}"
            if isinstance(approval, Mapping)
            else "not recorded"
        )
        licence_lines.extend(
            [
                f"### `{source_id}`",
                f"- URI: `{source['uri']}`",
                f"- Content SHA-256: `{source['digest']}`",
                f"- Licence: {source['licence']}",
                f"- Attribution: {source['attribution']}",
                f"- Allowed uses: {allowed_use}",
                f"- Source approval: {approval_text}",
                "",
            ]
        )
    (output_dir / "DATA-LICENCE.md").write_text(
        "\n".join(licence_lines),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    try:
        report = build_dataset(args.manifest, args.out_dir, seed=args.seed)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        DatasetValidationError,
        DatasetBuildBlocked,
        TypeError,
        ValueError,
        OverflowError,
    ) as exc:
        print(json.dumps({"status": "not_run", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "frozen" else 2


if __name__ == "__main__":
    raise SystemExit(main())
