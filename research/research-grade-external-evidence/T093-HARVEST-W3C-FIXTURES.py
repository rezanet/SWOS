#!/usr/bin/env python3
"""Harvest the pinned W3C PROV test catalogue into a checksummed T093 inventory.

PREPARATION ONLY. The source authority is the historical W3C PROV repository at
one exact Git commit. The script downloads only the exact test files named by the
pinned catalogue and records SHA-256 over the acquired bytes. Modified/adversarial
fixtures must be stored separately as SWOS fixtures and must never be represented
as unchanged W3C conformance cases.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

W3C_REPO = "w3c/prov"
W3C_COMMIT = "aa82bd71b6bb1f7b735bf3f7f5b948fae87764f0"
CATALOG_PATH = "testcases/all-tests.txt"
CATALOG_GIT_BLOB = "0c8940cf34282a3728a0b5b6794892c73be9f727"
REPORTED_CASE_COUNT = 280
RAW_ROOT = f"https://raw.githubusercontent.com/{W3C_REPO}/{W3C_COMMIT}/"
CATALOG_URI = RAW_ROOT + CATALOG_PATH
TEST_SUITE_LICENCE_URI = "https://www.w3.org/copyright/test-suites-licenses/"


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fetch(uri: str) -> bytes:
    request = urllib.request.Request(uri, headers={"User-Agent": "SWOS-T093-fixture-harvester/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def legacy_to_repo_path(uri: str) -> str:
    path = urlparse(uri).path
    marker = "/testcases/"
    if marker not in path:
        raise ValueError(f"not a W3C PROV testcase URI: {uri}")
    return "testcases/" + path.split(marker, 1)[1]


def case_identity(path: str) -> tuple[str, str]:
    stem = Path(path).stem
    if "-PASS-" in stem:
        expected = "pass"
    elif "-FAIL-" in stem:
        expected = "fail"
    else:
        expected = "unspecified"
    return stem, expected


def constraint_ids(case_id: str) -> list[str]:
    return sorted(set(re.findall(r"(?:^|-)(c\d+)(?:-|$)", case_id)))


def harvest(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    catalog_bytes = fetch(CATALOG_URI)
    links = [line.strip() for line in catalog_bytes.decode("utf-8").splitlines() if line.strip()]
    grouped: dict[str, dict] = defaultdict(lambda: {"representations": {}})

    for legacy_uri in links:
        repo_path = legacy_to_repo_path(legacy_uri)
        case_id, expected = case_identity(repo_path)
        extension = Path(repo_path).suffix.lower()
        representation = {".provn": "provn", ".ttl": "prov_o_turtle", ".provx": "prov_xml"}.get(extension)
        if representation is None:
            continue
        pinned_uri = RAW_ROOT + repo_path
        data = fetch(pinned_uri)
        target = output / repo_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        record = grouped[case_id]
        record.update(
            {
                "case_id": case_id,
                "case_class": case_id.split("-", 1)[0],
                "expected_validation": expected,
                "constraint_ids": constraint_ids(case_id),
                "source_commit": W3C_COMMIT,
                "license_route": "unchanged_w3c_testcase_pending_exact_notice_confirmation",
            }
        )
        record["representations"][representation] = {
            "repo_path": repo_path,
            "legacy_uri": legacy_uri,
            "pinned_uri": pinned_uri,
            "bytes": len(data),
            "sha256": sha256(data),
        }

    cases = sorted(grouped.values(), key=lambda item: item["case_id"])
    manifest = {
        "schema_version": "research-handoff.t093.w3c-fixture-inventory.v2",
        "status": "harvested_pending_license_notice_and_swos_admission_review",
        "source": {
            "repository": W3C_REPO,
            "commit": W3C_COMMIT,
            "catalog_path": CATALOG_PATH,
            "catalog_git_blob": CATALOG_GIT_BLOB,
            "catalog_uri": CATALOG_URI,
            "catalog_sha256": sha256(catalog_bytes),
            "w3c_reported_case_count": REPORTED_CASE_COUNT,
            "test_suite_license_policy": TEST_SUITE_LICENCE_URI,
        },
        "case_count": len(cases),
        "representation_file_count": sum(len(case["representations"]) for case in cases),
        "cases": cases,
        "admission": {
            "independent_approval": None,
            "oracle_execution": "NOT_RUN",
            "warning": "Hashes prove byte identity only. They do not by themselves establish T093 admission or W3C conformance claims."
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = harvest(args.output)
    print(json.dumps({"status": result["status"], "case_count": result["case_count"], "representation_file_count": result["representation_file_count"]}, sort_keys=True))
    return 0 if result["case_count"] == REPORTED_CASE_COUNT else 2


if __name__ == "__main__":
    raise SystemExit(main())
