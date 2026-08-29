"""Validate the SWOS documentation authority manifest.

The JSON Schema checks shape and value enums. This module adds repository-level
checks for corpus coverage, safe paths, reciprocal supersession and canonical
authority uniqueness.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

AUTHORITY_VALUES = {
    "constitutional",
    "normative",
    "governance",
    "operational",
    "informative",
    "historical",
}
STATUS_VALUES = {"draft", "active", "superseded", "deprecated", "historical"}
VERSION_SCHEMES = {"semver", "date", "living"}
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class ManifestValidationError(ValueError):
    """Raised when the manifest cannot be loaded or its schema is invalid."""


def _normalise_relative_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def _is_excluded(path: str, prefixes: list[str]) -> bool:
    return any(
        path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
        for prefix in prefixes
    )


def discover_corpus(repo_root: Path, corpus: dict[str, Any]) -> set[str]:
    """Return the normalized document paths required by the manifest policy."""

    discovered: set[str] = set()
    for configured_root in corpus.get("include_roots", []):
        root_name = _normalise_relative_path(str(configured_root))
        root = repo_root if root_name == "." else repo_root / root_name
        if not root.is_dir():
            continue
        iterator = root.glob("*.md") if root == repo_root else root.rglob("*.md")
        for path in iterator:
            if path.is_file():
                discovered.add(path.relative_to(repo_root).as_posix())

    for configured_file in corpus.get("include_files", []):
        path = _normalise_relative_path(str(configured_file))
        if (repo_root / path).is_file():
            discovered.add(path)

    prefixes = [
        _normalise_relative_path(str(prefix)) for prefix in corpus.get("exclude_prefixes", [])
    ]
    return {path for path in discovered if not _is_excluded(path, prefixes)}


def _schema_errors(manifest: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - project dependency is installed in normal runs
        return [f"schema validation failed: jsonschema is unavailable ({exc})"]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker()
        )
        return [
            f"schema validation failed: {error.message} at {list(error.path)}"
            for error in validator.iter_errors(manifest)
        ]
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        return [f"schema validation failed: unable to load or compile schema ({exc})"]


def _path_errors(documents: list[dict[str, Any]], repo_root: Path) -> list[str]:
    errors: list[str] = []
    ids: dict[str, int] = {}
    paths: dict[str, int] = {}
    for index, document in enumerate(documents):
        document_id = document.get("id")
        if isinstance(document_id, str):
            if document_id in ids:
                errors.append(f"duplicate document id: {document_id}")
            ids[document_id] = index

        raw_path = document.get("path")
        if not isinstance(raw_path, str):
            continue
        path = _normalise_relative_path(raw_path)
        if path in paths:
            errors.append(f"duplicate document path: {path}")
        paths[path] = index
        candidate = (repo_root / path).resolve()
        try:
            candidate.relative_to(repo_root.resolve())
        except ValueError:
            errors.append(f"document path escapes repository: {raw_path}")
            continue
        if not candidate.is_file():
            errors.append(f"document path does not exist: {path}")
    return errors


def _metadata_errors(documents: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for document in documents:
        document_id = document.get("id", "<missing-id>")
        authority = document.get("authority")
        status = document.get("status")
        scheme = document.get("version_scheme")
        version = document.get("version")
        if authority not in AUTHORITY_VALUES:
            errors.append(f"invalid authority for {document_id}: {authority!r}")
        if status not in STATUS_VALUES:
            errors.append(f"invalid status for {document_id}: {status!r}")
        if scheme not in VERSION_SCHEMES:
            errors.append(f"invalid version scheme for {document_id}: {scheme!r}")
        elif not isinstance(version, str) or (
            (scheme == "semver" and not SEMVER_PATTERN.fullmatch(version))
            or (scheme == "date" and not DATE_PATTERN.fullmatch(version))
            or (scheme == "living" and version != "current")
        ):
            errors.append(f"version does not match scheme for {document_id}: {scheme}/{version}")
    return errors


def _relationship_errors(documents: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    by_id = {
        document.get("id"): document
        for document in documents
        if isinstance(document.get("id"), str)
    }
    superseded_ids = {
        target_id for document in documents for target_id in document.get("supersedes", [])
    }
    for document in documents:
        document_id = document.get("id", "<missing-id>")
        supersedes = document.get("supersedes", [])
        superseded_by = document.get("superseded_by", [])
        if document.get("status") == "active" and (superseded_by or document_id in superseded_ids):
            errors.append(f"active document is superseded: {document_id}")
        for target_id in supersedes:
            target = by_id.get(target_id)
            if target is None:
                errors.append(
                    f"supersession target does not exist: {document_id} supersedes {target_id}"
                )
            elif document_id not in target.get("superseded_by", []):
                errors.append(f"non-reciprocal supersession: {document_id} supersedes {target_id}")
        for target_id in superseded_by:
            target = by_id.get(target_id)
            if target is None:
                errors.append(
                    f"superseding document does not exist: {target_id} supersedes {document_id}"
                )
            elif document_id not in target.get("supersedes", []):
                errors.append(f"non-reciprocal supersession: {target_id} supersedes {document_id}")
    return errors


def _canonical_errors(documents: list[dict[str, Any]]) -> list[str]:
    owners: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        for domain in document.get("canonical_for", []):
            owners[domain].append(str(document.get("id", "<missing-id>")))
    return [
        f"multiple canonical documents for authority domain {domain}: {', '.join(sorted(ids))}"
        for domain, ids in sorted(owners.items())
        if len(ids) > 1
    ]


def _source_input_errors(manifest: dict[str, Any], documents: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids = {document.get("id") for document in documents}
    filenames: set[str] = set()
    for source in manifest.get("source_inputs", []):
        filename = source.get("filename")
        if filename in filenames:
            errors.append(f"duplicate source input filename: {filename}")
        filenames.add(filename)
        digest = source.get("sha256")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            errors.append(f"invalid source input SHA-256 for {filename}")
        for document_id in source.get("derived_canonical_documents", []):
            if document_id not in ids:
                errors.append(f"source input references unknown derived document: {document_id}")
    return errors


def validate_manifest_data(
    manifest: dict[str, Any],
    repo_root: Path,
    schema_path: Path | None = None,
) -> list[str]:
    """Return deterministic validation errors for an in-memory manifest."""

    if schema_path is None:
        schema_path = repo_root / "schemas" / "document-manifest" / "document-manifest.schema.json"
    if not isinstance(manifest, dict):
        return ["schema validation failed: manifest root must be an object"]

    errors = _schema_errors(manifest, schema_path)
    documents = manifest.get("documents", [])
    if not isinstance(documents, list):
        return errors

    errors.extend(_path_errors(documents, repo_root))
    errors.extend(_metadata_errors(documents))
    errors.extend(_relationship_errors(documents))
    errors.extend(_canonical_errors(documents))
    errors.extend(_source_input_errors(manifest, documents))

    expected = discover_corpus(repo_root, manifest.get("corpus", {}))
    listed = {
        _normalise_relative_path(document.get("path"))
        for document in documents
        if isinstance(document, dict) and isinstance(document.get("path"), str)
    }
    for path in sorted(expected - listed):
        errors.append(f"missing corpus entry: {path}")
    for path in sorted(listed - expected):
        errors.append(f"document outside declared corpus: {path}")
    return sorted(set(errors))


def validate_manifest_file(
    manifest_path: Path, repo_root: Path, schema_path: Path | None = None
) -> list[str]:
    """Load and validate a manifest file."""

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"unable to load manifest: {exc}"]
    return validate_manifest_data(manifest, repo_root, schema_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("docs/document-manifest.json"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Path to the JSON Schema; defaults to schemas/document-manifest/document-manifest.schema.json",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else repo_root / args.manifest
    schema_path = args.schema
    if schema_path is not None and not schema_path.is_absolute():
        schema_path = repo_root / schema_path
    errors = validate_manifest_file(manifest_path, repo_root, schema_path)
    if errors:
        print("Document manifest validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = discover_corpus(repo_root, manifest["corpus"])
    print(
        f"Document manifest valid: {len(expected)} corpus documents; {len(manifest['source_inputs'])} research inputs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
