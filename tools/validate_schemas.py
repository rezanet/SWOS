#!/usr/bin/env python3
"""Validate every SWOS artefact against the frozen JSON Schemas.

Usage:  python3 tools/validate_schemas.py [--strict]

Exit codes: 0 ok, 1 validation failure, 2 harness error.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"

REQUIRED_SCHEMAS = [
    "common/common.schema.json",
    "evidence-matrix/evidence-matrix.schema.json",
    "argument-graph/argument-graph.schema.json",
    "provenance-graph/epg.schema.json",
    "decision-ledger/sdl.schema.json",
    "memory/rpm.schema.json",
    "reviewer/reviewer-finding.schema.json",
    "evaluation/evaluation-result.schema.json",
    "governance/governance-gate.schema.json",
    "state/scholarly-state.schema.json",
]

# Artefact filename patterns mapped to their governing schema.
ARTEFACT_MAP = {
    "evidence-matrix": "evidence-matrix/evidence-matrix.schema.json",
    "argument-graph": "argument-graph/argument-graph.schema.json",
    "epg": "provenance-graph/epg.schema.json",
    "provenance-bundle": "provenance-graph/epg.schema.json",
    "sdl": "decision-ledger/sdl.schema.json",
    "decision-ledger": "decision-ledger/sdl.schema.json",
    "rpm": "memory/rpm.schema.json",
    "reviewer-finding": "reviewer/reviewer-finding.schema.json",
    "evaluation-result": "evaluation/evaluation-result.schema.json",
    "governance-gate": "governance/governance-gate.schema.json",
    "scholarly-state": "state/scholarly-state.schema.json",
}


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    strict = "--strict" in sys.argv
    errors = []
    checked = 0

    # 1. Every required schema exists and is parseable.
    for rel in REQUIRED_SCHEMAS:
        path = SCHEMA_DIR / rel
        if not path.exists():
            errors.append(f"MISSING SCHEMA: {rel}")
            continue
        try:
            schema = load_json(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"UNPARSEABLE SCHEMA {rel}: {exc}")
            continue
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{rel}: must declare JSON Schema draft 2020-12")
        if "$id" not in schema:
            errors.append(f"{rel}: missing $id")
        if "title" not in schema:
            errors.append(f"{rel}: missing title")
        checked += 1

    # 2. Every JSON artefact in the repo parses.
    for path in ROOT.rglob("*.json"):
        try:
            load_json(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"UNPARSEABLE: {path.relative_to(ROOT)}: {exc}")

    # 3. Governance policies are well formed.
    for path in (ROOT / "governance" / "policies").glob("*.policy.json"):
        pol = load_json(path)
        for field in (
            "policy_id",
            "version",
            "gate_type",
            "trigger",
            "rules",
            "default_effect",
            "nist_ai_rmf",
        ):
            if field not in pol:
                errors.append(f"{path.name}: missing required policy field '{field}'")
        if pol.get("default_effect") not in ("deny", "escalate"):
            errors.append(
                f"{path.name}: default_effect is '{pol.get('default_effect')}'. "
                "A control that fails open is not a control."
            )
        checked += 1

    # 4. Adapter capability matrices declare what they cannot do.
    for path in (ROOT / "adapters").rglob("capability-matrix.json"):
        cap = load_json(path)
        for field in (
            "adapter",
            "swos_version",
            "capabilities",
            "unsupported",
            "work_classes_permitted",
        ):
            if field not in cap:
                errors.append(f"{path.parent.name}: capability matrix missing '{field}'")
        unsupported = set(cap.get("unsupported", []))
        if "provenance_store" in unsupported and "release" not in unsupported:
            errors.append(
                f"{path.parent.name}: declares provenance_store unsupported but "
                "does not exclude release. No audit pack is possible without provenance."
            )
        checked += 1

    # 5. Validate example artefacts where jsonschema is available.
    try:
        import jsonschema  # type: ignore
    except ImportError:
        if strict:
            errors.append("jsonschema not installed; --strict requires it")
        else:
            print("note: jsonschema not installed, skipping instance validation")
        jsonschema = None  # type: ignore

    if jsonschema is not None:
        store = {}
        for rel in REQUIRED_SCHEMAS:
            s = load_json(SCHEMA_DIR / rel)
            store[s["$id"]] = s
        for path in (ROOT / "examples").rglob("*.json"):
            stem = path.stem
            schema_rel = next((v for k, v in ARTEFACT_MAP.items() if stem.startswith(k)), None)
            if not schema_rel:
                continue
            schema = load_json(SCHEMA_DIR / schema_rel)
            instance = load_json(path)
            resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
            validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
            instances = (
                instance
                if stem == "governance-gates" and isinstance(instance, list)
                else [instance]
            )
            for index, item in enumerate(instances):
                for err in validator.iter_errors(item):
                    prefix = f"{index}/" if len(instances) > 1 else ""
                    errors.append(
                        f"{path.relative_to(ROOT)}: {prefix}{'/'.join(str(p) for p in err.path)}: {err.message}"
                    )
            checked += 1

    if errors:
        print(f"FAIL  {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK    {checked} artefact(s) validated. Contracts frozen at v1.0.0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
