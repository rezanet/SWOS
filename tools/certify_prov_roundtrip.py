"""Certify the frozen EPG/PROV conversion matrix without network access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.prov_model import ResourceLimits  # noqa: E402
from swos_runtime.prov_validation import certify_round_trip  # noqa: E402


def _load(path: Path, limits: ResourceLimits | None = None) -> dict[str, Any]:
    if limits is None:
        raw = path.read_bytes()
    else:
        with path.open("rb") as stream:
            raw = stream.read(limits.max_bytes + 1)
        limits.check_bytes(len(raw))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"PROV certification input must be a JSON object: {path}")
    return dict(payload)


def _limits(path: Path) -> ResourceLimits:
    payload = _load(path)
    values = payload.get("limits")
    if not isinstance(values, Mapping):
        raise ValueError("PROV resource-limits manifest requires an explicit limits object")
    required = ("max_bytes", "max_statements", "max_literal_length", "max_depth", "timeout_seconds")
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError("PROV resource-limits manifest is missing: " + ", ".join(missing))
    try:
        return ResourceLimits(
            max_bytes=int(values["max_bytes"]),
            max_statements=int(values["max_statements"]),
            max_literal_length=int(values["max_literal_length"]),
            max_depth=int(values["max_depth"]),
            timeout_seconds=float(values["timeout_seconds"]),
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("PROV resource-limits manifest contains invalid bounds") from exc


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
    limits = _limits(limits_path)
    profile = _load(profile_path, limits)
    oracle = _load(oracle_path, limits)
    if tuple(formats) != tuple(dict.fromkeys(formats)):
        raise ValueError("PROV formats must not be duplicated")
    if not set(formats).issubset({"prov-json", "prov-n", "prov-o-trig"}):
        raise ValueError("unsupported PROV format in certification matrix")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if epg_path is not None:
        certificate = certify_round_trip(
            _load(epg_path, limits), formats, oracle=oracle, limits=limits
        )
        report = certificate.to_dict()
        report["profile_manifest"] = profile
    else:
        manifest = _load(corpus_manifest, limits)
        cases = manifest.get("cases")
        if not isinstance(cases, list):
            raise ValueError("PROV corpus manifest requires a cases list")
        certificates = []
        root = corpus_manifest.parent.resolve()
        for index, case in enumerate(cases):
            if not isinstance(case, dict) or not isinstance(case.get("epg"), str):
                raise ValueError(f"PROV corpus case {index} lacks an EPG path")
            case_path = (root / case["epg"]).resolve()
            if not case_path.is_relative_to(root):
                raise ValueError(f"PROV corpus case escapes its manifest directory: {case['epg']}")
            if not case_path.is_file():
                raise ValueError(f"PROV corpus EPG does not exist: {case_path}")
            certificates.append(
                certify_round_trip(
                    _load(case_path, limits), formats, oracle=oracle, limits=limits
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
