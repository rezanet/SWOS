#!/usr/bin/env python3
"""Assemble and strictly verify an exact-head Research Grade audit pack.

The pack is deliberately a small, content-addressed directory.  Verification
does not trust a manifest's claims about files: it enumerates the directory,
rejects missing and extra entries, and re-hashes every recorded byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST_NAME = "audit-pack.json"
MANIFEST_VERSION = "2.0.0"


class AuditPackError(ValueError):
    """Raised when a pack cannot be assembled or verified fail-closed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_files(root: Path) -> list[Path]:
    if not root.is_dir():
        raise AuditPackError(f"audit-pack directory does not exist: {root}")
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise AuditPackError(f"symlink is not permitted in audit pack: {path}")
        if path.is_file():
            relative = path.relative_to(root)
            if relative.as_posix() == MANIFEST_NAME:
                continue
            files.append(relative)
    return sorted(files, key=lambda item: item.as_posix())


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def assemble_audit_pack(
    source_dir: str | Path,
    output_dir: str | Path,
    *,
    code_sha: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Copy source artifacts and write a manifest bound to ``code_sha``."""

    source = Path(source_dir)
    output = Path(output_dir)
    if not code_sha or any(character.isspace() for character in code_sha):
        raise AuditPackError("code_sha is required")
    if output.exists() and any(output.iterdir()):
        raise AuditPackError(f"output directory is not empty: {output}")
    files = _relative_files(source)
    output.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for relative in files:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
        entries.append(
            {
                "path": relative.as_posix(),
                "bytes": target.stat().st_size,
                "sha256": _sha256(target),
            }
        )
    manifest: dict[str, Any] = {
        "artifact": "swos.research-grade.audit-pack",
        "schema_version": MANIFEST_VERSION,
        "code_sha": code_sha,
        "artifact_count": len(entries),
        "artifacts": entries,
    }
    if metadata:
        manifest["metadata"] = metadata
    (output / MANIFEST_NAME).write_text(
        _canonical_json(manifest) + "\n", encoding="utf-8"
    )
    return manifest


def verify_audit_pack(
    pack_dir: str | Path,
    *,
    expected_code_sha: str | None = None,
) -> dict[str, Any]:
    """Verify manifest, exact file set, byte sizes, and content digests."""

    pack = Path(pack_dir)
    manifest_path = pack / MANIFEST_NAME
    if not manifest_path.is_file():
        raise AuditPackError("missing audit-pack manifest")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditPackError("malformed audit-pack manifest") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != MANIFEST_VERSION:
        raise AuditPackError("unsupported audit-pack manifest version")
    recorded_head = manifest.get("code_sha")
    if not isinstance(recorded_head, str) or not recorded_head:
        raise AuditPackError("audit-pack manifest has no code head")
    if expected_code_sha is not None and recorded_head != expected_code_sha:
        raise AuditPackError(
            f"audit-pack head mismatch: {recorded_head} != {expected_code_sha}"
        )
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise AuditPackError("audit-pack artifacts must be a list")
    expected: dict[str, dict[str, Any]] = {}
    for entry in artifacts:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise AuditPackError("malformed audit-pack artifact entry")
        path = Path(entry["path"])
        normalized = path.as_posix()
        if path.is_absolute() or normalized != entry["path"] or ".." in path.parts:
            raise AuditPackError(f"unsafe audit-pack artifact path: {entry['path']}")
        if normalized in expected:
            raise AuditPackError(f"duplicate audit-pack artifact: {normalized}")
        expected[normalized] = entry

    actual = {path.as_posix() for path in _relative_files(pack)}
    expected_names = set(expected)
    missing = sorted(expected_names - actual)
    extra = sorted(actual - expected_names)
    if missing:
        raise AuditPackError("missing audit-pack artifacts: " + ", ".join(missing))
    if extra:
        raise AuditPackError("extra audit-pack artifacts: " + ", ".join(extra))
    for name in sorted(expected):
        path = pack / Path(name)
        entry = expected[name]
        actual_size = path.stat().st_size
        actual_digest = _sha256(path)
        if actual_size != entry.get("bytes") or actual_digest != entry.get("sha256"):
            raise AuditPackError(f"artifact digest or size mismatch: {name}")
    if manifest.get("artifact_count") != len(expected):
        raise AuditPackError("audit-pack artifact count mismatch")
    return {
        "status": "pass",
        "code_sha": recorded_head,
        "artifact_count": len(expected),
        "manifest_sha256": _sha256(manifest_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", help="source artifact directory")
    parser.add_argument("output", nargs="?", help="output audit-pack directory")
    parser.add_argument("--code-sha", default=None)
    parser.add_argument("--verify", default=None, metavar="PACK")
    parser.add_argument("--expected-code-sha", default=None)
    args = parser.parse_args(argv)
    try:
        if args.verify:
            result = verify_audit_pack(args.verify, expected_code_sha=args.expected_code_sha)
        elif args.source and args.output and args.code_sha:
            result = assemble_audit_pack(args.source, args.output, code_sha=args.code_sha)
        else:
            parser.error("provide SOURCE OUTPUT --code-sha, or --verify PACK")
            return 2
    except AuditPackError as exc:
        print(f"error: {exc}")
        return 1
    print(_canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
