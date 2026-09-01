#!/usr/bin/env python3
"""Run a bounded local RPM benchmark and emit reproducible measurements."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.programme_store import ProgrammeStore  # noqa: E402
from swos_runtime.research_memory import ResearchScope  # noqa: E402


def run_benchmark(repository: str | Path, *, item_count: int = 1000) -> dict[str, object]:
    if item_count <= 0 or item_count > 100_000:
        raise ValueError("item_count must be between 1 and 100000")
    store = ProgrammeStore(repository, lock_timeout_seconds=5.0)
    store.initialize()
    scope = ResearchScope("benchmark", "rpm", "local")
    start = time.perf_counter()
    for index in range(item_count):
        store.append_event(scope, "write", f"item-{index}", {"status": "active", "n": index})
    write_seconds = time.perf_counter() - start
    samples = []
    for index in range(min(10_000, item_count)):
        began = time.perf_counter()
        store.get_projection(scope, f"item-{index}")
        samples.append((time.perf_counter() - began) * 1000)
    return {
        "schema_version": "2.0.0",
        "status": "measured",
        "item_count": item_count,
        "write_seconds": write_seconds,
        "lookup_p95_ms": statistics.quantiles(samples, n=20)[18] if len(samples) >= 20 else max(samples),
        "chain_head": store.chain_head(scope),
        "chain_errors": store.verify_chain(scope),
        "environment": {"python": platform.python_version(), "os": platform.platform(), "sqlite": store.schema_version()},
        "limitations": ["Local SQLite measurement only; not a hosted throughput claim."],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--items", type=int, default=1000)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = run_benchmark(args.repository, item_count=args.items)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
