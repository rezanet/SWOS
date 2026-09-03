#!/usr/bin/env python3
"""Build a single deterministic T094 ProvToolbox 2.2.3 oracle artifact.

The resulting ``.pyz`` binds the thin adapter, exact ProvToolbox runtime JARs,
transitive runtime dependencies, pinned upstream licence bytes and a complete
file-hash manifest into one SHA-256-addressable artifact. It is preparation only:
independent approval and independent execution remain mandatory before the
production oracle manifest may move from NOT_RUN to accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

VERSION = "2.2.3"
COORDINATE = f"org.openprovenance.prov:provconvert:{VERSION}"
TAG_COMMIT = "aef0816c2a277958774fac88cf0076248e7065cc"
LICENSE_URI = f"https://raw.githubusercontent.com/lucmoreau/ProvToolbox/{TAG_COMMIT}/license.txt"
LICENSE_SHA256 = "147f99cd87ca23fb66e8da69fba39ef5f937d12e3575f7ca1bbd942e00e55fba"
FIXED_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch(uri: str) -> bytes:
    request = urllib.request.Request(uri, headers={"User-Agent": "SWOS-T094-package-builder/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def maven_pom() -> str:
    return f"""<project xmlns=\"http://maven.apache.org/POM/4.0.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd\">\n  <modelVersion>4.0.0</modelVersion>\n  <groupId>org.swos.research</groupId>\n  <artifactId>provtoolbox-oracle-package</artifactId>\n  <version>1</version>\n  <dependencies>\n    <dependency>\n      <groupId>org.openprovenance.prov</groupId>\n      <artifactId>provconvert</artifactId>\n      <version>{VERSION}</version>\n    </dependency>\n  </dependencies>\n</project>\n"""


