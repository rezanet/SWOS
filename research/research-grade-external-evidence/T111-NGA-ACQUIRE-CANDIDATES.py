#!/usr/bin/env python3
"""Acquire checksummed National Gallery of Art Open Access candidates for T111.

PREPARATION ONLY. This script does not create human grounding labels, rights
approval, discipline review, adversarial truth, or T111 completion evidence.

It consumes the NGA Open Data `objects.csv` and `published_images.csv` tables,
selects only image rows whose official `openaccess` flag is 1, joins object
metadata, deliberately balances media classes, optionally downloads bounded IIIF
renditions, and writes a candidate manifest with exact byte SHA-256 values.

The NGA data dictionary defines `openaccess = 1` as an open-access image with no
usage restriction. The repository dataset itself is CC0, while image rights are
tracked separately through that image-level flag; do not infer image rights from
mere inclusion in the dataset.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OBJECTS_URL = "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/objects.csv"
IMAGES_URL = "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/published_images.csv"
DATASET_URI = "https://github.com/NationalGalleryOfArt/opendata"
DATA_DICTIONARY_URI = "https://github.com/NationalGalleryOfArt/opendata/blob/main/documentation/Data%20Dictionary.txt"
IMAGE_RIGHTS_URI = "https://www.nga.gov/artworks/free-images-and-open-access"
CC0_URI = "https://creativecommons.org/publicdomain/zero/1.0/"
USER_AGENT = "SWOS-T111-NGA-acquisition/1.0 (research preparation)"

MEDIA_QUOTAS = {
    "painting": 12,
    "drawing_watercolor": 12,
    "print": 12,
    "photograph": 10,
    "sculpture": 8,
    "decorative_functional": 8,
    "textile_ceramic_metalwork": 8,
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _download(url: str, target: Path, max_bytes: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise OSError(f"asset exceeds max bytes: {url}")
        with tempfile.NamedTemporaryFile(delete=False, dir=target.parent) as handle:
            count = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                count += len(block)
                if count > max_bytes:
                    raise OSError(f"asset exceeds max bytes: {url}")
                handle.write(block)
            tmp = Path(handle.name)
    os.replace(tmp, target)


def _ensure_csv(value: str, cache_dir: Path, filename: str) -> Path:
    if value.startswith("http://") or value.startswith("https://"):
        target = cache_dir / filename
        if not target.is_file():
            _download(value, target, 256 * 1024 * 1024)
        return target
    path = Path(value).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _media_class(obj: dict[str, str]) -> str:
    text = " ".join(
        str(obj.get(key) or "").lower()
        for key in ("classification", "subclassification", "visualbrowserclassification", "medium")
    )
    if "photograph" in text or "albumen" in text or "silver print" in text:
        return "photograph"
    if "painting" in text or "oil on" in text or "tempera" in text:
        return "painting"
    if "drawing" in text or "watercolor" in text or "gouache" in text or "charcoal" in text:
        return "drawing_watercolor"
    if "print" in text or "etching" in text or "woodcut" in text or "engraving" in text or "lithograph" in text:
        return "print"
    if "sculpt" in text or "statue" in text or "relief" in text:
        return "sculpture"
    if any(term in text for term in ("textile", "ceramic", "porcelain", "stoneware", "metalwork", "silver", "bronze vessel")):
        return "textile_ceramic_metalwork"
    return "decorative_functional"


def _load_objects(path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            object_id = str(row.get("objectid") or "").strip()
            if object_id:
                result[object_id] = row
    return result


def _candidate_rows(images_path: Path, objects: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_objects: set[str] = set()
    with images_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for image in csv.DictReader(handle):
            if str(image.get("openaccess") or "").strip() != "1":
                continue
            if str(image.get("viewtype") or "").strip().lower() != "primary":
                continue
            object_id = str(image.get("depictstmsobjectid") or "").strip()
            if not object_id or object_id in seen_objects or object_id not in objects:
                continue
            obj = objects[object_id]
            base = str(image.get("iiifurl") or "").strip().rstrip("/")
            if not base:
                continue
            seen_objects.add(object_id)
            rows.append(
                {
                    "object_id": object_id,
                    "uuid": str(image.get("uuid") or "").strip(),
                    "title": str(obj.get("title") or "").strip(),
                    "accession": str(obj.get("accessionnum") or "").strip(),
                    "artist_attribution": str(obj.get("attribution") or "").strip(),
                    "medium": str(obj.get("medium") or "").strip(),
                    "classification": str(obj.get("classification") or "").strip(),
                    "media_class": _media_class(obj),
                    "object_uri": f"https://www.nga.gov/artworks/{object_id}",
                    "iiif_service_uri": base,
                    "rendition_uri": f"{base}/full/!1600,1600/0/default.jpg",
                    "source_width": int(image["width"]) if str(image.get("width") or "").isdigit() else None,
                    "source_height": int(image["height"]) if str(image.get("height") or "").isdigit() else None,
                    "assistive_text_source": str(image.get("assistivetext") or "").strip() or None,
                }
            )
    return rows


def _select(rows: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["media_class"]].append(row)
    selected: list[dict[str, Any]] = []
    chosen_ids: set[str] = set()
    for media_class, quota in MEDIA_QUOTAS.items():
        for row in grouped.get(media_class, [])[:quota]:
            selected.append(row)
            chosen_ids.add(row["object_id"])
    if len(selected) < target:
        for row in rows:
            if row["object_id"] in chosen_ids:
                continue
            selected.append(row)
            chosen_ids.add(row["object_id"])
            if len(selected) >= target:
                break
    return selected[:target]


def build_manifest(
    objects_path: Path,
    images_path: Path,
    output_dir: Path,
    *,
    target: int,
    download_assets: bool,
    max_asset_bytes: int,
) -> dict[str, Any]:
    objects = _load_objects(objects_path)
    selected = _select(_candidate_rows(images_path, objects), target)
    if len(selected) < target:
        raise ValueError(f"only {len(selected)} qualifying unique NGA objects available; target={target}")
    assets_dir = output_dir / "assets"
    records = []
    for index, row in enumerate(selected, 1):
        byte_digest = None
        byte_size = None
        local_path = None
        if download_assets:
            target_path = assets_dir / f"nga-{row['object_id']}-{row['uuid']}.jpg"
            if not target_path.is_file():
                _download(row["rendition_uri"], target_path, max_asset_bytes)
            byte_digest = _sha256(target_path)
            byte_size = target_path.stat().st_size
            local_path = target_path.relative_to(output_dir).as_posix()
        records.append(
            {
                "candidate_id": f"MM-NGA-AUTO-{index:03d}",
                "institution": "National Gallery of Art, Washington",
                **row,
                "rights": {
                    "designation": "NGA Open Access / no usage restriction",
                    "image_openaccess_flag": 1,
                    "rights_uri": IMAGE_RIGHTS_URI,
                    "dataset_uri": DATASET_URI,
                    "data_dictionary_uri": DATA_DICTIONARY_URI,
                    "cc0_reference_uri": CC0_URI,
                    "verification_state": "institutional_image_flag_verified_pending_human_rights_review",
                    "allowed_actions_candidate": [
                        "view", "analyse", "transform", "create_derivative", "cache", "export", "redistribute"
                    ],
                },
                "asset": {
                    "status": "downloaded_checksummed" if byte_digest else "uri_verified_download_pending",
                    "byte_sha256": byte_digest,
                    "byte_size": byte_size,
                    "local_path": local_path,
                    "format": "image/jpeg",
                    "derivative_lineage": {
                        "source_iiif_service": row["iiif_service_uri"],
                        "request": "full/!1600,1600/0/default.jpg",
                    },
                },
                "attribution_statement": f"National Gallery of Art, Washington — {row['title']} (object {row['object_id']})",
                "human_review": None,
            }
        )
    manifest = {
        "schema_version": "research-handoff.t111.nga-acquisition.v1",
        "status": "candidate_assets_prepared_human_review_required",
        "generated_at": _utc(),
        "source_tables": {
            "objects": {"uri": OBJECTS_URL, "sha256": _sha256(objects_path)},
            "published_images": {"uri": IMAGES_URL, "sha256": _sha256(images_path)},
        },
        "selection": {
            "target_unique_objects": target,
            "selected_unique_objects": len(records),
            "primary_only": True,
            "openaccess_flag_required": 1,
            "media_class_counts": dict(sorted(Counter(item["media_class"] for item in records).items())),
        },
        "records": records,
        "review_boundary": "No automated record is a final rights/grounding/discipline/adversarial human review.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "nga-candidate-manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objects", default=OBJECTS_URL)
    parser.add_argument("--published-images", default=IMAGES_URL)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target", type=int, default=80)
    parser.add_argument("--download-assets", action="store_true")
    parser.add_argument("--max-asset-bytes", type=int, default=25 * 1024 * 1024)
    args = parser.parse_args()
    try:
        cache = args.cache_dir.resolve()
        cache.mkdir(parents=True, exist_ok=True)
        objects = _ensure_csv(args.objects, cache, "nga-objects.csv")
        images = _ensure_csv(args.published_images, cache, "nga-published-images.csv")
        manifest = build_manifest(
            objects,
            images,
            args.output_dir.resolve(),
            target=args.target,
            download_assets=args.download_assets,
            max_asset_bytes=args.max_asset_bytes,
        )
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "PREPARATION_INCOMPLETE", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({
        "status": manifest["status"],
        "selected_unique_objects": manifest["selection"]["selected_unique_objects"],
        "media_class_counts": manifest["selection"]["media_class_counts"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
