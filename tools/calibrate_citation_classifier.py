"""Fit calibration only from a permitted calibration split."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_calibration import fit_temperature  # noqa: E402
from swos_runtime.models import canonical_digest  # noqa: E402


def calibrate(
    model_manifest_path: Path | str, calibration_split_path: Path | str, output_path: Path | str
) -> dict:
    model = json.loads(Path(model_manifest_path).read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in Path(calibration_split_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        any(str(row.get("split")) == "locked_test" for row in rows)
        or Path(calibration_split_path).name == "locked_test.jsonl"
    ):
        raise RuntimeError("locked-test data is not permitted during calibration")
    if model.get("status") != "frozen" or not model.get("verified") or not rows:
        result = {
            "schema_version": "2.0.0",
            "status": "not_run",
            "reason": "verified model and non-empty calibration split are required",
            "model_manifest_digest": canonical_digest(model),
        }
    else:
        logits = [row.get("logits") for row in rows]
        labels = [row.get("label") for row in rows]
        if any(not isinstance(row, list) for row in logits) or any(
            label in (None, "") for label in labels
        ):
            result = {
                "schema_version": "2.0.0",
                "status": "not_run",
                "reason": "calibration rows must contain model logits and labels",
                "model_manifest_digest": canonical_digest(model),
            }
        else:
            artifact = fit_temperature(
                logits,
                labels,
                model_digest=str(model.get("model_digest") or ""),
                dataset_manifest_digest=str(model.get("dataset_manifest_digest") or ""),
                ontology_digest=str(model.get("ontology_digest") or ""),
            )
            result = {
                "schema_version": "2.0.0",
                "status": "frozen",
                **artifact.to_dict(),
                "model_manifest_digest": canonical_digest(model),
                "locked_test_used": False,
            }
    output_path = Path(output_path)
    if output_path.exists():
        raise RuntimeError(f"immutable calibration output already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--calibration-split", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = calibrate(args.model_manifest, args.calibration_split, args.out)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "not_run", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 2 if result.get("status") != "frozen" else 0


if __name__ == "__main__":
    raise SystemExit(main())