def dependency_tree(mvn: str, pom: Path, output: Path) -> None:
    process = subprocess.run(
        [mvn, "-q", "-f", str(pom), "dependency:tree", "-Dscope=runtime", f"-DoutputFile={output}", "-DappendOutput=false"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0 or not output.is_file():
        raise RuntimeError("Maven dependency:tree failed: " + process.stderr.decode("utf-8", errors="replace")[-2000:])


def copy_dependencies(mvn: str, pom: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        [mvn, "-q", "-f", str(pom), "dependency:copy-dependencies", "-DincludeScope=runtime", f"-DoutputDirectory={output}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError("Maven dependency:copy-dependencies failed: " + process.stderr.decode("utf-8", errors="replace")[-2000:])


def run_version_probe(lib: Path) -> dict[str, Any]:
    jars = sorted(lib.glob("*.jar"))
    classpath = os.pathsep.join(str(path) for path in jars)
    process = subprocess.run(
        ["java", "-cp", classpath, "org.openprovenance.prov.interop.CommandLineArguments", "--version"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError("ProvToolbox --version probe failed")
    combined = (process.stdout + b"\n" + process.stderr).decode("utf-8", errors="replace")
    if VERSION not in combined:
        raise RuntimeError(f"ProvToolbox version probe did not report pinned version {VERSION}")
    return {
        "exit_code": process.returncode,
        "stdout_sha256": sha256_bytes(process.stdout),
        "stderr_sha256": sha256_bytes(process.stderr),
        "reported_text": combined.strip(),
    }


def write_deterministic_zip(root: Path, output: Path) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, default=Path(__file__).with_name("T094-ORACLE-ADAPTER.py"))
    parser.add_argument("--output", type=Path, required=True, help="Output .pyz path")
    parser.add_argument("--manifest-out", type=Path, default=None)
    args = parser.parse_args()
    try:
        mvn = shutil.which("mvn") or shutil.which("mvn.cmd")
        java = shutil.which("java")
        if not mvn or not java:
            raise RuntimeError("mvn and java are required")
        adapter = args.adapter.resolve()
        if not adapter.is_file():
            raise FileNotFoundError(adapter)
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise RuntimeError(f"refusing to overwrite oracle artifact: {output}")
        with tempfile.TemporaryDirectory(prefix="swos-t094-package-") as temp_name:
            temp = Path(temp_name)
            staging = temp / "staging"
            lib = staging / "lib"
            staging.mkdir(parents=True)
            pom = temp / "pom.xml"
            pom.write_text(maven_pom(), encoding="utf-8")
            tree_path = staging / "DEPENDENCY-TREE.txt"
            dependency_tree(mvn, pom, tree_path)
            copy_dependencies(mvn, pom, lib)
            jars = sorted(lib.glob("*.jar"))
            if not any(path.name == f"provconvert-{VERSION}.jar" for path in jars):
                raise RuntimeError("pinned provconvert JAR is absent from runtime closure")
            licence = fetch(LICENSE_URI)
            if sha256_bytes(licence) != LICENSE_SHA256:
                raise RuntimeError("pinned ProvToolbox licence bytes do not match expected SHA-256")
            (staging / "LICENSE-provtoolbox.txt").write_bytes(licence)
            shutil.copyfile(adapter, staging / "__main__.py")
            probe = run_version_probe(lib)
            files = []
            for path in sorted(staging.rglob("*"), key=lambda p: p.relative_to(staging).as_posix()):
                if path.is_file() and path.name != "package-manifest.json":
                    files.append({
                        "path": path.relative_to(staging).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                    })
            manifest = {
                "schema_version": "research-handoff.t094.provtoolbox-package.v1",
                "status": "package_built_pending_independent_approval_and_execution",
                "implementation": "ProvToolbox",
                "version": VERSION,
                "coordinate": COORDINATE,
                "upstream_tag_commit": TAG_COMMIT,
                "license": {
                    "spdx": "MIT",
                    "source_uri": LICENSE_URI,
                    "sha256": LICENSE_SHA256,
                },
                "runtime": {
                    "main_class": "org.openprovenance.prov.interop.CommandLineArguments",
                    "jar_count": len(jars),
                    "java_executable": java,
                    "version_probe": probe,
                },
                "files": files,
                "artifact_contract": {
                    "single_file": True,
                    "python_zipapp": True,
                    "invocation": ["python3", "{artifact}", "--artifact", "{artifact}", "--input", "{input}", "--profile", "{profile}", "--formats", "{formats}", "--output", "{output}"],
                    "note": "The artifact hashes and contains the adapter plus the full runtime dependency closure; no network dependency resolution is needed during certification."
                },
                "independent_approval": None,
                "independent_execution": "NOT_RUN",
                "release_evidence": False,
            }
            (staging / "package-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            # Add the manifest to its own file list only through the outer artifact
            # digest; package-manifest.json cannot recursively contain its own hash.
            write_deterministic_zip(staging, output)
        artifact_sha = sha256_file(output)
        outer = {
            **manifest,
            "artifact": {
                "path": str(output),
                "bytes": output.stat().st_size,
                "sha256": artifact_sha,
            },
            "candidate_oracle_manifest_patch": {
                "schema_version": "2.0.0",
                "status": "not_run_pending_independent_approval",
                "implementation": "ProvToolbox",
                "version": VERSION,
                "licence": "MIT",
                "artifact_uri": None,
                "artifact_sha256": artifact_sha,
                "command": ["python3", "{artifact}", "--artifact", "{artifact}", "--input", "{input}", "--profile", "{profile}", "--formats", "{formats}", "--output", "{output}"],
                "reason": "Artifact prepared and hashed; independent approval and execution still required before accepted status."
            }
        }
        manifest_out = (args.manifest_out.resolve() if args.manifest_out else output.with_suffix(output.suffix + ".manifest.json"))
        if manifest_out.exists():
            raise RuntimeError(f"refusing to overwrite package manifest: {manifest_out}")
        manifest_out.write_text(json.dumps(outer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(json.dumps({"status": "PACKAGE_BUILD_FAILED", "reason": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "PACKAGE_BUILT_PENDING_EXTERNAL_APPROVAL", "artifact": str(output), "artifact_sha256": artifact_sha, "manifest": str(manifest_out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
