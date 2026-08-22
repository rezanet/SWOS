#!/usr/bin/env python3
"""Governed benchmark harness for the active SWOS Prose M1 benchmark.

The benchmark deliberately separates four questions:

* validate: Is the active 56-case corpus well-formed, and do deterministic diagnostics
  obey their fail-closed fixture contract?
* safety: Does the semantic verifier ever PASS a human-labelled material change?
* efficiency: How many provider tokens would the current diagnostics abstentions
  avoid relative to an observed diagnostics-disabled polish run?
* stability: Across repeated draws of the 11 inherited live probes, how does
  PASS/REVIEW/REJECT vary?

Diagnostics are not scored as a grammar classifier. An unreviewed good sentence
that proceeds to rewrite is conservative inefficiency, not a correctness error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_prose.diagnostics import diagnose_polish
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.openai_responses import OpenAIResponsesSemanticVerifierProvider
from swos_prose.providers.openai_rewrite import OpenAIResponsesRewriteProvider
from swos_prose.rewrite import polish_text

BENCHMARK_VERSION = "0.3.0-m1"
SCHEMA_VERSION = "1.0"
ACTIVE_CORPUS_COUNT = 56
DEFAULT_CORPUS = ROOT / "benchmark" / "corpus"
FIXTURE_SCHEMA = ROOT / "benchmark" / "fixture_schema.json"
REPORT_SCHEMA = ROOT / "benchmark" / "report_schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_hash(fixtures: list[dict[str, Any]]) -> str:
    payload = json.dumps(fixtures, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_corpus(corpus_dir: str | Path = DEFAULT_CORPUS) -> list[dict[str, Any]]:
    root = Path(corpus_dir)
    files = sorted(root.glob("prose-*.json"))
    fixtures = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    return fixtures


def validate_fixture_shape(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "fixture_id",
        "category",
        "benchmark_group",
        "mode",
        "assurance",
        "source",
        "semantic_probe_candidate",
        "semantic_relation",
        "diagnostics_expectation",
        "stability_probe",
        "notes",
    }
    missing = sorted(required - fixture.keys())
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
        return errors
    if fixture["mode"] != "polish":
        errors.append("mode must be polish")
    if fixture["assurance"] != "strict":
        errors.append("assurance must be strict")
    if fixture["semantic_relation"] not in {"equivalent", "material_change"}:
        errors.append("semantic_relation must be equivalent or material_change")
    expected = fixture["diagnostics_expectation"]
    if not isinstance(expected, dict):
        errors.append("diagnostics_expectation must be an object")
    else:
        if expected.get("outcome") not in {"NO_CHANGE_RECOMMENDED", "PROCEED_TO_REWRITE"}:
            errors.append("invalid diagnostics expectation")
        if not isinstance(expected.get("must_not_abstain"), bool):
            errors.append("must_not_abstain must be boolean")
    for key in ("source", "semantic_probe_candidate"):
        if not isinstance(fixture.get(key), str) or not fixture[key]:
            errors.append(f"{key} must be a non-empty string")
    return errors


def _json_schema_errors(fixtures: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    try:
        import jsonschema
    except ImportError:
        return False, []
    schema = json.loads(FIXTURE_SCHEMA.read_text(encoding="utf-8"))
    errors: list[dict[str, Any]] = []
    validator = jsonschema.Draft202012Validator(schema)
    for fixture in fixtures:
        for error in sorted(validator.iter_errors(fixture), key=lambda item: list(item.path)):
            errors.append(
                {
                    "fixture_id": fixture.get("fixture_id"),
                    "path": list(error.path),
                    "message": error.message,
                }
            )
    return True, errors


def validate_corpus(
    fixtures: list[dict[str, Any]], expect_count: int | None = None
) -> dict[str, Any]:
    shape_errors: list[dict[str, Any]] = []
    ids = [item.get("fixture_id") for item in fixtures]
    duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
    for fixture in fixtures:
        errors = validate_fixture_shape(fixture)
        if errors:
            shape_errors.append({"fixture_id": fixture.get("fixture_id"), "errors": errors})

    if expect_count is not None and len(fixtures) != expect_count:
        shape_errors.append(
            {
                "fixture_id": None,
                "errors": [f"expected {expect_count} fixtures, found {len(fixtures)}"],
            }
        )

    diagnostic_records: list[dict[str, Any]] = []
    unsafe_abstentions: list[str] = []
    expectation_mismatches: list[str] = []
    missing_expected_signals: list[str] = []

    for fixture in fixtures:
        if shape_errors and any(e["fixture_id"] == fixture.get("fixture_id") for e in shape_errors):
            continue
        diagnostics = diagnose_polish(
            fixture["source"],
            context_before=fixture.get("context_before"),
            context_after=fixture.get("context_after"),
        )
        expected = fixture["diagnostics_expectation"]
        actual = diagnostics.recommendation
        if expected["must_not_abstain"] and actual == "NO_CHANGE_RECOMMENDED":
            unsafe_abstentions.append(fixture["fixture_id"])
        if actual != expected["outcome"]:
            expectation_mismatches.append(fixture["fixture_id"])
        expected_signal = expected.get("expected_signal")
        if expected_signal and expected_signal not in diagnostics.signals:
            missing_expected_signals.append(fixture["fixture_id"])
        diagnostic_records.append(
            {
                "fixture_id": fixture["fixture_id"],
                "expected": expected["outcome"],
                "actual": actual,
                "must_not_abstain": expected["must_not_abstain"],
                "signals": list(diagnostics.signals),
                "positive_evidence": list(diagnostics.positive_evidence),
            }
        )

    schema_checked, schema_errors = _json_schema_errors(fixtures)
    return {
        "shape_errors": shape_errors,
        "json_schema_checked": schema_checked,
        "json_schema_errors": schema_errors,
        "duplicate_fixture_ids": duplicates,
        "unsafe_abstentions": unsafe_abstentions,
        "diagnostics_expectation_mismatches": expectation_mismatches,
        "missing_expected_signals": missing_expected_signals,
        "diagnostics_records": diagnostic_records,
        "valid": not (
            shape_errors
            or schema_errors
            or duplicates
            or unsafe_abstentions
            or expectation_mismatches
            or missing_expected_signals
        ),
    }


def _base_report(fixtures: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    groups = Counter(item["benchmark_group"] for item in fixtures)
    relations = Counter(item["semantic_relation"] for item in fixtures)
    validation = validate_corpus(fixtures)
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "mode": mode,
        "generated_at": _utc_now(),
        "corpus": {
            "fixture_count": len(fixtures),
            "sha256": _canonical_hash(fixtures),
            "groups": dict(sorted(groups.items())),
            "semantic_relations": dict(sorted(relations.items())),
            "stability_probe_count": sum(1 for item in fixtures if item["stability_probe"]),
        },
        "diagnostics_contract": {
            "unsafe_abstentions": validation["unsafe_abstentions"],
            "expectation_mismatches": validation["diagnostics_expectation_mismatches"],
            "missing_expected_signals": validation["missing_expected_signals"],
            "reviewed_abstentions": sum(
                1
                for item in validation["diagnostics_records"]
                if item["actual"] == "NO_CHANGE_RECOMMENDED"
            ),
            "note": (
                "Diagnostics are evaluated for unsafe abstention and governed coverage, "
                "not as a general grammar/style classifier."
            ),
        },
        "semantic_safety": None,
        "token_efficiency": None,
        "stability": None,
        "records": [],
    }


def _require_live() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for live benchmark modes.")


def _semantic_record(fixture: dict[str, Any], result: Any, draw: int = 1) -> dict[str, Any]:
    status = result.status.value
    unsafe_pass = fixture["semantic_relation"] == "material_change" and status == "PASS"
    return {
        "fixture_id": fixture["fixture_id"],
        "draw": draw,
        "semantic_relation": fixture["semantic_relation"],
        "status": status,
        "unsafe_pass": unsafe_pass,
        "verifier_used": result.verifier_used,
        "verifier_skip_reason": result.verifier_skip_reason,
        "semantic_deltas": [delta.to_dict() for delta in result.semantic_deltas],
        "token_usage": result.token_usage,
        "verifier_notes": list(result.verifier_notes),
    }


def run_safety(
    fixtures: list[dict[str, Any]], verifier_model: str | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _require_live()
    provider = OpenAIResponsesSemanticVerifierProvider(model=verifier_model)
    records: list[dict[str, Any]] = []
    for fixture in fixtures:
        result = verify_rewrite(
            source=fixture["source"],
            candidate=fixture["semantic_probe_candidate"],
            assurance=fixture["assurance"],
            verifier_provider=provider,
        )
        records.append(_semantic_record(fixture, result))

    unsafe = [item["fixture_id"] for item in records if item["unsafe_pass"]]
    equivalent_counts = Counter(
        item["status"] for item in records if item["semantic_relation"] == "equivalent"
    )
    changed_counts = Counter(
        item["status"] for item in records if item["semantic_relation"] == "material_change"
    )
    return {
        "unsafe_pass_count": len(unsafe),
        "unsafe_pass_fixture_ids": unsafe,
        "equivalent_status_counts": dict(sorted(equivalent_counts.items())),
        "material_change_status_counts": dict(sorted(changed_counts.items())),
        "safety_gate_passed": not unsafe,
        "note": (
            "For material-change probes, PASS is unsafe. REVIEW and REJECT are fail-closed. "
            "For equivalent probes, non-PASS outcomes are reported as quality/stability costs, "
            "not safety failures."
        ),
    }, records


def _sum_usage(usage: dict[str, int] | None, totals: dict[str, int]) -> None:
    if not usage:
        return
    for key, value in usage.items():
        if isinstance(value, int):
            totals[key] = totals.get(key, 0) + value


def _combined_result_usage(result: Any) -> dict[str, int]:
    totals: dict[str, int] = {}
    _sum_usage(result.rewrite_token_usage, totals)
    for attempt in result.repair_attempts:
        _sum_usage(attempt.token_usage, totals)
    if result.verification is not None:
        _sum_usage(result.verification.token_usage, totals)
    return totals


def run_efficiency(
    fixtures: list[dict[str, Any]],
    rewrite_model: str | None,
    verifier_model: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Observe a diagnostics-disabled baseline and compute the exact skip counterfactual.

    Diagnostics do not alter the generation path for PROCEED_TO_REWRITE cases. Therefore
    the token counterfactual for the current deterministic abstention slice is the observed
    no-diagnostics total minus the observed provider usage of fixtures that diagnostics
    would skip entirely. This avoids paying for a redundant second stochastic run.
    """
    _require_live()
    rewriter = OpenAIResponsesRewriteProvider(model=rewrite_model)
    verifier = OpenAIResponsesSemanticVerifierProvider(model=verifier_model)

    total_without: dict[str, int] = {}
    saved: dict[str, int] = {}
    records: list[dict[str, Any]] = []
    unsafe_abstentions: list[str] = []

    for fixture in fixtures:
        diagnostics = diagnose_polish(
            fixture["source"],
            context_before=fixture.get("context_before"),
            context_after=fixture.get("context_after"),
        )
        would_skip = diagnostics.no_change_recommended
        if would_skip and fixture["diagnostics_expectation"]["must_not_abstain"]:
            unsafe_abstentions.append(fixture["fixture_id"])

        result = polish_text(
            source=fixture["source"],
            rewrite_provider=rewriter,
            verifier_provider=verifier,
            assurance=fixture["assurance"],
            context_before=fixture.get("context_before"),
            context_after=fixture.get("context_after"),
            run_diagnostics=False,
        )
        usage = _combined_result_usage(result)
        for key, value in usage.items():
            total_without[key] = total_without.get(key, 0) + value
            if would_skip:
                saved[key] = saved.get(key, 0) + value

        records.append(
            {
                "fixture_id": fixture["fixture_id"],
                "diagnostics_would_skip": would_skip,
                "diagnostics_signals": list(diagnostics.signals),
                "baseline_status": result.verification_status,
                "baseline_safe_for_automatic_use": result.safe_for_automatic_use,
                "baseline_token_usage": usage,
            }
        )

    with_diagnostics = {
        key: total_without.get(key, 0) - saved.get(key, 0)
        for key in set(total_without) | set(saved)
    }
    total_base = total_without.get("total_tokens", 0)
    total_saved = saved.get("total_tokens", 0)
    savings_pct = (100.0 * total_saved / total_base) if total_base else None

    return {
        "method": "observed_no_diagnostics_plus_exact_skip_counterfactual",
        "baseline_without_diagnostics": dict(sorted(total_without.items())),
        "counterfactual_with_diagnostics": dict(sorted(with_diagnostics.items())),
        "tokens_saved_by_diagnostics": dict(sorted(saved.items())),
        "total_token_savings_percent": savings_pct,
        "abstention_count": sum(1 for item in records if item["diagnostics_would_skip"]),
        "abstention_rate": (
            sum(1 for item in records if item["diagnostics_would_skip"]) / len(records)
        )
        if records
        else 0.0,
        "unsafe_abstention_count": len(unsafe_abstentions),
        "unsafe_abstention_fixture_ids": unsafe_abstentions,
        "note": (
            "This is a counterfactual on the exact current fast path: cases that do not "
            "abstain are unchanged by diagnostics, while abstaining cases make zero rewrite "
            "and verifier calls."
        ),
    }, records


