#!/usr/bin/env python3
"""Governed benchmark harness for the active SWOS Prose G-Prose95 benchmark.

The benchmark deliberately separates four questions:

* validate: Is the active 76-case corpus well-formed, and do deterministic diagnostics
  obey their fail-closed fixture contract?
* safety: Does the semantic verifier ever PASS a human-labelled material change?
* efficiency: How many provider tokens would the current diagnostics abstentions
  avoid relative to an observed diagnostics-disabled polish run?
* stability: Across repeated draws of the 16 governed live probes, how does
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
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_prose.cost import configured_cost_rates
from swos_prose.diagnostics import diagnose_polish
from swos_prose.modes import SUPPORTED_MODES, SUPPORTED_PRESETS, writer_policy
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.openai_responses import OpenAIResponsesSemanticVerifierProvider
from swos_prose.providers.openai_rewrite import OpenAIResponsesRewriteProvider
from swos_prose.rewrite import polish_text

BENCHMARK_VERSION = "0.4.0-g-prose95"
SCHEMA_VERSION = "1.0"
ACTIVE_CORPUS_COUNT = 76
DEFAULT_CORPUS = ROOT / "benchmark" / "corpus"
FIXTURE_SCHEMA = ROOT / "benchmark" / "fixture_schema.json"
REPORT_SCHEMA = ROOT / "benchmark" / "report_schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cost_method() -> dict[str, Any]:
    rates = configured_cost_rates()
    return {
        "available": rates is not None,
        "rates": rates,
        "input_rate_env": "SWOS_PROSE_INPUT_USD_PER_1K",
        "output_rate_env": "SWOS_PROSE_OUTPUT_USD_PER_1K",
        "note": (
            "Cost is an optional estimate from explicit input/output USD-per-1K-token rates; "
            "missing or invalid pricing is reported as unavailable, never as zero."
        ),
    }


def _resolved_model(model: str | None, env_name: str, default: str = "gpt-5.6") -> str:
    return model or os.environ.get(env_name, default)


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
    if fixture["mode"] not in SUPPORTED_MODES:
        errors.append(f"mode must be one of {SUPPORTED_MODES}")
    preset = fixture.get("preset")
    if preset is not None and preset not in SUPPORTED_PRESETS:
        errors.append(f"preset must be one of {SUPPORTED_PRESETS} or null")
    try:
        writer_policy(fixture["mode"], preset)
    except ValueError as exc:
        errors.append(str(exc))
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
            mode=fixture["mode"],
            preset=fixture.get("preset"),
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
            "mode_preset_matrix": dict(
                sorted(
                    Counter(
                        f"{item['mode']}::{item.get('preset') or 'none'}" for item in fixtures
                    ).items()
                )
            ),
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
        "performance": {"cost": _cost_method()},
        "records": [],
    }


def _require_live() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for live benchmark modes.")


def _semantic_record(
    fixture: dict[str, Any], result: Any, draw: int = 1, latency_ms: float | None = None
) -> dict[str, Any]:
    status = result.status.value
    unsafe_pass = fixture["semantic_relation"] == "material_change" and status == "PASS"
    verifier_calls = getattr(result, "verifier_call_count", int(bool(result.verifier_used)))
    return {
        "fixture_id": fixture["fixture_id"],
        "draw": draw,
        "mode": fixture["mode"],
        "preset": fixture.get("preset"),
        "semantic_relation": fixture["semantic_relation"],
        "status": status,
        "unsafe_pass": unsafe_pass,
        "verifier_used": result.verifier_used,
        "verifier_skip_reason": result.verifier_skip_reason,
        "semantic_deltas": [delta.to_dict() for delta in result.semantic_deltas],
        "token_usage": result.token_usage,
        "cost_estimate": result.cost_estimate,
        "latency_ms": latency_ms,
        "provider_calls": {
            "rewrite": 0,
            "verifier": verifier_calls,
            "repair": 0,
            "total": verifier_calls,
        },
        "verifier_notes": list(result.verifier_notes),
        "context_safety": result.context_safety,
    }


def _aggregate_cost(records: list[dict[str, Any]], cost_key: str = "cost_estimate") -> float | None:
    calls = [record for record in records if record.get("provider_calls", {}).get("total", 0) > 0]
    if not calls:
        return 0.0
    values = [record.get(cost_key) for record in calls]
    if any(value is None for value in values):
        return None
    return round(sum(float(value) for value in values), 10)


def _provider_call_summary(records: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"rewrite": 0, "verifier": 0, "repair": 0, "total": 0}
    for record in records:
        for key in totals:
            totals[key] += int(record.get("provider_calls", {}).get(key, 0))
    return totals


def run_safety(
    fixtures: list[dict[str, Any]], verifier_model: str | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _require_live()
    provider = OpenAIResponsesSemanticVerifierProvider(model=verifier_model)
    records: list[dict[str, Any]] = []
    for fixture in fixtures:
        started = perf_counter()
        result = verify_rewrite(
            source=fixture["source"],
            candidate=fixture["semantic_probe_candidate"],
            assurance=fixture["assurance"],
            verifier_provider=provider,
            context_before=fixture.get("context_before"),
            context_after=fixture.get("context_after"),
        )
        records.append(
            _semantic_record(fixture, result, latency_ms=(perf_counter() - started) * 1000)
        )

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
        "provider_calls": _provider_call_summary(records),
        "latency_ms_total": round(sum(record["latency_ms"] or 0 for record in records), 3),
        "average_latency_ms": round(
            sum(record["latency_ms"] or 0 for record in records) / len(records), 3
        )
        if records
        else 0.0,
        "cost_estimate_total": _aggregate_cost(records),
        "cost": _cost_method(),
        "model_identity": {"verifier": provider.model},
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
    verifier_usage = getattr(result, "verifier_token_usage", None)
    if verifier_usage is not None:
        _sum_usage(verifier_usage, totals)
    elif result.verification is not None:
        _sum_usage(result.verification.token_usage, totals)
    return totals


def _combined_result_cost(result: Any) -> float | None:
    """Sum configured costs for every provider call represented by a result."""

    costs: list[float | None] = []
    rewrite_calls = getattr(
        result,
        "rewrite_call_count",
        int(not result.generation_skipped_by_diagnostics),
    )
    if rewrite_calls:
        costs.append(result.rewrite_cost_estimate)
    for attempt in result.repair_attempts:
        if getattr(attempt, "provider_called", True):
            costs.append(attempt.cost_estimate)
    verifier_calls = getattr(
        result,
        "verifier_call_count",
        int(result.verification is not None and result.verification.verifier_used),
    )
    if verifier_calls:
        verifier_cost = getattr(result, "verifier_cost_estimate", None)
        if verifier_cost is None and result.verification is not None:
            verifier_cost = result.verification.cost_estimate
        costs.append(verifier_cost)
    if not costs:
        return 0.0
    if any(value is None for value in costs):
        return None
    return round(sum(float(value) for value in costs), 10)


def _result_provider_calls(result: Any) -> dict[str, int]:
    rewrite = getattr(
        result,
        "rewrite_call_count",
        int(not result.generation_skipped_by_diagnostics),
    )
    repair = sum(
        1 for attempt in result.repair_attempts if getattr(attempt, "provider_called", True)
    )
    verifier = getattr(
        result,
        "verifier_call_count",
        int(result.verification is not None and result.verification.verifier_used),
    )
    return {
        "rewrite": rewrite,
        "verifier": verifier,
        "repair": repair,
        "total": rewrite + verifier + repair,
    }


def _mode_preset_performance(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[f"{record['mode']}::{record.get('preset') or 'none'}"].append(record)
    result: dict[str, dict[str, Any]] = {}
    for key, items in sorted(grouped.items()):
        latencies = [item["latency_ms"] for item in items if item.get("latency_ms") is not None]
        result[key] = {
            "fixture_count": len(items),
            "provider_calls": _provider_call_summary(items),
            "baseline_token_usage": dict(
                sorted(
                    {
                        token: sum(
                            item.get("baseline_token_usage", {}).get(token, 0) for item in items
                        )
                        for token in {
                            token
                            for item in items
                            for token in item.get("baseline_token_usage", {})
                        }
                    }.items()
                )
            ),
            "baseline_cost_estimate_total": _aggregate_cost(items, "baseline_cost_estimate"),
            "average_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
        }
    return result


def _repair_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    attempt_counts = Counter(record["repair_attempt_count"] for record in records)
    outcomes = Counter(
        (
            "success"
            if record["repair_success"]
            else "failed"
            if record["repair_attempt_count"]
            else "not_attempted"
        )
        for record in records
    )
    attempted = [record for record in records if record["repair_attempt_count"]]
    successes = sum(1 for record in attempted if record["repair_success"])
    return {
        "cases_attempted": len(attempted),
        "cases_with_provider_call": sum(
            1 for record in records if record["provider_calls"]["repair"]
        ),
        "total_attempts": sum(record["repair_attempt_count"] for record in records),
        "successes": successes,
        "success_rate": successes / len(attempted) if attempted else 0.0,
        "fallback_count": sum(1 for record in records if record["used_source_fallback"]),
        "attempt_count_distribution": dict(sorted((str(k), v) for k, v in attempt_counts.items())),
        "outcome_counts": dict(sorted(outcomes.items())),
        "note": "Repair records include every bounded attempt, outcome, fallback, and provider-call count.",
    }


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
    model_identity = {
        "rewriter": rewriter.model,
        "verifier": verifier.model,
        "repair": rewriter.model,
    }

    total_without: dict[str, int] = {}
    saved: dict[str, int] = {}
    records: list[dict[str, Any]] = []
    unsafe_abstentions: list[str] = []
    baseline_costs: list[float | None] = []
    saved_costs: list[float | None] = []

    for fixture in fixtures:
        diagnostics_started = perf_counter()
        diagnostics = diagnose_polish(
            fixture["source"],
            context_before=fixture.get("context_before"),
            context_after=fixture.get("context_after"),
            mode=fixture["mode"],
            preset=fixture.get("preset"),
        )
        diagnostics_latency_ms = (perf_counter() - diagnostics_started) * 1000
        would_skip = diagnostics.no_change_recommended
        if would_skip and fixture["diagnostics_expectation"]["must_not_abstain"]:
            unsafe_abstentions.append(fixture["fixture_id"])

        rewrite_started = perf_counter()
        result = polish_text(
            source=fixture["source"],
            rewrite_provider=rewriter,
            verifier_provider=verifier,
            assurance=fixture["assurance"],
            context_before=fixture.get("context_before"),
            context_after=fixture.get("context_after"),
            run_diagnostics=False,
            mode=fixture["mode"],
            preset=fixture.get("preset"),
        )
        latency_ms = (perf_counter() - rewrite_started) * 1000
        usage = _combined_result_usage(result)
        cost = _combined_result_cost(result)
        baseline_costs.append(cost)
        if would_skip:
            saved_costs.append(cost)
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
                "verification_status": result.verification_status,
                "used_source_fallback": result.used_source_fallback,
                "final_text_equals_source": result.final_text == fixture["source"],
                "repair_attempts": [attempt.to_dict() for attempt in result.repair_attempts],
                "repair_attempt_count": len(result.repair_attempts),
                "repair_success": result.repair_success,
                "repair_failure_reason": result.repair_failure_reason,
                "baseline_token_usage": usage,
                "baseline_cost_estimate": cost,
                "mode": fixture["mode"],
                "preset": fixture.get("preset"),
                "latency_ms": latency_ms,
                "diagnostics_latency_ms": diagnostics_latency_ms,
                "provider_calls": _result_provider_calls(result),
                "model_identity": model_identity,
            }
        )

    with_diagnostics = {
        key: total_without.get(key, 0) - saved.get(key, 0)
        for key in set(total_without) | set(saved)
    }
    total_base = total_without.get("total_tokens", 0)
    total_saved = saved.get("total_tokens", 0)
    savings_pct = (100.0 * total_saved / total_base) if total_base else None
    baseline_cost = (
        None
        if any(value is None for value in baseline_costs)
        else round(sum(float(value) for value in baseline_costs), 10)
    )
    saved_cost = (
        None
        if any(value is None for value in saved_costs)
        else round(sum(float(value) for value in saved_costs), 10)
    )
    with_diagnostics_cost = (
        round(baseline_cost - saved_cost, 10)
        if baseline_cost is not None and saved_cost is not None
        else None
    )
    baseline_calls = _provider_call_summary(records)
    saved_calls = {
        key: sum(item["provider_calls"][key] for item in records if item["diagnostics_would_skip"])
        for key in ("rewrite", "verifier", "repair", "total")
    }
    latencies = [item["latency_ms"] for item in records]

    return {
        "method": "observed_no_diagnostics_plus_exact_skip_counterfactual",
        "baseline_without_diagnostics": dict(sorted(total_without.items())),
        "counterfactual_with_diagnostics": dict(sorted(with_diagnostics.items())),
        "tokens_saved_by_diagnostics": dict(sorted(saved.items())),
        "total_token_savings_percent": savings_pct,
        "baseline_provider_calls": baseline_calls,
        "provider_calls_saved_by_diagnostics": saved_calls,
        "counterfactual_provider_calls": {
            key: baseline_calls[key] - saved_calls[key] for key in baseline_calls
        },
        "baseline_cost_estimate_total": baseline_cost,
        "cost_saved_by_diagnostics": saved_cost,
        "counterfactual_cost_estimate_total": with_diagnostics_cost,
        "cost_savings_percent": (
            100.0 * saved_cost / baseline_cost
            if baseline_cost not in (None, 0) and saved_cost is not None
            else None
        ),
        "cost": _cost_method(),
        "model_identity": model_identity,
        "mode_preset_performance": _mode_preset_performance(records),
        "repair": _repair_summary(records),
        "latency_ms_total": round(sum(latencies), 3),
        "average_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
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
            started = perf_counter()
            result = verify_rewrite(
                source=fixture["source"],
                candidate=fixture["semantic_probe_candidate"],
                assurance=fixture["assurance"],
                verifier_provider=provider,
                context_before=fixture.get("context_before"),
                context_after=fixture.get("context_after"),
            )
            record = _semantic_record(
                fixture,
                result,
                draw=draw,
                latency_ms=(perf_counter() - started) * 1000,
            )
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
        "provider_calls": _provider_call_summary(records),
        "latency_ms_total": round(sum(record["latency_ms"] or 0 for record in records), 3),
        "average_latency_ms": round(
            sum(record["latency_ms"] or 0 for record in records) / len(records), 3
        )
        if records
        else 0.0,
        "cost_estimate_total": _aggregate_cost(records),
        "cost": _cost_method(),
        "model_identity": {"verifier": provider.model},
        "repeated_verifier_overhead": {
            "total_draws": len(records),
            "verifier_calls": _provider_call_summary(records)["verifier"],
            "note": "Measured wall-clock and provider-call totals across repeated verifier draws.",
        },
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
    report["performance"]["model_identity"] = {
        "rewriter": _resolved_model(rewrite_model, "SWOS_PROSE_OPENAI_REWRITE_MODEL"),
        "verifier": _resolved_model(verifier_model, "SWOS_PROSE_OPENAI_MODEL"),
        "repair": _resolved_model(rewrite_model, "SWOS_PROSE_OPENAI_REWRITE_MODEL"),
    }
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
    parser = argparse.ArgumentParser(description="Run the governed SWOS Prose G-Prose95 benchmark")
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
