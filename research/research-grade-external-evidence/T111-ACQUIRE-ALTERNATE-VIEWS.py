#!/usr/bin/env python3
"""Acquire exact NGA open-access alternate views for T111 mediation coverage.

This is preparation only. It selects alternate institutional image records for the
already-selected 80 NGA objects, requires ``openaccess=1``, downloads bounded IIIF
renditions, hashes exact bytes, and leaves human rights/identity review null.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import tempfile
import urllib.request
from pathlib import Path

PUBLISHED_IMAGES_URI = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/published_images.csv"
)
USER_AGENT = "SWOS-T111-alternate-view-acquisition/1.0"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch(uri: str) -> bytes:
    request = urllib.request.Request(uri, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def download(uri: str, target: Path, max_bytes: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(uri, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise OSError(f"asset exceeds max bytes: {uri}")
        with tempfile.NamedTemporaryFile(delete=False, dir=target.parent) as handle:
            total = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    raise OSError(f"asset exceeds max bytes: {uri}")
                handle.write(block)
            temporary = Path(handle.name)
    os.replace(temporary, target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target", type=int, default=16)
    parser.add_argument("--max-asset-bytes", type=int, default=25 * 1024 * 1024)
    args = parser.parse_args()
    try:
        source = json.loads(args.source_manifest.read_text(encoding="utf-8"))
        records = source.get("records")
        if not isinstance(records, list) or len(records) < 80:
            raise ValueError("source candidate manifest lacks 80 records")
        by_object = {str(row["object_id"]): row for row in records}
        primary_uuids = {str(row["uuid"]) for row in records}
        table_bytes = fetch(PUBLISHED_IMAGES_URI)
        reader = csv.DictReader(io.StringIO(table_bytes.decode("utf-8-sig")))
        candidates = []
        for row in reader:
            object_id = str(row.get("depictstmsobjectid") or "").strip()
            uuid = str(row.get("uuid") or "").strip()
            if object_id not in by_object or not uuid or uuid in primary_uuids:
                continue
            if str(row.get("openaccess") or "").strip() != "1":
                continue
            if str(row.get("viewtype") or "").strip().lower() != "alternate":
                continue
            iiif = str(row.get("iiifurl") or "").strip().rstrip("/")
            if not iiif:
                continue
            candidates.append((object_id, int(row.get("sequence") or 999999), uuid, row, iiif))
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        selected = candidates[: args.target]
        if len(selected) < args.target:
            raise ValueError(
                f"only {len(selected)} qualifying alternate views found; target={args.target}"
            )
        out = args.output_dir.resolve()
        if out.exists() and any(out.iterdir()):
            raise ValueError(f"refusing to overwrite non-empty directory: {out}")
        assets_dir = out / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        output_records = []
        for index, (object_id, sequence, uuid, image_row, iiif) in enumerate(selected, 1):
            object_row = by_object[object_id]
            rendition = f"{iiif}/full/!1600,1600/0/default.jpg"
            target = assets_dir / f"nga-alt-{object_id}-{uuid}.jpg"
            download(rendition, target, args.max_asset_bytes)
            rights = object_row["rights"]
            output_records.append(
                {
                    "candidate_id": f"MM-NGA-ALT-{index:03d}",
                    "object_id": object_id,
                    "asset_id": f"NGA-{uuid}-ALTERNATE",
                    "uuid": uuid,
                    "institution": object_row["institution"],
                    "object_source_uri": object_row["object_uri"],
                    "source_uri": rendition,
                    "iiif_service_uri": iiif,
                    "viewtype": "alternate",
                    "sequence": sequence,
                    "mediation_condition": "institutional_alternate_view",
                    "rights_uri": rights["rights_uri"],
                    "rights_designation": rights["designation"],
                    "image_openaccess_flag": 1,
                    "allowed_actions_candidate": rights.get("allowed_actions_candidate") or [],
                    "attribution_statement": object_row["attribution_statement"],
                    "byte_sha256": sha256_file(target),
                    "byte_size": target.stat().st_size,
                    "source_width": image_row.get("width"),
                    "source_height": image_row.get("height"),
                    "source_assistive_text": image_row.get("assistivetext") or None,
                    "human_rights_review": None,
                    "human_identity_review": None,
                }
            )
        manifest = {
            "schema_version": "research-handoff.t111.nga-alternate-views.v1",
            "status": "THIRD_MEDIATION_CANDIDATES_READY_FOR_HUMAN_REVIEW",
            "source_candidate_manifest_sha256": sha256_file(args.source_manifest.resolve()),
            "published_images_snapshot": {
                "uri": PUBLISHED_IMAGES_URI,
                "sha256": sha256_bytes(table_bytes),
            },
            "record_count": len(output_records),
            "mediation_condition": "institutional_alternate_view",
            "records": output_records,
            "human_review": None,
            "release_evidence": False,
        }
        (out / "alternate-view-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        print(
            json.dumps(
                {"status": "ACQUISITION_FAILED", "reason": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "record_count": len(output_records),
                "output": str(out / "alternate-view-manifest.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
