#!/usr/bin/env python3
"""Prepare a real, rights-screened T070 source catalog outside the Git checkout.

The script never creates labels.  It verifies the pinned Elsevier v2 archive,
extracts selected article JSON bytes into a machine-local cache, discovers
article-level CC BY records from the official OLH API, and writes a catalog for
``acquire_citation_candidates.py``.  The latter remains responsible for the
final byte hashes and unlabelled packet generation.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ELSEVIER_DOI = "10.17632/zm33cdndxs.2"
ELSEVIER_ARCHIVE_URI = (
    "https://elsevier.digitalcommonsdata.com/public-api/zip/zm33cdndxs/download/2"
)
ELSEVIER_ARCHIVE_SHA256 = "877ac30109eb1333965a1c912e7e1b7b422542990cdc5b4658feb8d978d5bce2"
CC_BY_URI = "https://creativecommons.org/licenses/by/4.0/"
OLH_API_URI = "https://olh.openlibhums.org/api/articles/"
OLH_ARTICLE_URI = "https://olh.openlibhums.org/article/id/{article_id}/"
OLH_USER_AGENT = "SWOS-T070-citation-acquisition/1.0 (research)"
MAX_ARTICLE_BYTES = 50 * 1024 * 1024
SEMANTIC_POLICY_VERSION = "2.0.0"
TEMPORAL_CRITERIA_ID = "T070-TEMPORAL-LATER-YEAR-V1"
TEMPORAL_START_YEAR = 2020
TEMPORAL_DEFINITION = "publication_year >= 2020 and catalog_declared_held_out_domain is not true"

DISCIPLINES = (
    "art_history",
    "art_criticism",
    "engineering",
    "humanities",
    "interdisciplinary",
    "materials_science",
    "philosophy",
    "psychology",
    "technical_writing",
)

_ENGINEERING = {"ENGI", "CENG", "COMP", "ENER", "MATH"}
_MATERIALS = {"MATE", "CHEM", "PHYS"}
_PSYCHOLOGY = {"PSYC"}
_ARTS = {"ARTS"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _download(url: str, path: Path, *, max_bytes: int = MAX_ARTICLE_BYTES) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": OLH_USER_AGENT})
    try:
        with (
            urllib.request.urlopen(request, timeout=120) as response,
            temporary.open("wb") as handle,
        ):
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise OSError(f"article content exceeds resource limit: {max_bytes} bytes")
            count = 0
            for block in iter(lambda: response.read(1024 * 1024), b""):
                count += len(block)
                if count > max_bytes:
                    raise OSError(f"article content exceeds resource limit: {max_bytes} bytes")
                handle.write(block)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _strip_markup(value: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(value or "")))).strip()


def _normalise_doi(value: Any) -> str | None:
    raw = str(value or "").strip()
    raw = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.I).rstrip(".")
    return raw or None


def _keywords(metadata: dict[str, Any]) -> str:
    values = metadata.get("keywords", [])
    if not isinstance(values, list):
        values = []
    return " ".join(str(value) for value in values)


def classify_elsevier(metadata: dict[str, Any]) -> str | None:
    subjects = {str(value).upper() for value in metadata.get("subjareas", [])}
    text = f"{metadata.get('title', '')} {_keywords(metadata)}".lower()
    if any(
        token in text
        for token in (
            "technical communication",
            "technical writing",
            "documentation",
            "documentation",
        )
    ):
        return "technical_writing"
    if (
        any(
            token in text
            for token in (
                "interdisciplinary",
                "cross-disciplinary",
                "multidisciplinary",
                "transdisciplinary",
            )
        )
        or "MULT" in subjects
    ):
        return "interdisciplinary"
    if "philosoph" in text or any(
        token in text for token in ("epistem", "ontology", "ethic", "hermeneutic")
    ):
        return "philosophy"
    if "psych" in text or subjects & _PSYCHOLOGY:
        return "psychology"
    if subjects & _ARTS:
        if any(
            token in text for token in ("criticism", "critical", "cinema", "film", "visual culture")
        ):
            return "art_criticism"
        return "art_history"
    if subjects & _ENGINEERING:
        return "engineering"
    if subjects & _MATERIALS:
        return "materials_science"
    if subjects & {"SOCI", "ECON", "BUSI", "DECI"}:
        return "humanities"
    return None


def classify_olh(article: dict[str, Any]) -> str:
    text = " ".join(str(article.get(key) or "") for key in ("title", "section", "abstract")).lower()
    if any(
        token in text for token in ("technical communication", "technical writing", "documentation")
    ):
        return "technical_writing"
    if any(
        token in text
        for token in (
            "interdisciplinary",
            "cross-disciplinary",
            "cross disciplinary",
            "digital humanities",
        )
    ):
        return "interdisciplinary"
    if any(
        token in text
        for token in ("philosoph", "posthuman", "political theory", "ethic", "ontology")
    ):
        return "philosophy"
    if any(
        token in text
        for token in ("psychoanal", "pathological body", "medieval brain", "audience psychology")
    ):
        return "psychology"
    if any(
        token in text
        for token in ("visual art", "museum", "curat", "iconograph", "art history", "collections")
    ):
        return "art_history"
    if any(
        token in text
        for token in ("art criticism", "cinema", "film", "cartoon", "visual rhetor", "game studies")
    ):
        return "art_criticism"
    if any(
        token in text
        for token in (
            "language",
            "writing",
            "textual",
            "literature",
            "culture",
            "medieval",
            "history",
        )
    ):
        return "humanities"
    return "humanities"


def _semantic_assignment(year: int | None, discipline: str, ordinal: int) -> dict[str, Any]:
    # The held-out designation is a declared domain policy, not a hash bucket:
    # technical-writing sources are withheld as a named OOD domain for every
    # third eligible modern source. Human review may revise the domain policy.
    if discipline == "technical_writing" and ordinal % 3 == 0:
        return {
            "partition": "ood",
            "criteria_id": "T070-OOD-DOMAIN-V1",
            "catalog_declared_held_out_domain": True,
            "domain_id": "technical-writing-held-out-v1",
        }
    if year is not None and year >= TEMPORAL_START_YEAR:
        return {
            "partition": "temporal",
            "criteria_id": TEMPORAL_CRITERIA_ID,
            "publication_year": year,
            "start_year": TEMPORAL_START_YEAR,
            "catalog_declared_held_out_domain": False,
        }
    return {
        "partition": "in_domain",
        "criteria_id": "T070-IN-DOMAIN-V1",
        "publication_year": year,
        "catalog_declared_held_out_domain": False,
    }


def _license(*, rights_uri: str, evidence_uri: str, basis: str) -> dict[str, str]:
    return {
        "spdx": "CC-BY-4.0",
        "uri": CC_BY_URI,
        "version": "4.0",
        "article_rights_uri": rights_uri,
        "verification": "article_level_verified",
        "evidence_uri": evidence_uri,
        "verification_basis": basis,
    }


def _elsevier_entry(
    data: dict[str, Any], content_path: Path, ordinal: int
) -> dict[str, Any] | None:
    metadata = data.get("metadata")
    if not isinstance(metadata, dict) or str(metadata.get("openaccess") or "").casefold() != "full":
        return None
    discipline = classify_elsevier(metadata)
    if discipline is None:
        return None
    doc_id = str(data.get("docId") or "").strip()
    if not doc_id:
        return None
    doi = _normalise_doi(metadata.get("doi"))
    stable_uri = f"https://doi.org/{doi}" if doi else f"https://data.elsevier.com/article/{doc_id}"
    year = metadata.get("pub_year")
    year = int(year) if isinstance(year, int) and not isinstance(year, bool) else None
    authors = []
    for author in metadata.get("authors", []):
        if isinstance(author, dict):
            name = " ".join(str(author.get(key) or "").strip() for key in ("first", "last")).strip()
            if name:
                authors.append(name)
    authors = authors or ["Elsevier OA CC-BY Corpus contributor"]
    return {
        "source_id": f"elsevier-{doc_id}",
        "doi": doi,
        "stable_uri": stable_uri,
        "content_uri": str(content_path.resolve()),
        "title": str(metadata.get("title") or doc_id).strip(),
        "authors": authors,
        "publisher": "Elsevier OA CC-BY Corpus",
        "publication_date": f"{year:04d}-01-01" if year else "undated",
        "disciplines": [discipline],
        "licence": _license(
            rights_uri=stable_uri,
            evidence_uri="https://elsevier.digitalcommonsdata.com/datasets/zm33cdndxs/2",
            basis="official v2 oa-ccby article ID list plus metadata openaccess=Full; embedded third-party material remains a human-review warning",
        ),
        "attribution": f"Elsevier OA CC-BY Corpus, {metadata.get('title') or doc_id}, {', '.join(authors)}",
        "allowed_uses": ["candidate_generation", "human_annotation", "provenance_audit"],
        "third_party": {
            "status": "warning",
            "warning": "The dataset licence warns that further permission may be required for third-party content within an article.",
        },
        "semantic_split": _semantic_assignment(year, discipline, ordinal),
        "expected_sha256": None,
    }


def _olh_entry(article: dict[str, Any], content_path: Path, ordinal: int) -> dict[str, Any] | None:
    article_id = article.get("pk")
    licence = article.get("license")
    if not article_id or not isinstance(licence, dict) or licence.get("short_name") != "CC BY 4.0":
        return None
    galleys = article.get("galleys")
    if not isinstance(galleys, list):
        return None
    xml_galleys = [item for item in galleys if isinstance(item, dict) and item.get("type") == "xml"]
    if not xml_galleys:
        return None
    article_uri = OLH_ARTICLE_URI.format(article_id=article_id)
    discipline = classify_olh(article)
    author = article.get("frozenauthors")
    authors = []
    if isinstance(author, dict):
        name = " ".join(
            str(author.get(key) or "").strip() for key in ("first_name", "last_name")
        ).strip()
        if name:
            authors.append(name)
    authors = authors or ["Open Library of Humanities author"]
    year = None
    match = re.match(r"^(\d{4})", str(article.get("date_published") or ""))
    if match:
        year = int(match.group(1))
    return {
        "source_id": f"olh-{article_id}",
        "doi": f"10.16995/olh.{article_id}",
        "stable_uri": article_uri,
        "content_uri": str(content_path.resolve()),
        "title": _strip_markup(article.get("title")) or f"OLH article {article_id}",
        "authors": authors,
        "publisher": "Open Library of Humanities",
        "publication_date": str(article.get("date_published") or "undated"),
        "disciplines": [discipline],
        "licence": _license(
            rights_uri=article_uri,
            evidence_uri=f"{OLH_API_URI}{article_id}/",
            basis="official article API returns CC BY 4.0 and the XML galley is the acquired article copy",
        ),
        "attribution": f"{', '.join(authors)}, {_strip_markup(article.get('title'))}, Open Library of Humanities",
        "allowed_uses": ["candidate_generation", "human_annotation", "provenance_audit"],
        "third_party": {
            "status": "warning",
            "warning": "Review article-level notices for separately licensed third-party material before final admission.",
        },
        "semantic_split": _semantic_assignment(year, discipline, ordinal),
        "expected_sha256": None,
        "content_download_uri": str(xml_galleys[0].get("path") or ""),
    }


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": OLH_USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON endpoint did not return an object: {url}")
    return payload


def _discover_olh() -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = _fetch_json(f"{OLH_API_URI}?limit=100&offset={offset}")
        results = payload.get("results")
        if not isinstance(results, list):
            raise ValueError("OLH API results are not a list")
        articles.extend(item for item in results if isinstance(item, dict))
        if not payload.get("next"):
            break
        offset += 100
    return articles


def prepare_catalog(
    archive_path: Path,
    cache_dir: Path,
    catalog_path: Path,
    *,
    per_discipline: int = 45,
    olh_per_discipline: int = 45,
) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    cache_dir = cache_dir.resolve()
    catalog_path = catalog_path.resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    archive_digest = _sha256(archive_path)
    if archive_digest != ELSEVIER_ARCHIVE_SHA256:
        raise ValueError(f"Elsevier v2 archive SHA-256 mismatch: {archive_digest}")
    if per_discipline <= 0 or olh_per_discipline <= 0:
        raise ValueError("source quotas must be positive")
    cache_dir.mkdir(parents=True, exist_ok=True)
    elsevier_dir = cache_dir / "elsevier-json"
    olh_dir = cache_dir / "olh-xml"
    selected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    with zipfile.ZipFile(archive_path) as outer:
        with (
            outer.open("json-articals.zip") as nested_stream,
            zipfile.ZipFile(nested_stream) as nested,
        ):
            for info in nested.infolist():
                if info.is_dir():
                    continue
                try:
                    data = json.loads(nested.read(info).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if not isinstance(data, dict):
                    continue
                metadata = data.get("metadata")
                discipline = (
                    classify_elsevier(metadata)
                    if isinstance(metadata, dict)
                    and str(metadata.get("openaccess") or "").casefold() == "full"
                    else None
                )
                if discipline is None or len(selected[discipline]) >= per_discipline:
                    continue
                doc_id = str(data.get("docId") or "").strip()
                source_id = f"elsevier-{doc_id}"
                if not doc_id or source_id in seen_ids:
                    continue
                target = elsevier_dir / f"{doc_id}.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(nested.read(info))
                entry = _elsevier_entry(data, target, len(selected[discipline]))
                if entry is not None:
                    selected[discipline].append(entry)
                    seen_ids.add(source_id)
    olh_articles = _discover_olh()
    for article in olh_articles:
        discipline = classify_olh(article)
        olh_count = len(
            [item for item in selected[discipline] if item["source_id"].startswith("olh-")]
        )
        if olh_count >= olh_per_discipline:
            continue
        article_id = article.get("pk")
        galleys = article.get("galleys")
        xml_galleys = [
            item for item in galleys or [] if isinstance(item, dict) and item.get("type") == "xml"
        ]
        if not article_id or not xml_galleys:
            continue
        target = olh_dir / f"{article_id}.xml"
        if not target.is_file():
            _download(str(xml_galleys[0].get("path")), target, max_bytes=MAX_ARTICLE_BYTES)
        entry = _olh_entry(article, target, len(selected[discipline]))
        if entry is not None:
            selected[discipline].append(entry)
            seen_ids.add(entry["source_id"])

    sources = [source for discipline in DISCIPLINES for source in selected.get(discipline, [])]
    counts = Counter(source["disciplines"][0] for source in sources)
    catalog = {
        "schema_version": "2.0.0",
        "catalog_type": "citation_source_candidate_catalog",
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "semantic_split_policy": {
            "version": SEMANTIC_POLICY_VERSION,
            "temporal": {
                "criteria_id": TEMPORAL_CRITERIA_ID,
                "definition": TEMPORAL_DEFINITION,
                "start_year": TEMPORAL_START_YEAR,
            },
            "ood": {
                "criteria_id": "T070-OOD-DOMAIN-V1",
                "definition": "catalog_declared_held_out_domain is true",
            },
        },
        "provenance": {
            "elsevier_dataset_doi": ELSEVIER_DOI,
            "elsevier_archive_uri": ELSEVIER_ARCHIVE_URI,
            "elsevier_archive_sha256": archive_digest,
            "elsevier_archive_copy_uri": archive_path.as_uri(),
            "olh_api_uri": OLH_API_URI,
            "rights_policy": "CC BY 4.0 only; article-level licence and third-party warning retained for independent review",
        },
        "source_counts_by_discipline": dict(sorted(counts.items())),
        "sources": sources,
    }
    _write_atomic(catalog_path, catalog)
    return {
        "status": "CATALOG_READY_FOR_ACQUISITION",
        "catalog": str(catalog_path),
        "source_count": len(sources),
        "source_counts_by_discipline": dict(sorted(counts.items())),
        "elsevier_archive_sha256": archive_digest,
        "olh_articles_discovered": len(olh_articles),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elsevier-archive", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--per-discipline", type=int, default=45)
    parser.add_argument("--olh-per-discipline", type=int, default=45)
    args = parser.parse_args()
    try:
        result = prepare_catalog(
            args.elsevier_archive,
            args.cache_dir,
            args.catalog,
            per_discipline=args.per_discipline,
            olh_per_discipline=args.olh_per_discipline,
        )
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "CATALOG_INCOMPLETE", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
