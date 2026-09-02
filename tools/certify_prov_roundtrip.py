"""Certify the frozen EPG/PROV conversion matrix without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.models import canonical_digest  # noqa: E402
from swos_runtime.prov_model import ResourceLimits  # noqa: E402
from swos_runtime.prov_validation import certify_round_trip  # noqa: E402

REQUIRED_CORPUS_CATEGORIES = frozenset(
    {"valid", "invalid", "large", "adversarial", "hostile_blank_node"}
)


def _read(path: Path, limits: ResourceLimits | None = None) -> bytes:
    if limits is None:
        return path.read_bytes()
    with path.open("rb") as stream:
        raw = stream.read(limits.max_bytes + 1)
    limits.check_bytes(len(raw))
    return raw


def _load_json_with_digest(
    path: Path, limits: ResourceLimits | None = None
) -> tuple[dict[str, Any], str]:
    raw = _read(path, limits)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"PROV certification input must be a JSON object: {path}")
    return dict(payload), hashlib.sha256(raw).hexdigest()


def _load(path: Path, limits: ResourceLimits | None = None) -> dict[str, Any]:
    return _load_json_with_digest(path, limits)[0]


def _limits(path: Path) -> ResourceLimits:
    payload = _load(path)
    values = payload.get("limits")
    if not isinstance(values, Mapping):
        raise ValueError("PROV resource-limits manifest requires an explicit limits object")
    required = ("max_bytes", "max_statements", "max_literal_length", "max_depth", "timeout_seconds")
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError("PROV resource-limits manifest is missing: " + ", ".join(missing))
    integer_keys = ("max_bytes", "max_statements", "max_literal_length", "max_depth")
    if any(type(values[key]) is not int for key in integer_keys):
        raise ValueError("PROV resource-limits integer bounds must be JSON integers")
    if isinstance(values["timeout_seconds"], bool) or not isinstance(
        values["timeout_seconds"], (int, float)
    ):
        raise ValueError("PROV resource-limits timeout_seconds must be a JSON number")
    try:
        return ResourceLimits(
            max_bytes=values["max_bytes"],
            max_statements=values["max_statements"],
            max_literal_length=values["max_literal_length"],
            max_depth=values["max_depth"],
            timeout_seconds=values["timeout_seconds"],
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
        manifest, manifest_sha256 = _load_json_with_digest(corpus_manifest, limits)
        cases = manifest.get("cases")
        if not isinstance(cases, list):
            raise ValueError("PROV corpus manifest requires a cases list")
        if manifest.get("checksum_algorithm") != "sha256":
            raise ValueError("PROV corpus manifest requires checksum_algorithm=sha256")
        if cases:
            required_categories = manifest.get("required_categories")
            if (
                not isinstance(required_categories, list)
                or not all(isinstance(item, str) for item in required_categories)
                or set(required_categories) != REQUIRED_CORPUS_CATEGORIES
                or len(required_categories) != len(REQUIRED_CORPUS_CATEGORIES)
            ):
                raise ValueError("PROV corpus manifest has incomplete required_categories")
        certificates = []
        bindings = []
        seen_ids = set()
        seen_categories = set()
        root = corpus_manifest.parent.resolve()
        for index, case in enumerate(cases):
            if not isinstance(case, dict) or not isinstance(case.get("epg"), str):
                raise ValueError(f"PROV corpus case {index} lacks an EPG path")
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError(f"PROV corpus case {index} lacks an id")
            if case_id in seen_ids:
                raise ValueError(f"PROV corpus has duplicate case id: {case_id}")
            seen_ids.add(case_id)
            category = case.get("category")
            if not isinstance(category, str) or category not in REQUIRED_CORPUS_CATEGORIES:
                raise ValueError(f"PROV corpus case {index} has an unsupported category")
            seen_categories.add(category)
            case_path = (root / case["epg"]).resolve()
            if not case_path.is_relative_to(root):
                raise ValueError(f"PROV corpus case escapes its manifest directory: {case['epg']}")
            if not case_path.is_file():
                raise ValueError(f"PROV corpus EPG does not exist: {case_path}")
            expected_sha256 = case.get("sha256")
            if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
                raise ValueError(f"PROV corpus case {index} lacks a SHA-256 checksum")
            if any(character not in "0123456789abcdef" for character in expected_sha256):
                raise ValueError(f"PROV corpus case {index} has an invalid SHA-256 checksum")
            epg, actual_sha256 = _load_json_with_digest(case_path, limits)
            if actual_sha256 != expected_sha256:
                raise ValueError(f"PROV corpus case checksum mismatch: {case['epg']}")
            certificate = certify_round_trip(epg, formats, oracle=oracle, limits=limits).to_dict()
            certificates.append(certificate)
            bindings.append(
                {
                    "id": str(case.get("id") or index),
                    "epg": case["epg"],
                    "sha256": actual_sha256,
                    "category": category,
                    "source_sha": certificate["source_sha"],
                    "input_digest": certificate["input_digest"],
                }
            )
        if cases and seen_categories != REQUIRED_CORPUS_CATEGORIES:
            missing = sorted(REQUIRED_CORPUS_CATEGORIES - seen_categories)
            raise ValueError("PROV corpus is missing required categories: " + ", ".join(missing))
        statuses = {str(item.get("status")) for item in certificates}
        status = (
            "certified"
            if certificates and statuses == {"certified"}
            else ("failed" if "failed" in statuses else "not_run")
        )
        corpus_binding = {"manifest_sha256": manifest_sha256, "cases": bindings}
        source_sha = canonical_digest(corpus_binding)
        input_digest = canonical_digest(
            {
                "corpus_source_sha": source_sha,
                "case_input_digests": [item["input_digest"] for item in bindings],
            }
        )
        report = {
            "certificate_version": "2.0.0",
            "status": status,
            "profile": profile.get("profile_id", "swos.prov-dm-round-trip.v2"),
            "source_sha": source_sha,
            "input_digest": input_digest,
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


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)
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
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        TypeError,
        OverflowError,
        json.JSONDecodeError,
    ) as exc:
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
