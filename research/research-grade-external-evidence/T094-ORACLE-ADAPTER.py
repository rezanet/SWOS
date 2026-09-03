#!/usr/bin/env python3
"""Thin executable adapter between SWOS EPG input and ProvToolbox 2.2.3.

The adapter is preparation for T094. It does not decide SWOS scholarly policy and
is not itself the independent oracle. For each requested public PROV interchange
format it asks SWOS to emit the exact candidate representation, then requires the
pinned ProvToolbox runtime bundled inside this executable archive to parse that
representation successfully into PROV-N. The acceptance decision is therefore
bound to an external PROV implementation; SWOS cannot satisfy T094 by parsing its
own bytes alone.

The final package containing this adapter and the complete ProvToolbox dependency
closure must be independently approved and then executed outside the builder's
self-attestation context. Until that happens, T094 remains NOT_RUN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

MAIN_CLASS = "org.openprovenance.prov.interop.CommandLineArguments"
FORMAT_TO_PROVTOOLBOX = {
    "prov-json": "json",
    "prov-n": "provn",
    "prov-o-trig": "trig",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def find_repo_root(input_path: Path) -> Path:
    candidates = [input_path.resolve().parent, Path.cwd().resolve()]
    for start in candidates:
        for root in (start, *start.parents):
            if (root / "swos_runtime" / "prov_interop.py").is_file() and (root / "swos_runtime" / "prov_validation.py").is_file():
                return root
    raise RuntimeError("unable to locate SWOS repository root from oracle execution context")


def extract_runtime(artifact: Path, target: Path) -> Path:
    with zipfile.ZipFile(artifact) as archive:
        names = set(archive.namelist())
        if "package-manifest.json" not in names:
            raise RuntimeError("oracle artifact lacks package-manifest.json")
        archive.extractall(target)
    manifest_path = target / "package-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("implementation") != "ProvToolbox" or manifest.get("version") != "2.2.3":
        raise RuntimeError("oracle artifact identity is not pinned ProvToolbox 2.2.3")
    for entry in manifest.get("files", []):
        path = target / str(entry.get("path") or "")
        if not path.is_file() or sha256(path) != entry.get("sha256"):
            raise RuntimeError(f"oracle package file digest mismatch: {entry.get('path')}")
    return target


def java_classpath(runtime: Path) -> str:
    jars = sorted((runtime / "lib").glob("*.jar"))
    if not jars:
        raise RuntimeError("oracle package contains no ProvToolbox runtime jars")
    return os.pathsep.join(str(path) for path in jars)


def run_provconvert(classpath: str, source: Path, in_format: str, output: Path) -> dict[str, Any]:
    argv = [
        "java", "-cp", classpath, MAIN_CLASS,
        "-infile", str(source),
        "-informat", in_format,
        "-outfile", str(output),
        "-outformat", "provn",
    ]
    process = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return {
        "exit_code": process.returncode,
        "command_sha256": hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "stdout_sha256": hashlib.sha256(process.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(process.stderr).hexdigest(),
        "output_sha256": sha256(output) if output.is_file() else None,
        "output_bytes": output.stat().st_size if output.is_file() else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--formats", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        requested = tuple(item.strip() for item in args.formats.split(",") if item.strip())
        if not requested or any(item not in FORMAT_TO_PROVTOOLBOX for item in requested):
            raise ValueError("unsupported requested PROV format")
        profile_payload = json.loads(args.profile.read_text(encoding="utf-8"))
        profile_id = profile_payload.get("profile_id")
        if not isinstance(profile_id, str) or not profile_id:
            raise ValueError("profile file lacks profile_id")
        epg = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(epg, dict):
            raise ValueError("oracle input must be an EPG JSON object")
        repo_root = find_repo_root(args.input)
        sys.path.insert(0, str(repo_root))
        from swos_runtime.prov_interop import epg_to_prov, serialize_prov
        from swos_runtime.prov_validation import canonical_fingerprint
        from swos_runtime.prov_model import ResourceLimits

        document = epg_to_prov(epg, base_iri=str(epg.get("base_iri") or ""))
        input_digest = canonical_fingerprint(document, ResourceLimits()).semantic_digest
        checks: dict[str, Any] = {}
        with tempfile.TemporaryDirectory(prefix="swos-provtoolbox-oracle-") as temp_name:
            temp = Path(temp_name)
            runtime = extract_runtime(args.artifact.resolve(), temp / "runtime")
            classpath = java_classpath(runtime)
            version_probe = subprocess.run(
                ["java", "-cp", classpath, MAIN_CLASS, "--version"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            for fmt in requested:
                source = temp / ("input" + {"prov-json": ".json", "prov-n": ".provn", "prov-o-trig": ".trig"}[fmt])
                source.write_bytes(serialize_prov(document, fmt))
                converted = temp / f"parsed-{fmt}.provn"
                check = run_provconvert(classpath, source, FORMAT_TO_PROVTOOLBOX[fmt], converted)
                check["source_sha256"] = sha256(source)
                check["source_bytes"] = source.stat().st_size
                checks[fmt] = check
                if check["exit_code"] != 0 or not converted.is_file() or converted.stat().st_size == 0:
                    raise RuntimeError(f"ProvToolbox rejected or failed to convert {fmt}")
        result = {
            "status": "pass",
            "input_digest": input_digest,
            "profile": profile_id,
            "formats": list(requested),
            "oracle": {
                "implementation": "ProvToolbox",
                "version": "2.2.3",
                "artifact_sha256": sha256(args.artifact.resolve()),
                "java": shutil.which("java"),
                "version_probe_exit_code": version_probe.returncode,
                "version_probe_stdout_sha256": hashlib.sha256(version_probe.stdout).hexdigest(),
                "version_probe_stderr_sha256": hashlib.sha256(version_probe.stderr).hexdigest(),
            },
            "format_checks": checks,
            "policy_decision": "none; adapter only verifies independent parser acceptance of emitted interchange bytes"
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise RuntimeError(f"refusing to overwrite oracle output: {args.output}")
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(json.dumps({"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "pass", "output": str(args.output), "formats": list(requested)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
