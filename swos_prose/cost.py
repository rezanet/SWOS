"""Optional, explicit provider cost estimation for SWOS Prose evidence.

The engine never needs pricing data to make a safety decision. Cost is an
observability concern only, and estimates are reported as unavailable unless
both input and output USD-per-1K-token rates are explicitly configured.
"""

from __future__ import annotations

import math
import os
from typing import Any

INPUT_RATE_ENV = "SWOS_PROSE_INPUT_USD_PER_1K"
OUTPUT_RATE_ENV = "SWOS_PROSE_OUTPUT_USD_PER_1K"


def _parse_rate(name: str) -> float | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def configured_cost_rates() -> dict[str, float] | None:
    """Return configured input/output rates, or ``None`` when incomplete."""

    input_rate = _parse_rate(INPUT_RATE_ENV)
    output_rate = _parse_rate(OUTPUT_RATE_ENV)
    if input_rate is None or output_rate is None:
        return None
    return {"input_usd_per_1k": input_rate, "output_usd_per_1k": output_rate}


def estimate_cost(usage: dict[str, Any] | None) -> float | None:
    """Estimate USD cost from input/output token usage and explicit rates.

    Returning ``None`` is deliberate: missing, malformed, or partial pricing
    configuration must never be represented as a zero-cost provider call.
    """

    rates = configured_cost_rates()
    if not rates or not isinstance(usage, dict):
        return None
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not all(
        isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0
        for value in (input_tokens, output_tokens)
    ):
        return None
    value = (
        input_tokens * rates["input_usd_per_1k"] + output_tokens * rates["output_usd_per_1k"]
    ) / 1000
    return round(value, 10)
