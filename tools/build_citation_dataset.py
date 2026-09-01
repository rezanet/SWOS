"""Build a licensed, adjudicated, leakage-checked citation corpus offline."""

from __future__ import annotations

import argparse
import json
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


class DatasetBuildBlocked(RuntimeError):
    pass


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


def _read_rows(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    rows = manifest.get("pairs")
    if isinstance(rows, list):
        return [dict(row) for row in rows]
    source = manifest.get("pairs_path")
    if source:
        path = (manifest_path.parent / str(source)).resolve()
        if not path.is_file():
            raise DatasetBuildBlocked(f"citation pair source is missing: {path}")
        if path.suffix == ".jsonl":
            return [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        payload = json.loads(path.read_text(encoding="utf-8"))
        return list(payload if isinstance(payload, list) else payload.get("pairs", []))
    raise DatasetBuildBlocked("no licensed pair source was provided; acquisition is NOT_RUN")


def _read_source_licence_manifest(
    manifest: dict[str, Any], manifest_path: Path
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    reference = str(manifest.get("source_licence_manifest") or "").strip()
    if not reference:
        raise DatasetBuildBlocked("source licence manifest is required; acquisition is NOT_RUN")
    path = (manifest_path.parent / reference).resolve()
    if not path.is_file():
        raise DatasetBuildBlocked(f"source licence manifest is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
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
    splits = grouped_split(rows, seed=seed)
    report = dataset_manifest(
        splits,
        source_manifest_digest=canonical_digest(source_manifest),
        code_digest=canonical_digest({"tool": "build_citation_dataset", "version": "2.0.0"}),
    )
    counts = {
        str(label): sum(row.get("label") == label for row in rows)
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
    (output_dir / "DATA-LICENCE.md").write_text(
        "# Data licence\n\nThis manifest is valid only when every source has explicit permitted use and attribution evidence.\n",
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
    except (OSError, json.JSONDecodeError, DatasetValidationError, DatasetBuildBlocked) as exc:
        print(json.dumps({"status": "not_run", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "frozen" else 2


if __name__ == "__main__":
    raise SystemExit(main())
