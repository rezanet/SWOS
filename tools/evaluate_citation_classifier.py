"""Evaluate a verified citation artifact on a locked split without mutation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def evaluate(
    model_manifest_path: Path | str,
    calibration_path: Path | str,
    locked_test_path: Path | str,
    predictions_path: Path | str,
    report_path: Path | str,
) -> dict[str, Any]:
    model = json.loads(Path(model_manifest_path).read_text(encoding="utf-8"))
    calibration = json.loads(Path(calibration_path).read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in Path(locked_test_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        result = {
            "schema_version": "2.0.0",
            "status": "not_run",
            "reason": "locked test is empty",
            "locked_test_count": 0,
        }
    elif model.get("status") != "frozen" or calibration.get("status") != "frozen":
        result = {
            "schema_version": "2.0.0",
            "status": "not_run",
            "reason": "verified model and calibration are required",
            "locked_test_count": len(rows),
        }
    else:
        result = {
            "schema_version": "2.0.0",
            "status": "not_run",
            "reason": "production inference adapter is not available in this offline checkout",
            "locked_test_count": len(rows),
        }
    predictions_path = Path(predictions_path)
    report_path = Path(report_path)
    for path in (predictions_path, report_path):
        if path.exists():
            raise RuntimeError(f"immutable evaluation output already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path.write_text("", encoding="utf-8")
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
    return 2 if report.get("status") != "frozen" else 0


if __name__ == "__main__":
    raise SystemExit(main())
