#!/usr/bin/env python3
"""Generate deterministic T095 provenance performance/resource corpora.

RESEARCH/PREPARATION ONLY. This generator does not produce benchmark PASS
measurements and its outputs are not release evidence until the frozen T095
workflow executes them at an exact candidate head and records CPU/memory/time
measurements under the approved resource contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PROV_NAMESPACE = "http://www.w3.org/ns/prov#"
EX_NAMESPACE = "https://example.org/swos/provbench/"
GENERATOR_VERSION = "1.0.0"
PROFILE_ID = "swos.prov-dm-round-trip.v2"
GENERATOR_SEED = 0
DEFAULT_RESOURCE_LIMITS = (
    Path(__file__).resolve().parents[2] / "benchmark" / "provenance" / "resource-limits.json"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _positive_number(value: Any, name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return value


def load_resource_limits(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("limits"), dict):
        raise ValueError("resource limits must contain a limits object")
    limits = payload["limits"]
    for name in (
        "max_bytes",
        "max_statements",
        "max_literal_length",
        "max_depth",
        "timeout_seconds",
        "cpu_seconds",
        "max_rss_kb",
    ):
        _positive_number(limits.get(name), f"limits.{name}")
    return payload


def generator_identity(resource_limits: Path) -> dict[str, Any]:
    return {
        "name": Path(__file__).name,
        "version": GENERATOR_VERSION,
        "source_sha256": sha256_file(Path(__file__).resolve()),
        "seed": GENERATOR_SEED,
        "profile_id": PROFILE_ID,
        "resource_limits": {
            "path": "benchmark/provenance/resource-limits.json",
            "sha256": sha256_file(resource_limits),
        },
    }


def valid_provn(statement_count: int) -> bytes:
    """Return a syntactically simple PROV-N document with exactly N statements."""
    if statement_count <= 0:
        raise ValueError("statement_count must be positive")
    lines = ["document", f"  prefix ex <{EX_NAMESPACE}>"]
    lines.extend(f"  entity(ex:e{index})" for index in range(statement_count))
    lines.append("endDocument")
    return ("\n".join(lines) + "\n").encode("utf-8")


def hostile_blank_nodes(node_count: int) -> bytes:
    """Return a deterministic TriG blank-node chain with dense jump references."""
    if node_count <= 1:
        raise ValueError("node_count must be greater than one")
    lines = [
        f"@prefix ex: <{EX_NAMESPACE}> .",
        f"@prefix prov: <{PROV_NAMESPACE}> .",
        "ex:g {",
    ]
    for index in range(node_count):
        next_index = (index + 1) % node_count
        jump_index = (index * 37 + 17) % node_count
        lines.append(
            f"  _:b{index} a prov:Entity ; ex:next _:b{next_index} ; "
            f"ex:jump _:b{jump_index} ; ex:index {index} ."
        )
    lines.append("}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def generate(output: Path, resource_limits: Path = DEFAULT_RESOURCE_LIMITS) -> dict:
    resource_limits = resource_limits.resolve()
    limits_payload = load_resource_limits(resource_limits)
    identity = generator_identity(resource_limits)
    output.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for count in (1000, 10000, 100000):
        data = valid_provn(count)
        path = output / f"valid-{count}.provn"
        path.write_bytes(data)
        records.append(
            {
                "name": f"valid-{count}",
                "path": path.name,
                "format": "provn",
                "statement_count": count,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
                "purpose": "parser/converter/canonicalization performance",
                "profile_id": PROFILE_ID,
                "expected_status": "valid",
                "generator": {
                    **identity,
                    "input_parameters": {
                        "document_kind": "valid_provn",
                        "statement_count": count,
                        "namespace": EX_NAMESPACE,
                    },
                },
            }
        )
    for count in (1000, 5000, 10000):
        data = hostile_blank_nodes(count)
        path = output / f"hostile-bnodes-{count}.trig"
        path.write_bytes(data)
        records.append(
            {
                "name": f"hostile-bnodes-{count}",
                "path": path.name,
                "format": "trig",
                "blank_node_count": count,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
                "purpose": "RDF dataset canonicalization/resource-bound stress",
                "profile_id": PROFILE_ID,
                "expected_status": "resource_limit_or_bounded_canonicalization",
                "generator": {
                    **identity,
                    "input_parameters": {
                        "document_kind": "hostile_blank_nodes",
                        "blank_node_count": count,
                        "namespace": EX_NAMESPACE,
                        "prov_namespace": PROV_NAMESPACE,
                    },
                },
            }
        )
    manifest = {
        "schema_version": "research-handoff.t095.resource-corpus.v1",
        "status": "generated_not_measured",
        "release_evidence": False,
        "profile_id": PROFILE_ID,
        "generator": {
            **identity,
            "input_parameters": {
                "valid_statement_counts": [1000, 10000, 100000],
                "hostile_blank_node_counts": [1000, 5000, 10000],
            },
        },
        "resource_limits": {
            "path": "benchmark/provenance/resource-limits.json",
            "sha256": sha256_file(resource_limits),
            "limits": limits_payload["limits"],
        },
        "corpora": records,
        "release_measurements": [],
        "warning": "No generated corpus or digest is a T095 PASS until exact-head resource measurements and required approvals exist.",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resource-limits", type=Path, default=DEFAULT_RESOURCE_LIMITS)
    args = parser.parse_args()
    print(
        json.dumps(
            generate(args.output, args.resource_limits),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
