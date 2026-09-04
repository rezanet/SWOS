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
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

MAIN_CLASS = "org.openprovenance.prov.interop.CommandLineArguments"
PACKAGE_SCHEMA = "research-handoff.t094.provtoolbox-package.v1"
PACKAGE_VERSION = "2.2.3"
PACKAGE_COORDINATE = f"org.openprovenance.prov:provconvert:{PACKAGE_VERSION}"
PACKAGE_LICENSE_SHA256 = "147f99cd87ca23fb66e8da69fba39ef5f937d12e3575f7ca1bbd942e00e55fba"
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


def _require_sha256(value: Any, context: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise ValueError(f"{context} must be a lowercase SHA-256")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{context} must be a lowercase SHA-256")
    return value


def _safe_member_path(root: Path, name: str) -> Path | None:
    """Resolve a ZIP member without permitting traversal or host paths."""

    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError("unsafe oracle package ZIP member path")
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or (path.parts and ":" in path.parts[0])
    ):
        raise ValueError(f"unsafe oracle package ZIP member path: {name}")
    destination = (root / Path(*path.parts)).resolve()
    if not destination.is_relative_to(root):
        raise ValueError(f"unsafe oracle package ZIP member path: {name}")
    if normalized.endswith("/"):
        return None
    return destination


def _validate_package_manifest(manifest: dict[str, Any], member_names: set[str]) -> None:
    if manifest.get("schema_version") != PACKAGE_SCHEMA:
        raise ValueError("oracle package manifest has an unsupported schema")
    if manifest.get("implementation") != "ProvToolbox":
        raise ValueError("oracle package manifest is not a ProvToolbox package")
    if manifest.get("version") != PACKAGE_VERSION:
        raise ValueError("oracle package manifest is not pinned to ProvToolbox 2.2.3")
    if manifest.get("coordinate") != PACKAGE_COORDINATE:
        raise ValueError("oracle package manifest has an unexpected Maven coordinate")
    if manifest.get("release_evidence") is not False:
        raise ValueError("oracle package manifest must keep release_evidence=false")
    if manifest.get("independent_execution") != "NOT_RUN":
        raise ValueError("oracle package must remain pending independent execution")
    if manifest.get("independent_approval") is not None:
        raise ValueError("oracle package must remain pending independent approval")
    license_payload = manifest.get("license")
    if not isinstance(license_payload, dict):
        raise ValueError("oracle package manifest lacks license binding")
    if license_payload.get("spdx") != "MIT":
        raise ValueError("oracle package must retain the pinned MIT license")
    if license_payload.get("sha256") != PACKAGE_LICENSE_SHA256:
        raise ValueError("oracle package license digest is not pinned")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("main_class") != MAIN_CLASS:
        raise ValueError("oracle package manifest lacks the pinned runtime entry point")
    if runtime.get("java_executable") != "java":
        raise ValueError("oracle package must use the stable java executable identity")
    contract = manifest.get("artifact_contract")
    if (
        not isinstance(contract, dict)
        or contract.get("single_file") is not True
        or contract.get("python_zipapp") is not True
    ):
        raise ValueError("oracle package manifest lacks the single-file artifact contract")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValueError("oracle package manifest files must be a list")
    expected: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("oracle package manifest contains an invalid file entry")
        path = entry["path"]
        if path == "package-manifest.json" or path in expected:
            raise ValueError("oracle package manifest contains a duplicate or recursive file entry")
        _safe_member_path(Path.cwd().resolve(), path)
        if type(entry.get("bytes")) is not int or entry["bytes"] < 0:
            raise ValueError(f"oracle package manifest has invalid byte count: {path}")
        _require_sha256(entry.get("sha256"), f"oracle package file {path}.sha256")
        expected[path] = entry
    actual = member_names - {"package-manifest.json"}
    if actual != set(expected):
        raise ValueError("oracle package archive members do not match its manifest")


def find_repo_root(input_path: Path) -> Path:
    candidates = [input_path.resolve().parent, Path.cwd().resolve()]
    for start in candidates:
        for root in (start, *start.parents):
            if (root / "swos_runtime" / "prov_interop.py").is_file() and (
                root / "swos_runtime" / "prov_validation.py"
            ).is_file():
                return root
    raise RuntimeError("unable to locate SWOS repository root from oracle execution context")


