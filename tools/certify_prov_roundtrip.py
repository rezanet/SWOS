"""Certify the frozen EPG/PROV conversion matrix without network access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.prov_model import ResourceLimits  # noqa: E402
from swos_runtime.prov_validation import certify_round_trip  # noqa: E402


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _limits(path: Path) -> ResourceLimits:
    payload = _load(path)
    if isinstance(payload, dict) and isinstance(payload.get("limits"), dict):
        payload = payload["limits"]
    return ResourceLimits(
        max_bytes=int(payload.get("max_bytes", ResourceLimits.max_bytes)),
        max_statements=int(payload.get("max_statements", ResourceLimits.max_statements)),
        max_literal_length=int(
            payload.get("max_literal_length", ResourceLimits.max_literal_length)
        ),
        max_depth=int(payload.get("max_depth", ResourceLimits.max_depth)),
        timeout_seconds=float(payload.get("timeout_seconds", ResourceLimits.timeout_seconds)),
    )


def certify(
    *,
    epg_path: Path | None,
    corpus_manifest: Path | None,
    profile_path: Path,
    formats: tuple[str, ...],
    oracle_path: Path,
    limits_path: Path,
    artifact_dir: Path,
    certificate_out: Path,
) -> dict[str, Any]:
    if (epg_path is None) == (corpus_manifest is None):
        raise ValueError("exactly one of --epg and --corpus-manifest is required")
    profile = _load(profile_path)
    oracle = _load(oracle_path)
    limits = _limits(limits_path)
    if tuple(formats) != tuple(dict.fromkeys(formats)):
        raise ValueError("PROV formats must not be duplicated")
    if not set(formats).issubset({"prov-json", "prov-n", "prov-o-trig"}):
        raise ValueError("unsupported PROV format in certification matrix")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if epg_path is not None:
        certificate = certify_round_trip(_load(epg_path), formats, oracle=oracle, limits=limits)
        report = certificate.to_dict()
        report["profile_manifest"] = profile
    else:
        manifest = _load(corpus_manifest)
        cases = manifest.get("cases", []) if isinstance(manifest, dict) else []
        certificates = []
        root = corpus_manifest.parent
        for case in cases:
            if not isinstance(case, dict) or not case.get("epg"):
                continue
            case_path = (root / str(case["epg"])).resolve()
            certificates.append(
                certify_round_trip(
                    _load(case_path), formats, oracle=oracle, limits=limits
                ).to_dict()
            )
        statuses = {str(item.get("status")) for item in certificates}
        status = (
            "certified"
            if certificates and statuses == {"certified"}
            else ("failed" if "failed" in statuses else "not_run")
        )
        report = {
            "certificate_version": "2.0.0",
            "status": status,
            "profile": profile.get("profile_id", "swos.prov-dm-round-trip.v2"),
            "source_sha": "0" * 64,
            "input_digest": "0" * 64,
            "paths": list(formats),
            "legs": certificates,
            "oracle": oracle,
            "limitations": []
            if status == "certified"
            else ["The corpus or independent oracle is not release-complete."],
            "limits": limits.__dict__,
            "profile_manifest": profile,
        }
    if certificate_out.exists():
        raise RuntimeError(f"immutable certificate already exists: {certificate_out}")
    certificate_out.parent.mkdir(parents=True, exist_ok=True)
    certificate_out.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--epg", type=Path)
    source.add_argument("--corpus-manifest", type=Path)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--formats", nargs="+", required=True)
    parser.add_argument("--oracle-manifest", type=Path, required=True)
    parser.add_argument("--limits", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--certificate-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = certify(
            epg_path=args.epg,
            corpus_manifest=args.corpus_manifest,
            profile_path=args.profile,
            formats=tuple(args.formats),
            oracle_path=args.oracle_manifest,
            limits_path=args.limits,
            artifact_dir=args.artifact_dir,
            certificate_out=args.certificate_out,
        )
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "not_run", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {"status": result.get("status"), "certificate": str(args.certificate_out)},
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "certified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
