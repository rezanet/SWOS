"""Enforce the governed executable-Python coverage policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CRITICAL_THRESHOLDS = {
    "swos_prose/repair.py": 80.0,
    "swos_prose/pipeline.py": 85.0,
    "swos_prose/verify/causal_scope.py": 90.0,
    "swos_prose/verify/deterministic.py": 90.0,
    "swos_prose/verify/propositions.py": 85.0,
}


def _normalise_path(path: str) -> str:
    return path.replace("\\", "/")


def _load_report(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read coverage report {path}: {exc}") from exc

    if not isinstance(report, dict) or "totals" not in report or "files" not in report:
        raise SystemExit(f"Coverage report {path} has no usable totals/files sections")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage-json",
        type=Path,
        default=Path("coverage.json"),
        help="coverage.py JSON report (default: coverage.json)",
    )
    parser.add_argument(
        "--minimum",
        type=float,
        default=80.0,
        help="minimum total executable-Python coverage percentage (default: 80)",
    )
    args = parser.parse_args()

    report = _load_report(args.coverage_json)
    total = float(report["totals"]["percent_covered"])
    files = {_normalise_path(str(path)): details for path, details in report["files"].items()}
    failures: list[str] = []

    print(f"Executable Python scope: swos_prose ({total:.2f}%)")
    print(f"Required total floor: {args.minimum:.2f}%")
    if total < args.minimum:
        failures.append(f"total coverage {total:.2f}% is below {args.minimum:.2f}%")

    print("Critical module floors:")
    for path, minimum in CRITICAL_THRESHOLDS.items():
        details = files.get(path)
        if not isinstance(details, dict) or not isinstance(details.get("summary"), dict):
            failures.append(f"{path} is missing from the coverage report")
            print(f"  {path}: MISSING (required {minimum:.2f}%)")
            continue
        covered = float(details["summary"]["percent_covered"])
        print(f"  {path}: {covered:.2f}% (required {minimum:.2f}%)")
        if covered < minimum:
            failures.append(f"{path} coverage {covered:.2f}% is below {minimum:.2f}%")

    if failures:
        print("Coverage policy: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Coverage policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
