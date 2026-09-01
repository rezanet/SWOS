"""Deterministically compile reviewed Turtle discipline packs to JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.discipline_ontology import (  # noqa: E402
    DisciplineOntologyRegistry,
    OntologyVersionError,
    parse_turtle,
)
from swos_runtime.models import canonical_digest, canonical_json  # noqa: E402

COMPILER_VERSION = "swos-discipline-compiler/2.0.0"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compile_release(
    manifest_path: Path | str, shapes_path: Path | str, output_dir: Path | str
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    shapes_path = Path(shapes_path)
    output_dir = Path(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest.get("version")) != "2.0.0":
        raise OntologyVersionError(
            f"unsupported ontology version {manifest.get('version', '<missing>')}"
        )
    registry = DisciplineOntologyRegistry().load(manifest_path)
    shapes = parse_turtle(shapes_path.read_text(encoding="utf-8"))
    shape_digest = _sha256(shapes_path.read_bytes())
    context_path = manifest_path.parent / "ontology" / "context.jsonld"
    context_digest = _sha256(context_path.read_bytes()) if context_path.is_file() else "missing"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[bytes] = []
    for discipline in registry.disciplines():
        profile = registry.profile(discipline)
        source_path = registry.root / profile.ontology_path
        triples = parse_turtle(source_path.read_text(encoding="utf-8"))
        payload = {
            "schema_version": "2.0.0",
            "ontology_version": registry.release.version if registry.release else "2.0.0",
            "ontology_iri": registry.release.version_iri if registry.release else "",
            "discipline": discipline,
            "discipline_iri": profile.discipline_iri,
            "pack_id": profile.pack_id,
            "pack_version": profile.pack_version,
            "ontology_digest": profile.ontology_digest,
            "source_digest": _sha256(source_path.read_bytes()),
            "shape_digest": shape_digest,
            "context_digest": context_digest,
            "compiler": COMPILER_VERSION,
            "profile": profile.to_dict(),
            "graph": [list(triple) for triple in triples],
            "shapes_graph": [list(triple) for triple in shapes],
        }
        encoded = (canonical_json(payload) + "\n").encode("utf-8")
        (output_dir / f"{discipline}.json").write_bytes(encoded)
        outputs.append(encoded)
    compiled_digest = _sha256(b"".join(outputs))
    report = {
        "schema_version": "2.0.0",
        "compiler": COMPILER_VERSION,
        "manifest": str(manifest_path),
        "source_digest": _sha256(manifest_path.read_bytes()),
        "shape_digest": shape_digest,
        "context_digest": context_digest,
        "tool_digest": canonical_digest({"compiler": COMPILER_VERSION}),
        "compiled_digest": compiled_digest,
        "packs": list(registry.disciplines()),
    }
    (output_dir / "release.json").write_bytes((canonical_json(report) + "\n").encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--shapes", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = compile_release(args.manifest, args.shapes, args.out)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes((canonical_json(report) + "\n").encode("utf-8"))
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