def run_stability(
    fixtures: list[dict[str, Any]],
    verifier_model: str | None,
    runs: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _require_live()
    if runs < 1:
        raise ValueError("stability runs must be >= 1")
    provider = OpenAIResponsesSemanticVerifierProvider(model=verifier_model)
    probes = [item for item in fixtures if item["stability_probe"]]
    records: list[dict[str, Any]] = []
    distributions: dict[str, Counter[str]] = defaultdict(Counter)
    unsafe_passes: list[dict[str, Any]] = []

    for draw in range(1, runs + 1):
        for fixture in probes:
            result = verify_rewrite(
                source=fixture["source"],
                candidate=fixture["semantic_probe_candidate"],
                assurance=fixture["assurance"],
                verifier_provider=provider,
            )
            record = _semantic_record(fixture, result, draw=draw)
            records.append(record)
            distributions[fixture["fixture_id"]][record["status"]] += 1
            if record["unsafe_pass"]:
                unsafe_passes.append({"fixture_id": fixture["fixture_id"], "draw": draw})

    return {
        "runs_per_probe": runs,
        "probe_count": len(probes),
        "distributions": {
            fixture_id: dict(sorted(counts.items()))
            for fixture_id, counts in sorted(distributions.items())
        },
        "unsafe_pass_count": len(unsafe_passes),
        "unsafe_passes": unsafe_passes,
        "note": (
            "Variance on equivalent probes quantifies verifier stability. Any PASS on a "
            "material-change probe is a safety failure."
        ),
    }, records


def build_report(
    fixtures: list[dict[str, Any]],
    mode: str,
    rewrite_model: str | None,
    verifier_model: str | None,
    stability_runs: int,
) -> dict[str, Any]:
    report = _base_report(fixtures, mode)
    validation = validate_corpus(fixtures)
    report["records"].append(
        {"kind": "diagnostics_validation", "items": validation["diagnostics_records"]}
    )

    if mode in {"safety", "all"}:
        summary, records = run_safety(fixtures, verifier_model)
        report["semantic_safety"] = summary
        report["records"].append({"kind": "semantic_safety", "items": records})

    if mode in {"efficiency", "all"}:
        summary, records = run_efficiency(fixtures, rewrite_model, verifier_model)
        report["token_efficiency"] = summary
        report["records"].append({"kind": "token_efficiency", "items": records})

    if mode in {"stability", "all"}:
        summary, records = run_stability(fixtures, verifier_model, stability_runs)
        report["stability"] = summary
        report["records"].append({"kind": "stability", "items": records})

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the governed SWOS Prose v0.2 benchmark")
    parser.add_argument(
        "--mode",
        choices=("validate", "safety", "efficiency", "stability", "all"),
        default="validate",
    )
    parser.add_argument("--corpus-dir", default=str(DEFAULT_CORPUS))
    parser.add_argument("--output", required=True)
    parser.add_argument("--expect-count", type=int, default=ACTIVE_CORPUS_COUNT)
    parser.add_argument("--rewriter-model", default=None)
    parser.add_argument("--verifier-model", default=None)
    parser.add_argument("--stability-runs", type=int, default=5)
    parser.add_argument("--fail-on-unsafe", action="store_true")
    args = parser.parse_args()

    fixtures = load_corpus(args.corpus_dir)
    validation = validate_corpus(fixtures, expect_count=args.expect_count)
    if not validation["valid"]:
        print(json.dumps(validation, indent=2, ensure_ascii=False))
        return 2

    report = build_report(
        fixtures,
        mode=args.mode,
        rewrite_model=args.rewriter_model,
        verifier_model=args.verifier_model,
        stability_runs=args.stability_runs,
    )
    try:
        import jsonschema
    except ImportError:
        jsonschema = None
    if jsonschema is not None:
        report_schema = json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(report_schema).validate(report)

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "mode": args.mode,
                "output": str(destination),
                "corpus_size": len(fixtures),
                "unsafe_abstentions": report["diagnostics_contract"]["unsafe_abstentions"],
                "unsafe_passes": (
                    report["semantic_safety"]["unsafe_pass_count"]
                    if report["semantic_safety"] is not None
                    else None
                ),
            },
            indent=2,
        )
    )

    if args.fail_on_unsafe:
        if report["diagnostics_contract"]["unsafe_abstentions"]:
            return 1
        if report["semantic_safety"] and report["semantic_safety"]["unsafe_pass_count"]:
            return 1
        if report["token_efficiency"] and report["token_efficiency"]["unsafe_abstention_count"]:
            return 1
        if report["stability"] and report["stability"]["unsafe_pass_count"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
