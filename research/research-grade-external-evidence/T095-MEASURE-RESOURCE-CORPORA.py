#!/usr/bin/env python3
"""Measure T095 corpora with fail-closed CPU/memory/wall-clock records.

PREPARATION ONLY / NOT RELEASE EVIDENCE.

The harness is intentionally Linux-oriented because the frozen hosted
certification workflow runs on Ubuntu. It wraps each supplied benchmark command
with GNU `/usr/bin/time`, records wall/user/system CPU and peak resident set size,
and fail-closes when the predeclared CPU, RSS, or wall-clock limits are exceeded.

Example command template:
  --command python tools/certify_prov_roundtrip.py --fixture {corpus}

The exact production benchmark command must be approved/bound separately; this
harness merely records deterministic measurements around it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import signal
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TIME_BIN = Path("/usr/bin/time")
FORMAT = "SWOS_TIME wall=%e user=%U sys=%S maxrss_kb=%M exit=%x"
RESOURCE_LIMIT_FAILURES = {
    "FAIL_CLOSED_CPU_LIMIT",
    "FAIL_CLOSED_MEMORY_LIMIT",
}


def utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def percentile95(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot compute p95 of empty sample")
    ordered = sorted(values)
    rank = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[rank]


def parse_time(stderr: str) -> dict[str, Any]:
    lines = [line for line in stderr.splitlines() if line.startswith("SWOS_TIME ")]
    if len(lines) != 1:
        raise ValueError("GNU time emitted zero or multiple SWOS_TIME measurement lines")
    fields: dict[str, str] = {}
    for token in lines[0].split()[1:]:
        key, value = token.split("=", 1)
        fields[key] = value
    return {
        "wall_seconds": float(fields["wall"]),
        "user_cpu_seconds": float(fields["user"]),
        "system_cpu_seconds": float(fields["sys"]),
        "total_cpu_seconds": float(fields["user"]) + float(fields["sys"]),
        "max_rss_kb": int(fields["maxrss_kb"]),
        "command_exit_code": int(fields["exit"]),
    }


def _positive_float(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive number")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0:
        raise ValueError(f"{name} must be a positive number")
    return converted


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def resource_disposition(
    measurement: dict[str, Any], *, cpu_limit: float, memory_limit_kb: int
) -> str:
    """Return the frozen resource result for one successful measured run."""
    try:
        raw_cpu_seconds = measurement["total_cpu_seconds"]
        raw_max_rss_kb = measurement["max_rss_kb"]
    except (KeyError, TypeError) as exc:
        raise ValueError("measurement lacks numeric CPU/RSS fields") from exc
    if (
        isinstance(raw_cpu_seconds, bool)
        or not isinstance(raw_cpu_seconds, (int, float))
        or isinstance(raw_max_rss_kb, bool)
        or not isinstance(raw_max_rss_kb, int)
    ):
        raise ValueError("measurement CPU/RSS values must use numeric runtime types")
    cpu_seconds = float(raw_cpu_seconds)
    max_rss_kb = raw_max_rss_kb
    if not math.isfinite(cpu_seconds) or cpu_seconds < 0 or max_rss_kb < 0:
        raise ValueError("measurement CPU/RSS values must be finite and non-negative")
    if cpu_seconds > _positive_float(cpu_limit, "cpu_limit"):
        return "FAIL_CLOSED_CPU_LIMIT"
    if max_rss_kb > _positive_int(memory_limit_kb, "memory_limit_kb"):
        return "FAIL_CLOSED_MEMORY_LIMIT"
    return "MEASURED"


def repository_head() -> str | None:
    """Return the exact execution checkout head when the harness runs in Git."""
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return value if len(value) == 40 and all(c in "0123456789abcdef" for c in value) else None


def render_command(template: list[str], corpus: Path) -> list[str]:
    if not any("{corpus}" in token for token in template):
        raise ValueError("benchmark command must contain {corpus}")
    return [token.replace("{corpus}", str(corpus.resolve())) for token in template]


def run_once(command: list[str], *, timeout_seconds: float) -> dict[str, Any]:
    if not TIME_BIN.is_file():
        raise FileNotFoundError("/usr/bin/time is required for T095 peak-RSS measurement")
    argv = [str(TIME_BIN), "-f", FORMAT, "--", *command]
    started = time.time()
    monotonic = time.monotonic()
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
    observed_wall = time.monotonic() - monotonic
    base = {
        "started_at": datetime.fromtimestamp(started, timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "argv": argv,
        "argv_sha256": hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest(),
        "timed_out": timed_out,
        "observed_wall_seconds": observed_wall,
        "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "process_return_code": process.returncode,
    }
    if timed_out:
        return {**base, "status": "FAIL_CLOSED_TIMEOUT", "measurement": None}
    measurement = parse_time(stderr)
    if process.returncode != 0 or measurement["command_exit_code"] != 0:
        return {**base, "status": "FAIL_CLOSED_NONZERO_EXIT", "measurement": measurement}
    return {**base, "status": "MEASURED", "measurement": measurement}


def measure(
    corpus_manifest: Path,
    resource_limits: Path,
    output: Path,
    command_template: list[str],
    *,
    repeats: int,
) -> dict[str, Any]:
    corpus_payload = json.loads(corpus_manifest.read_text(encoding="utf-8"))
    limits = json.loads(resource_limits.read_text(encoding="utf-8"))
    limit_values = limits.get("limits")
    if not isinstance(limit_values, dict):
        raise ValueError("resource limits must contain a limits object")
    timeout_seconds = _positive_float(limit_values.get("timeout_seconds"), "timeout_seconds")
    cpu_limit = _positive_float(limit_values.get("cpu_seconds"), "cpu_seconds")
    memory_limit_kb = _positive_int(limit_values.get("max_rss_kb"), "max_rss_kb")
    max_bytes = _positive_int(limit_values.get("max_bytes"), "max_bytes")
    performance_targets = limits.get("release_performance_targets")
    if not isinstance(performance_targets, dict):
        raise ValueError("resource limits must contain release performance targets")
    p95_target = _positive_float(performance_targets.get("p95_seconds"), "p95_seconds")
    records = []
    for corpus in corpus_payload.get("corpora", []):
        corpus_path = corpus_manifest.parent / corpus["path"]
        if not corpus_path.is_file():
            raise FileNotFoundError(corpus_path)
        actual_sha = sha256(corpus_path)
        if actual_sha != corpus.get("sha256"):
            raise ValueError(f"corpus checksum mismatch: {corpus_path}")
        if corpus_path.stat().st_size > max_bytes:
            records.append(
                {
                    "corpus": corpus["name"],
                    "corpus_sha256": actual_sha,
                    "status": "FAIL_CLOSED_MAX_BYTES",
                    "runs": [],
                }
            )
            continue
        command = render_command(command_template, corpus_path)
        runs = [run_once(command, timeout_seconds=timeout_seconds) for _ in range(repeats)]
        for run in runs:
            measurement = run.get("measurement")
            if run.get("status") == "MEASURED" and isinstance(measurement, dict):
                disposition = resource_disposition(
                    measurement,
                    cpu_limit=cpu_limit,
                    memory_limit_kb=memory_limit_kb,
                )
                run["resource_disposition"] = disposition
                if disposition != "MEASURED":
                    run["status"] = disposition
            else:
                run["resource_disposition"] = run.get("status", "FAIL_CLOSED_UNKNOWN")
        measured = [
            r["measurement"]
            for r in runs
            if r.get("resource_disposition") == "MEASURED" and r.get("measurement")
        ]
        walls = [float(m["wall_seconds"]) for m in measured if m]
        cpus = [float(m["total_cpu_seconds"]) for m in measured if m]
        rss = [int(m["max_rss_kb"]) for m in measured if m]
        all_measured = len(measured) == repeats
        p95 = percentile95(walls) if all_measured else None
        dispositions = {str(r["resource_disposition"]) for r in runs}
        if dispositions & RESOURCE_LIMIT_FAILURES:
            resource_status = "FAIL_CLOSED_RESOURCE_LIMIT"
        elif not all_measured:
            resource_status = "FAIL_CLOSED_INCOMPLETE"
        else:
            resource_status = "MEASURED_WITHIN_FROZEN_CPU_MEMORY_LIMIT"
        performance_status = (
            "MEASURED_WITHIN_FROZEN_WALL_TARGET"
            if resource_status.startswith("MEASURED") and p95 is not None and p95 <= p95_target
            else (
                resource_status
                if resource_status.startswith("FAIL_CLOSED")
                else "FAIL_CLOSED_WALL_TARGET_EXCEEDED"
            )
        )
        records.append(
            {
                "corpus": corpus["name"],
                "corpus_sha256": actual_sha,
                "format": corpus.get("format"),
                "statement_count": corpus.get("statement_count"),
                "blank_node_count": corpus.get("blank_node_count"),
                "resource_limits": {
                    "cpu_seconds": cpu_limit,
                    "max_rss_kb": memory_limit_kb,
                    "timeout_seconds": timeout_seconds,
                    "wall_target_seconds": p95_target,
                },
                "limit_dispositions": sorted(dispositions),
                "runs": runs,
                "aggregate": {
                    "completed_runs": len(measured),
                    "requested_runs": repeats,
                    "wall_seconds_p95": p95,
                    "wall_seconds_median": statistics.median(walls) if walls else None,
                    "cpu_seconds_median": statistics.median(cpus) if cpus else None,
                    "max_rss_kb_peak_observed": max(rss) if rss else None,
                    "resource_gate": resource_status,
                    "wall_target_seconds": p95_target,
                    "status": performance_status,
                },
            }
        )
    payload = {
        "schema_version": "research-handoff.t095.measurements.v1",
        "status": "MEASUREMENTS_RECORDED_NOT_RELEASE_APPROVED",
        "generated_at": utc(),
        "exact_code_head": repository_head(),
        "runner_identity": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
        "corpus_manifest_sha256": sha256(corpus_manifest),
        "resource_limits_sha256": sha256(resource_limits),
        "resource_limits": {
            "cpu_seconds": cpu_limit,
            "max_rss_kb": memory_limit_kb,
            "timeout_seconds": timeout_seconds,
            "wall_target_seconds": p95_target,
        },
        "command_template": command_template,
        "command_template_sha256": hashlib.sha256(
            json.dumps(command_template, separators=(",", ":")).encode()
        ).hexdigest(),
        "measurement_backend": "/usr/bin/time -f",
        "repeats": repeats,
        "records": records,
        "release_boundary": "Measurements alone do not satisfy T095; the exact approved production command, runner identity, exact candidate head and required external approvals/evaluation must be bound by the frozen workflow.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-manifest", type=Path, required=True)
    parser.add_argument("--resource-limits", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--command", nargs=argparse.REMAINDER, required=True)
    args = parser.parse_args()
    if args.repeats < 3:
        raise SystemExit("--repeats must be >= 3")
    if not args.command:
        raise SystemExit("--command is required after --command")
    try:
        result = measure(
            args.corpus_manifest.resolve(),
            args.resource_limits.resolve(),
            args.output.resolve(),
            args.command,
            repeats=args.repeats,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "MEASUREMENT_INCOMPLETE", "reason": str(exc)}, sort_keys=True))
        return 2
    print(
        json.dumps({"status": result["status"], "records": len(result["records"])}, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
