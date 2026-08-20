"""Local dogfood collection for the first SWOS Prose polish pipeline.

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
    """Load a deliberately small KEY=VALUE environment file.

    This is not a full dotenv parser. It supports comments, optional ``export ``
    prefixes, and simple single- or double-quoted values. Existing process
    environment variables always win, so a local file cannot silently override
    credentials/configuration already supplied by the shell.
    """
    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError(f"Environment file not found: {env_path}")
    if not env_path.is_file():
        raise ValueError(f"Environment path is not a file: {env_path}")

    loaded: list[str] = []
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"Malformed environment line {line_number}: expected KEY=VALUE")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "a").isalnum() or key[0].isdigit():
            raise ValueError(f"Malformed environment key on line {line_number}: {key!r}")

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


def _status_for(result: PolishResult) -> str:
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
        "verifier_used": verification.verifier_used if verification is not None else False,
        "verification_skip_reason": (
            verification.verifier_skip_reason
            if verification is not None
            else ("rewrite_provider_failure" if result.used_source_fallback else None)
        ),
        "verifier_notes": (
            list(verification.verifier_notes)
            if verification is not None
            else []
        ),
        "semantic_deltas": (
            [delta.to_dict() for delta in verification.semantic_deltas]
            if verification is not None
            else []
        ),
        "diagnostics_before": None,
        "diagnostics_after": None,
        "rewrite_token_usage": result.rewrite_token_usage,
        "verification_token_usage": verification.token_usage if verification is not None else None,
        "notes": result.notes,
        "human_review": {
            "category": None,
            "notes": None,
        },
    }


def collect_dogfood(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    rewrite_provider: RewriteProvider,
    verifier_provider: SemanticVerifierProvider | None,
    assurance: str = "strict",
) -> list[dict[str, Any]]:
    """Run polish over local .md/.txt samples and persist one JSON result each."""
    source_root = Path(input_dir)
    result_root = Path(output_dir)
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
        )
        record = _record_for(path, source_root, result)
        relative = path.relative_to(source_root)
        destination = result_root / relative.with_suffix(relative.suffix + ".json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        records.append(record)

    summary = {
        "mode": "polish",
        "preset": None,
        "assurance": assurance,
        "sample_count": len(records),
        "status_counts": {
            status: sum(1 for item in records if item["status"] == status)
            for status in sorted({item["status"] for item in records})
        },
        "files": [item["file"] for item in records],
        "note": "Prose diagnostics and presets are not implemented yet; null fields are intentional.",
    }
    (result_root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return records
