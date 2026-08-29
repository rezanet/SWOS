"""Provider-neutral validation of frozen SWOS v1.0 run artefacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_MAPPINGS = {
    "evidence-matrix.json": "evidence-matrix/evidence-matrix.schema.json",
    "argument-graph.json": "argument-graph/argument-graph.schema.json",
    "provenance.json": "provenance-graph/epg.schema.json",
    "decision-ledger.json": "decision-ledger/sdl.schema.json",
    "rpm.json": "memory/rpm.schema.json",
    "scholarly-state.json": "state/scholarly-state.schema.json",
}


def validate_frozen_run_schemas(output_dir: str | Path) -> list[str]:
    """Return schema errors for one SWOS output bundle; empty means valid."""

    try:
        import jsonschema
    except ImportError:
        return ["jsonschema unavailable; frozen artefact contracts could not be validated"]

    output = Path(output_dir)
    root = Path(__file__).resolve().parents[1]
    schema_dir = root / "schemas"
    required_schemas = list(SCHEMA_MAPPINGS.values()) + [
        "common/common.schema.json",
        "reviewer/reviewer-finding.schema.json",
    ]
    store: dict[str, Any] = {}
    for rel in required_schemas:
        schema = json.loads((schema_dir / rel).read_text(encoding="utf-8"))
        store[schema["$id"]] = schema

    errors: list[str] = []
    for filename, rel in SCHEMA_MAPPINGS.items():
        path = output / filename
        if not path.is_file():
            errors.append(f"{filename}: required artefact is missing")
            continue
        schema = json.loads((schema_dir / rel).read_text(encoding="utf-8"))
        instance = json.loads(path.read_text(encoding="utf-8"))
        resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
        validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
        errors.extend(
            f"{filename}: {'/'.join(str(part) for part in err.path)}: {err.message}"
            for err in validator.iter_errors(instance)
        )

    reviewer_schema = json.loads(
        (schema_dir / "reviewer/reviewer-finding.schema.json").read_text(encoding="utf-8")
    )
    resolver = jsonschema.RefResolver(
        base_uri=reviewer_schema["$id"], referrer=reviewer_schema, store=store
    )
    reviewer_validator = jsonschema.Draft202012Validator(reviewer_schema, resolver=resolver)
    review_dir = output / "review-findings"
    if review_dir.is_dir():
        for path in sorted(review_dir.glob("*.json")):
            instance = json.loads(path.read_text(encoding="utf-8"))
            errors.extend(
                f"{path.name}: {'/'.join(str(part) for part in err.path)}: {err.message}"
                for err in reviewer_validator.iter_errors(instance)
            )
    return errors
