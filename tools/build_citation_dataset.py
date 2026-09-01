"""Build a licensed, adjudicated, leakage-checked citation corpus offline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_dataset import (  # noqa: E402
    DatasetValidationError,
    dataset_manifest,
    grouped_split,
)
from swos_runtime.models import canonical_digest  # noqa: E402

MIN_TOTAL = 6000
MIN_PER_LABEL = 600
MIN_PER_DISCIPLINE = 300
MIN_LOCKED = 1500


class DatasetBuildBlocked(RuntimeError):
    pass


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


def build_dataset(
    manifest_path: Path | str, output_dir: Path | str, *, seed: int = 0
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise DatasetBuildBlocked(f"immutable dataset output already exists: {output_dir}")
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = _read_rows(source_manifest, manifest_path)
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
        "total": MIN_TOTAL,
        "per_label": MIN_PER_LABEL,
        "per_discipline": MIN_PER_DISCIPLINE,
        "locked_test": MIN_LOCKED,
    }
    report["counts"] = {"total": len(rows), "per_label": counts, "per_discipline": disciplines}
    report["status"] = (
        "frozen"
        if len(rows) >= MIN_TOTAL and len(splits.get("locked_test", [])) >= MIN_LOCKED
        else "blocked_below_release_floor"
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
