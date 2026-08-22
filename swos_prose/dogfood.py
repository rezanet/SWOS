"""Local dogfood collection for the SWOS Prose polish pipeline.

Dogfood inputs and outputs may contain unpublished or copyrighted prose. The
repository-level dogfood directories are therefore ignored by default; this
module only writes to paths explicitly supplied by the caller.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .providers.base import SemanticVerifierProvider
from .providers.rewrite_base import RewriteProvider
from .rewrite import PolishResult, polish_text

SUPPORTED_SUFFIXES = {".md", ".txt"}


def load_simple_env_file(path: str | Path) -> list[str]:
    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError(f"Environment file not found: {env_path}")
    if not env_path.is_file():
        raise ValueError(f"Environment path is not a file: {env_path}")
    loaded: list[str] = []
    for line_number, raw_line in enumerate(
        env_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"Malformed environment line {line_number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or not key.replace("_", "a").isalnum() or key[0].isdigit():
            raise ValueError(f"Malformed environment key on line {line_number}: {key!r}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


def _status_for(result: PolishResult) -> str:
    # A successful repair may deliberately restore the exact source wording. It
    # is still a PASS event with repair provenance, not a diagnostics/no-op event.
    if result.repair_success and result.verification_status is not None:
        return result.verification_status
    if result.generation_skipped_by_diagnostics:
        return "NO_CHANGE_RECOMMENDED"
    if result.verification is not None and result.verification.verifier_skip_reason in {
        "source_identical",
        "terminal_newline_only",
    }:
        return "NO_CHANGE_RECOMMENDED"
    if result.verification_status is not None:
        return result.verification_status
    if result.used_source_fallback:
        return "PROVIDER_FAILURE"
    return "NO_CHANGE_RECOMMENDED"


def _record_for(path: Path, root: Path, result: PolishResult) -> dict[str, Any]:
    verification = result.verification
    return {
        "file": path.relative_to(root).as_posix(),
        "mode": "polish",
        "preset": None,
        "assurance": result.assurance,
        "status": _status_for(result),
        "source_text": result.source,
        "candidate_text": result.candidate,
        "final_text": result.final_text,
        "used_fallback": result.used_source_fallback,
        "safe_for_automatic_use": result.safe_for_automatic_use,
        "generation_skipped_by_diagnostics": result.generation_skipped_by_diagnostics,
        "repair_attempts": [attempt.to_dict() for attempt in result.repair_attempts],
        "repair_success": result.repair_success,
        "repair_failure_reason": result.repair_failure_reason,
        "verifier_used": verification.verifier_used if verification is not None else False,
        "verification_skip_reason": (
            verification.verifier_skip_reason
            if verification is not None
            else (
                "diagnostics_no_change"
                if result.generation_skipped_by_diagnostics
                else ("rewrite_provider_failure" if result.used_source_fallback else None)
            )
        ),
        "verifier_notes": list(verification.verifier_notes) if verification is not None else [],
        "semantic_deltas": [delta.to_dict() for delta in verification.semantic_deltas]
        if verification is not None
        else [],
        "diagnostics_before": result.diagnostics_before.to_dict()
        if result.diagnostics_before is not None
        else None,
        "diagnostics_after": None,
        "rewrite_token_usage": result.rewrite_token_usage,
        "verification_token_usage": verification.token_usage if verification is not None else None,
        "notes": result.notes,
        "human_review": {"category": None, "notes": None},
    }


def collect_dogfood(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    rewrite_provider: RewriteProvider,
    verifier_provider: SemanticVerifierProvider | None,
    assurance: str = "strict",
    run_diagnostics: bool = True,
) -> list[dict[str, Any]]:
    source_root, result_root = Path(input_dir), Path(output_dir)
    if not source_root.exists() or not source_root.is_dir():
        raise ValueError(f"Dogfood input directory does not exist: {source_root}")
    files = sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
    )
    if not files:
        raise ValueError(f"Dogfood input directory contains no .md or .txt files: {source_root}")
    result_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for path in files:
        source = path.read_text(encoding="utf-8-sig")
        result = polish_text(
            source=source,
            rewrite_provider=rewrite_provider,
            verifier_provider=verifier_provider,
            assurance=assurance,
            run_diagnostics=run_diagnostics,
        )
        record = _record_for(path, source_root, result)
        relative = path.relative_to(source_root)
        destination = result_root / relative.with_suffix(relative.suffix + ".json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        records.append(record)

    diagnostics_note = (
        "Pre-generation diagnostics were enabled for this run; high-confidence abstentions may skip rewrite and verifier calls."
        if run_diagnostics
        else "Pre-generation diagnostics were disabled for this run so rewrite/verifier coverage is preserved for semantic calibration."
    )
    repair_attempted = [item for item in records if item["repair_attempts"]]
    total_repair_attempts = sum(len(item["repair_attempts"]) for item in records)
    repair_successes = sum(1 for item in repair_attempted if item["repair_success"])
    summary = {
        "mode": "polish",
        "preset": None,
        "assurance": assurance,
        "diagnostics_enabled": run_diagnostics,
        "sample_count": len(records),
        "status_counts": {
            status: sum(1 for item in records if item["status"] == status)
            for status in sorted({item["status"] for item in records})
        },
        "generation_skipped_by_diagnostics": sum(
            1 for item in records if item["generation_skipped_by_diagnostics"]
        ),
        "repair": {
            "cases_attempted": len(repair_attempted),
            "total_attempts": total_repair_attempts,
            "successes": repair_successes,
            "success_rate": repair_successes / len(repair_attempted) if repair_attempted else 0.0,
            "average_attempts_per_repair": total_repair_attempts / len(repair_attempted)
            if repair_attempted
            else 0.0,
        },
        "files": [item["file"] for item in records],
        "note": f"{diagnostics_note} Presets are not implemented yet.",
    }
    (result_root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return records
