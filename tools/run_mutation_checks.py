#!/usr/bin/env python3
"""Run bounded safety mutations against the frozen Research Grade guards."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class MutantSpec:
    mutant_id: str
    target: str
    description: str
    needle: str
    replacement: str
    probe: str


MUTANTS = (
    MutantSpec(
        mutant_id="rpm-provenance-evidence-or",
        target="swos_runtime/research_memory.py",
        description="Allow a durable candidate without complete source evidence.",
        needle=(
            "                if (\n"
            "                    not candidate.source_grounded\n"
            "                    or not candidate.epg_node_ids\n"
            "                    or not candidate.sdl_decision_id\n"
            "                ):"
        ),
        replacement="                if not candidate.source_grounded:",
        probe="tests.runtime.test_research_memory_writes",
    ),
    MutantSpec(
        mutant_id="rpm-approval-digest-binding",
        target="swos_runtime/research_memory.py",
        description="Accept an approval that is not bound to the assessed operation.",
        needle="        if approval.assessment_digest != assessment.digest:",
        replacement="        if False:",
        probe="tests.runtime.test_research_memory_writes",
    ),
    MutantSpec(
        mutant_id="rpm-commit-head-revalidation",
        target="swos_runtime/research_memory.py",
        description="Commit an assessment after the target chain head changed.",
        needle="        if current_head != assessment.target_head:",
        replacement="        if False:",
        probe="tests.runtime.test_research_memory_writes",
    ),
    MutantSpec(
        mutant_id="store-event-hash-verification",
        target="swos_runtime/programme_store.py",
        description="Ignore event-hash corruption during append-only store verification.",
        needle="            if actual_hash != canonical_digest(body):",
        replacement="            if False:",
        probe="tests.runtime.test_programme_store",
    ),
    MutantSpec(
        mutant_id="exchange-zip-member-safety",
        target="swos_runtime/rpm_exchange.py",
        description="Accept a non-canonical or traversal-bearing bundle member path.",
        needle='    if path.is_absolute() or ".." in path.parts or name.startswith("/"):',
        replacement="    if False:",
        probe="tests.runtime.test_rpm_exchange",
    ),
    MutantSpec(
        mutant_id="rpm-human-approval-gate",
        target="swos_runtime/governance.py",
        description="Permit a durable RPM write without a human approver.",
        needle="    return bool(source_grounded and epg_refs and sdl_id and human_approver)",
        replacement="    return True",
        probe="tests.runtime.test_runtime",
    ),
)

COPY_ROOTS = ("swos_runtime", "swos_prose", "evals", "tests", "schemas", "contracts")
SAFE_ENVIRONMENT_KEYS = frozenset(
    {
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "TZ",
        "WINDIR",
    }
)
DEFAULT_MAX_PROBE_OUTPUT_BYTES = 64 * 1024


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _output_metadata(value: str | bytes | None) -> tuple[int, str]:
    if value is None:
        raw = b""
    elif isinstance(value, bytes):
        raw = value
    else:
        raw = value.encode()
    return len(raw), _sha256(raw)


def _source_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _source_worktree_clean() -> bool | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.returncode == 0 and not result.stdout.strip()


def _prepare_sandbox(destination: Path, mutant: MutantSpec | None = None) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.py[cod]")
    for directory in COPY_ROOTS:
        shutil.copytree(ROOT / directory, destination / directory, ignore=ignore)
    if mutant is None:
        return
    target = destination / mutant.target
    source = target.read_text(encoding="utf-8")
    if source.count(mutant.needle) != 1:
        raise ValueError(f"mutation needle is not unique: {mutant.mutant_id}")
    target.write_text(source.replace(mutant.needle, mutant.replacement, 1), encoding="utf-8")


def _subprocess_environment(sandbox: Path) -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if key.upper() in SAFE_ENVIRONMENT_KEYS
    }
    environment["PYTHONHASHSEED"] = "0"
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONPATH"] = str(sandbox)
    return environment


def _capture_stream(
    stream: Any, maximum: int, buffer: bytearray, state: list[bool], index: int
) -> None:
    while True:
        chunk = stream.read(8192)
        if not chunk:
            return
        remaining = maximum - len(buffer)
        if remaining > 0:
            buffer.extend(chunk[:remaining])
        if len(chunk) > remaining:
            state[index] = True


def _run_probe(
    sandbox: Path,
    probe: str,
    timeout_seconds: float,
    max_output_bytes: int = DEFAULT_MAX_PROBE_OUTPUT_BYTES,
) -> dict[str, Any]:
    if max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be positive")
    command = [sys.executable, "-m", "unittest", "-q", probe]
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=sandbox,
        env=_subprocess_environment(sandbox),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    output_limit_state = [False, False]
    output_limit = max_output_bytes
    stdout_thread = Thread(
        target=_capture_stream,
        args=(process.stdout, output_limit, stdout_buffer, output_limit_state, 0),
        daemon=True,
    )
    stderr_thread = Thread(
        target=_capture_stream,
        args=(process.stderr, output_limit, stderr_buffer, output_limit_state, 1),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        returncode = process.wait()
    stdout_thread.join()
    stderr_thread.join()
    process.stdout.close()
    process.stderr.close()
    stdout = bytes(stdout_buffer)
    stderr = bytes(stderr_buffer)
    output_limit_exceeded = any(output_limit_state)
    output = (stdout + stderr).decode("utf-8", errors="replace")
    has_unittest_failure = any(
        marker in output for marker in ("FAILED", "FAIL:", "ERROR:", "AssertionError")
    )
    if timed_out or output_limit_exceeded:
        status = "error"
    elif returncode == 0:
        status = "passed"
    elif has_unittest_failure:
        status = "failed"
    else:
        status = "error"
    stdout_bytes, stdout_sha256 = _output_metadata(stdout)
    stderr_bytes, stderr_sha256 = _output_metadata(stderr)
    return {
        "status": status,
        "returncode": returncode,
        "timed_out": timed_out,
        "output_limit_exceeded": output_limit_exceeded,
        "output_limit_bytes": output_limit,
        "duration_seconds": round(time.perf_counter() - started, 6),
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "stdout_sha256": stdout_sha256,
        "stderr_sha256": stderr_sha256,
    }


def _run_mutations(
    timeout_seconds: float, max_output_bytes: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline: dict[str, dict[str, Any]] = {}
    mutants: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="swos-mutation-") as temporary:
        temporary_root = Path(temporary)
        for probe in sorted({spec.probe for spec in MUTANTS}):
            sandbox = temporary_root / "baseline" / probe.replace(".", "-")
            sandbox.mkdir(parents=True)
            _prepare_sandbox(sandbox)
            baseline[probe] = _run_probe(sandbox, probe, timeout_seconds, max_output_bytes)
        for index, spec in enumerate(MUTANTS):
            result: dict[str, Any] = {
                "mutant_id": spec.mutant_id,
                "target": spec.target,
                "description": spec.description,
                "probe": spec.probe,
                "status": "error",
            }
            if baseline[spec.probe]["status"] != "passed":
                result["reason"] = "baseline probe did not pass"
                result["probe_result"] = baseline[spec.probe]
                mutants.append(result)
                continue
            sandbox = temporary_root / "mutants" / f"{index:02d}-{spec.mutant_id}"
            sandbox.mkdir(parents=True)
            try:
                _prepare_sandbox(sandbox, spec)
                probe_result = _run_probe(sandbox, spec.probe, timeout_seconds, max_output_bytes)
                if probe_result["status"] == "failed":
                    result["status"] = "killed"
                elif probe_result["status"] == "passed":
                    result["status"] = "survived"
                else:
                    result["status"] = "error"
                result["probe_result"] = probe_result
            except (OSError, UnicodeError, ValueError) as exc:
                result["reason"] = str(exc)
            mutants.append(result)
    return [
        {"probe": probe, "result": result} for probe, result in sorted(baseline.items())
    ], mutants


def run_mutation_checks(
    *,
    timeout_seconds: float = 60.0,
    max_output_bytes: int = DEFAULT_MAX_PROBE_OUTPUT_BYTES,
    expected_source_sha: str | None = None,
) -> dict[str, Any]:
    if not 1 <= timeout_seconds <= 300:
        raise ValueError("timeout_seconds must be between 1 and 300")
    if max_output_bytes <= 0:
        raise ValueError("max_output_bytes must be positive")
    source_sha = _source_sha()
    expected_source_sha = expected_source_sha or os.environ.get("SWOS_EXPECTED_SOURCE_SHA")
    if expected_source_sha is None:
        expected_source_sha = source_sha
    source_sha_matches_expected = bool(source_sha and source_sha == expected_source_sha)
    source_worktree_clean = _source_worktree_clean()
    baseline, mutants = _run_mutations(timeout_seconds, max_output_bytes)
    killed = [item for item in mutants if item["status"] == "killed"]
    surviving = [item["mutant_id"] for item in mutants if item["status"] == "survived"]
    errors = [item["mutant_id"] for item in mutants if item["status"] == "error"]
    return {
        "schema_version": "2.0.0",
        "harness_version": "1.0.0",
        "status": (
            "passed"
            if (
                len(killed) == len(MUTANTS)
                and source_sha_matches_expected
                and source_worktree_clean is True
            )
            else "failed"
        ),
        "source_sha": source_sha,
        "expected_source_sha": expected_source_sha,
        "source_sha_matches_expected": source_sha_matches_expected,
        "source_worktree_clean": source_worktree_clean,
        "mutant_count": len(MUTANTS),
        "killed_count": len(killed),
        "surviving_mutants": surviving,
        "error_mutants": errors,
        "baseline": baseline,
        "mutants": mutants,
        "thresholds": {"surviving_mutants": 0, "error_mutants": 0},
        "environment": {
            "python": platform.python_version(),
            "os": platform.platform(),
            "timeout_seconds": timeout_seconds,
            "max_probe_output_bytes": max_output_bytes,
        },
        "limitations": [
            "Bounded deterministic guard mutations only; this is not exhaustive mutation coverage.",
            "Focused probes run against temporary package copies and never mutate the checkout.",
        ],
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "artifacts/research-grade/mutation-report.json",
    )
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_PROBE_OUTPUT_BYTES)
    parser.add_argument("--expected-source-sha")
    args = parser.parse_args(argv)
    try:
        report = run_mutation_checks(
            timeout_seconds=args.timeout_seconds,
            max_output_bytes=args.max_output_bytes,
            expected_source_sha=args.expected_source_sha,
        )
        _write_report(args.report, report)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
