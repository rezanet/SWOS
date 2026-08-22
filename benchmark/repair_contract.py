#!/usr/bin/env python3
"""Deterministic Milestone-1 repair contract for the governed benchmark slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.runner import load_corpus
from swos_prose.providers.rewrite_base import RewriteCandidate
from swos_prose.providers.rewrite_mock import StaticRewriteProvider
from swos_prose.rewrite import polish_text

POSITIVE_IDS = {f"repair-{index:03d}" for index in range(1, 6)}
NEGATIVE_ID = "repair-006"


class SourceLicensedRepairProvider:
    def __init__(self, source: str):
        self.source = source
        self.calls = 0

    def repair(self, **_: Any) -> RewriteCandidate:
        self.calls += 1
        return RewriteCandidate(candidate_text=self.source)


def run_contract() -> dict[str, Any]:
    fixtures = [item for item in load_corpus() if item["benchmark_group"] == "repair"]
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    ids = {item["fixture_id"] for item in fixtures}
    expected_ids = POSITIVE_IDS | {NEGATIVE_ID}
    if ids != expected_ids:
        failures.append(
            f"repair fixture IDs differ: expected {sorted(expected_ids)}, found {sorted(ids)}"
        )

    for fixture in fixtures:
        repairer = SourceLicensedRepairProvider(fixture["source"])
        result = polish_text(
            source=fixture["source"],
            rewrite_provider=StaticRewriteProvider(fixture["semantic_probe_candidate"]),
            verifier_provider=None,
            assurance=fixture["assurance"],
            run_diagnostics=False,
            repair_provider=repairer,
        )
        records.append(
            {
                "fixture_id": fixture["fixture_id"],
                "verification_status": result.verification_status,
                "repair_success": result.repair_success,
                "repair_attempt_count": len(result.repair_attempts),
                "repair_provider_calls": repairer.calls,
                "used_source_fallback": result.used_source_fallback,
                "safe_for_automatic_use": result.safe_for_automatic_use,
                "final_text_equals_source": result.final_text == fixture["source"],
                "repair_failure_reason": result.repair_failure_reason,
            }
        )
        fixture_id = fixture["fixture_id"]
        if fixture_id in POSITIVE_IDS:
            if not (
                result.verification_status == "PASS"
                and result.repair_success
                and len(result.repair_attempts) == 1
                and repairer.calls == 1
                and result.safe_for_automatic_use
                and result.final_text == fixture["source"]
                and not result.used_source_fallback
            ):
                failures.append(f"{fixture_id} did not satisfy positive repair contract")
        elif fixture_id == NEGATIVE_ID:
            if not (
                result.verification_status == "REJECT"
                and not result.repair_success
                and not result.repair_attempts
                and repairer.calls == 0
                and result.final_text == fixture["source"]
                and result.used_source_fallback
            ):
                failures.append(f"{fixture_id} did not bypass repair as a hard invariant")

    return {
        "contract": "swos-prose-m1-bounded-repair",
        "fixture_count": len(fixtures),
        "positive_fixture_count": len(POSITIVE_IDS),
        "negative_fixture_count": 1,
        "failures": failures,
        "passed": not failures,
        "records": records,
        "note": "This deterministic contract proves orchestration/localisation/confinement. It does not claim stochastic model repair success on arbitrary prose.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the SWOS Prose M1 repair contract")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run_contract()
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
