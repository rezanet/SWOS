#!/usr/bin/env python3
"""Measure T095 corpora with fail-closed CPU/memory/wall-clock records.

PREPARATION ONLY / NOT RELEASE EVIDENCE.

The harness is intentionally Linux-oriented because the frozen hosted
certification workflow runs on Ubuntu. It wraps each supplied benchmark command
with GNU `/usr/bin/time`, records wall/user/system CPU and peak resident set size,
enforces the frozen wall-clock timeout, and writes raw per-run records. It does
not invent a memory threshold that the frozen contract does not define.

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
import shlex
import signal
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TIME_BIN = Path("/usr/bin/time")
FORMAT = "SWOS_TIME wall=%e user=%U sys=%S maxrss_kb=%M exit=%x"


def utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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
        "started_at": datetime.fromtimestamp(started, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
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
    timeout_seconds = float(limits["limits"]["timeout_seconds"])
    p95_target = float(limits["release_performance_targets"]["p95_seconds"])
    records = []
    for corpus in corpus_payload.get("corpora", []):
        corpus_path = corpus_manifest.parent / corpus["path"]
        if not corpus_path.is_file():
            raise FileNotFoundError(corpus_path)
        actual_sha = sha256(corpus_path)
        if actual_sha != corpus.get("sha256"):
            raise ValueError(f"corpus checksum mismatch: {corpus_path}")
        if corpus_path.stat().st_size > int(limits["limits"]["max_bytes"]):
            records.append({
                "corpus": corpus["name"],
                "corpus_sha256": actual_sha,
                "status": "FAIL_CLOSED_MAX_BYTES",
                "runs": [],
            })
            continue
        command = render_command(command_template, corpus_path)
        runs = [run_once(command, timeout_seconds=timeout_seconds) for _ in range(repeats)]
        measured = [r["measurement"] for r in runs if r["status"] == "MEASURED"]
        walls = [float(m["wall_seconds"]) for m in measured if m]
        cpus = [float(m["total_cpu_seconds"]) for m in measured if m]
        rss = [int(m["max_rss_kb"]) for m in measured if m]
        all_measured = len(measured) == repeats
        p95 = percentile95(walls) if all_measured else None
        performance_status = (
            "MEASURED_WITHIN_FROZEN_WALL_TARGET"
            if all_measured and p95 is not None and p95 <= p95_target
            else "FAIL_CLOSED_INCOMPLETE_OR_WALL_TARGET_EXCEEDED"
        )
        records.append({
            "corpus": corpus["name"],
            "corpus_sha256": actual_sha,
            "format": corpus.get("format"),
            "statement_count": corpus.get("statement_count"),
            "blank_node_count": corpus.get("blank_node_count"),
            "runs": runs,
            "aggregate": {
                "completed_runs": len(measured),
                "requested_runs": repeats,
                "wall_seconds_p95": p95,
                "wall_seconds_median": statistics.median(walls) if walls else None,
                "cpu_seconds_median": statistics.median(cpus) if cpus else None,
                "max_rss_kb_peak_observed": max(rss) if rss else None,
                "memory_gate": "RECORDED_ONLY_NO_FROZEN_NUMERIC_MEMORY_THRESHOLD",
                "wall_target_seconds": p95_target,
                "status": performance_status,
            },
        })
    payload = {
        "schema_version": "research-handoff.t095.measurements.v1",
        "status": "MEASUREMENTS_RECORDED_NOT_RELEASE_APPROVED",
        "generated_at": utc(),
        "corpus_manifest_sha256": sha256(corpus_manifest),
        "resource_limits_sha256": sha256(resource_limits),
        "command_template": command_template,
        "command_template_sha256": hashlib.sha256(json.dumps(command_template, separators=(",", ":")).encode()).hexdigest(),
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
    print(json.dumps({"status": result["status"], "records": len(result["records"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
