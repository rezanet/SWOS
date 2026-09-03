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

PROV_NAMESPACE = "http://www.w3.org/ns/prov#"
EX_NAMESPACE = "https://example.org/swos/provbench/"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def generate(output: Path) -> dict:
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
            }
        )
    manifest = {
        "schema_version": "research-handoff.t095.resource-corpus.v1",
        "status": "generated_not_measured",
        "generator": Path(__file__).name,
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
    args = parser.parse_args()
    print(json.dumps(generate(args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
