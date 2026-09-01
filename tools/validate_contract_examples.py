#!/usr/bin/env python3
"""Validate executable examples for the versioned Research Grade contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _example_for_schema(path: Path, examples_dir: Path) -> Path:
    """Map ``name.schema.json`` to the task's ``name.json`` example path."""

    stem = path.name.removesuffix(".schema.json")
    return examples_dir / f"{stem}.json"


def validate_examples(schema_dir: Path, examples_dir: Path) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema is required to validate Research Grade contract examples"]

    schemas = sorted(schema_dir.glob("*.schema.json"))
    if not schemas:
        return [f"no Research Grade schemas found in {schema_dir}"]
    store: dict[str, Any] = {}
    errors: list[str] = []
    loaded: dict[Path, dict[str, Any]] = {}
    for path in schemas:
        try:
            schema = _load(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: cannot load schema: {exc}")
            continue
        loaded[path] = schema
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{path.relative_to(ROOT)}: wrong JSON Schema dialect")
        if schema.get("x-swos-version") != "2.0.0" or "2.0.0" not in str(schema.get("$id")):
            errors.append(f"{path.relative_to(ROOT)}: missing explicit v2.0.0 identity")
        if isinstance(schema.get("$id"), str):
            store[schema["$id"]] = schema

    for path, schema in loaded.items():
        example = _example_for_schema(path, examples_dir)
        if not example.is_file():
            continue
        try:
            instance = _load(example)
            resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
            validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
            for issue in validator.iter_errors(instance):
                location = "/".join(str(part) for part in issue.path)
                errors.append(f"{example.relative_to(ROOT)}: {location}: {issue.message}")
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            errors.append(f"{example.relative_to(ROOT)}: cannot validate: {exc}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-dir", type=Path, default=ROOT / "schemas" / "research-grade")
    parser.add_argument("--examples-dir", type=Path, default=ROOT / "examples" / "research-grade")
    args = parser.parse_args(argv)
    errors = validate_examples(args.schema_dir, args.examples_dir)
    if errors:
        print("Research Grade contract example validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"OK    Research Grade schemas/examples validated ({args.schema_dir})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