def extract_runtime(artifact: Path, target: Path) -> Path:
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(artifact) as archive:
        infos = archive.infolist()
        names = {info.filename for info in infos if not info.is_dir()}
        if "package-manifest.json" not in names:
            raise RuntimeError("oracle artifact lacks package-manifest.json")
        if len(names) != len([info for info in infos if not info.is_dir()]):
            raise ValueError("oracle package contains duplicate ZIP member names")
        for info in infos:
            _safe_member_path(target, info.filename)
        try:
            manifest = json.loads(archive.read("package-manifest.json").decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("oracle package manifest is not valid UTF-8 JSON") from exc
        if not isinstance(manifest, dict):
            raise ValueError("oracle package manifest must be a JSON object")
        _validate_package_manifest(manifest, names)
        entries = {entry["path"]: entry for entry in manifest["files"]}
        for info in infos:
            if info.is_dir():
                continue
            data = archive.read(info)
            if info.filename == "package-manifest.json":
                destination = target / "package-manifest.json"
            else:
                entry = entries[info.filename]
                if (
                    len(data) != entry["bytes"]
                    or hashlib.sha256(data).hexdigest() != entry["sha256"]
                ):
                    raise RuntimeError(f"oracle package file digest mismatch: {info.filename}")
                destination = _safe_member_path(target, info.filename)
                if destination is None:
                    continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    return target


def java_classpath(runtime: Path) -> str:
    jars = sorted((runtime / "lib").glob("*.jar"))
    if not jars:
        raise RuntimeError("oracle package contains no ProvToolbox runtime jars")
    return os.pathsep.join(str(path) for path in jars)


def run_provconvert(classpath: str, source: Path, in_format: str, output: Path) -> dict[str, Any]:
    argv = [
        "java",
        "-cp",
        classpath,
        MAIN_CLASS,
        "-infile",
        str(source),
        "-informat",
        in_format,
        "-outfile",
        str(output),
        "-outformat",
        "provn",
    ]
    process = subprocess.run(
        argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    return {
        "exit_code": process.returncode,
        "command_sha256": hashlib.sha256(
            json.dumps(argv, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
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
        if not requested or len(set(requested)) != len(requested):
            raise ValueError("duplicate requested PROV format")
        if any(item not in FORMAT_TO_PROVTOOLBOX for item in requested):
            raise ValueError("unsupported requested PROV format")
        profile_payload = json.loads(args.profile.read_text(encoding="utf-8"))
        profile_id = profile_payload.get("profile_id")
        if profile_id != "swos.prov-dm-round-trip.v2":
            raise ValueError("profile file lacks the frozen SWOS PROV profile")
        epg = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(epg, dict):
            raise ValueError("oracle input must be an EPG JSON object")
        repo_root = find_repo_root(args.input)
        sys.path.insert(0, str(repo_root))
        from swos_runtime.prov_interop import epg_to_prov, serialize_prov
        from swos_runtime.prov_model import ResourceLimits
        from swos_runtime.prov_validation import canonical_fingerprint

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
            version_text = (version_probe.stdout + b"\n" + version_probe.stderr).decode(
                "utf-8", errors="replace"
            )
            if version_probe.returncode != 0 or PACKAGE_VERSION not in version_text:
                raise RuntimeError("ProvToolbox version probe did not report pinned version 2.2.3")
            for fmt in requested:
                source = temp / (
                    "input"
                    + {"prov-json": ".json", "prov-n": ".provn", "prov-o-trig": ".trig"}[fmt]
                )
                source.write_bytes(serialize_prov(document, fmt))
                converted = temp / f"parsed-{fmt}.provn"
                check = run_provconvert(classpath, source, FORMAT_TO_PROVTOOLBOX[fmt], converted)
                check["source_sha256"] = sha256(source)
                check["source_bytes"] = source.stat().st_size
                checks[fmt] = check
                if (
                    check["exit_code"] != 0
                    or not converted.is_file()
                    or converted.stat().st_size == 0
                ):
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
                "java_executable": "java",
                "version_probe_exit_code": version_probe.returncode,
                "version_probe_stdout_sha256": hashlib.sha256(version_probe.stdout).hexdigest(),
                "version_probe_stderr_sha256": hashlib.sha256(version_probe.stderr).hexdigest(),
            },
            "format_checks": checks,
            "policy_decision": "none; adapter only verifies independent parser acceptance of emitted interchange bytes",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise RuntimeError(f"refusing to overwrite oracle output: {args.output}")
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        print(
            json.dumps(
                {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False
            )
        )
        return 2
    print(
        json.dumps(
            {"status": "pass", "output": str(args.output), "formats": list(requested)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
