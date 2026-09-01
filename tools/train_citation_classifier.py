"""Create an immutable model manifest; real training is an opt-in release job."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.citation_classifier import LABELS  # noqa: E402
from swos_runtime.models import canonical_digest  # noqa: E402


def train_model(config_path: Path | str, dataset_manifest_path: Path | str, output_dir: Path | str) -> dict[str, Any]:
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"immutable model output already exists: {output_dir}")
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    dataset = json.loads(Path(dataset_manifest_path).read_text(encoding="utf-8"))
    if dataset.get("status") != "frozen":
        status = "not_run"
        reason = "dataset manifest is not a frozen licensed/adjudicated release"
    else:
        status = "not_run"
        reason = "real model training requires the separately approved optional training environment"
    model_payload = {
        "schema_version": "2.0.0",
        "status": status,
        "reason": reason,
        "config_digest": canonical_digest(config),
        "dataset_manifest_digest": canonical_digest(dataset),
        "label_order": list(LABELS),
        "ontology_version": str(config.get("ontology_version") or "2.0.0"),
        "ontology_digest": str(config.get("ontology_digest") or ""),
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
    }
    artifact = json.dumps(model_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = output_dir / "model-artifact.json"
    artifact_path.write_bytes(artifact)
    report = {**model_payload, "model_id": "swos-citation-support-v2", "artifact_path": str(artifact_path), "model_digest": __import__("hashlib").sha256(artifact).hexdigest(), "verified": False}
    (output_dir / "model-manifest.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = train_model(args.config, args.dataset_manifest, args.out_dir)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "not_run", "reason": str(exc)}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
