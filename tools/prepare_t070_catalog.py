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
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

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
DISCIPLINE_CRITERIA_ID = "T070-DISCIPLINE-SOURCE-METADATA-V1"
OOD_CRITERIA_ID = "T070-OOD-DOMAIN-V1"
OOD_DOMAIN_ID = "technical-writing-held-out-v1"

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
_TECHNICAL_WRITING_TERMS = ("technical communication", "technical writing")
_INTERDISCIPLINARY_TERMS = (
    "interdisciplinary",
    "cross-disciplinary",
    "cross disciplinary",
    "multidisciplinary",
    "transdisciplinary",
    "digital humanities",
)
_PHILOSOPHY_TERMS = (
    "philosoph",
    "epistem",
    "hermeneutic",
    "posthuman",
    "political theory",
    "ethical theory",
    "normative ethics",
    "metaethic",
    "applied ethics",
    "bioethic",
)
_PSYCHOLOGY_TERMS = (
    "psycholog",
    "psychoanal",
    "cognitive",
    "mental health",
    "behavior",
    "behaviour",
    "pathological body",
    "medieval brain",
    "audience psychology",
)
_HUMANITIES_TERMS = (
    "anthropolog",
    "sociolog",
    "humanities",
    "literature",
    "literary",
    "language",
    "linguistic",
    "culture",
    "cultural",
    "history",
    "historical",
    "education",
    "pedagog",
    "politic",
    "society",
    "religion",
    "gender",
    "migration",
    "media",
    "communication",
    "rhetoric",
    "discourse",
    "writing",
    "textual",
    "medieval",
)
_ART_CRITICISM_TERMS = (
    "art criticism",
    "criticism",
    "critical",
    "cinema",
    "film",
    "visual culture",
    "cartoon",
    "visual rhetor",
    "game studies",
)
_ART_HISTORY_TERMS = (
    "art history",
    "archaeolog",
    "museum",
    "museolog",
    "heritage",
    "iconograph",
    "curat",
    "painting",
    "sculptur",
    "visual art",
    "artwork",
    "gallery",
    "mumm",
    "paleopath",
    "zooarchaeolog",
    "material culture",
    "ancient egypt",
    "architecture",
    "architectural history",
    "manuscript illumination",
    "conservation",
)
_DISCIPLINE_RULE_TERMS = {
    "art_criticism": _ART_CRITICISM_TERMS,
    "art_history": _ART_HISTORY_TERMS,
    "engineering": (
        "engineering",
        "engineer",
        "technology",
        "technical",
        "computer science",
        "software",
        "algorithm",
    ),
    "humanities": _HUMANITIES_TERMS,
    "interdisciplinary": _INTERDISCIPLINARY_TERMS,
    "materials_science": (
        "materials science",
        "material",
        "materials",
        "metallurg",
        "polymer",
        "ceramic",
        "composite",
        "nanomaterial",
    ),
    "philosophy": _PHILOSOPHY_TERMS,
    "psychology": _PSYCHOLOGY_TERMS,
    "technical_writing": _TECHNICAL_WRITING_TERMS,
}
_DISCIPLINE_SUBJECT_CODES = {
    "art_criticism": _ARTS,
    "art_history": _ARTS,
    "engineering": _ENGINEERING,
    "humanities": {"SOCI", "ECON", "BUSI", "DECI"},
    "interdisciplinary": {"MULT"},
    "materials_science": _MATERIALS,
    "philosophy": set(),
    "psychology": _PSYCHOLOGY,
    "technical_writing": set(),
}
_ELSEVIER_INTERDISCIPLINARY_TERMS = (
    "interdisciplinary",
    "cross-disciplinary",
    "multidisciplinary",
    "transdisciplinary",
)
_ELSEVIER_PHILOSOPHY_TERMS = (
    "philosoph",
    "epistem",
    "hermeneutic",
    "ethical theory",
    "normative ethics",
    "metaethic",
    "applied ethics",
    "bioethic",
)
_ELSEVIER_PSYCHOLOGY_TERMS = ("psych",)
_ELSEVIER_ART_CRITICISM_TERMS = (
    "criticism",
    "critical",
    "cinema",
    "film",
    "visual culture",
)
_OLH_INTERDISCIPLINARY_TERMS = (
    "interdisciplinary",
    "cross-disciplinary",
    "cross disciplinary",
    "digital humanities",
)
_OLH_PHILOSOPHY_TERMS = (
    "philosoph",
    "posthuman",
    "political theory",
    "ethical theory",
    "normative ethics",
    "metaethic",
    "applied ethics",
    "bioethic",
)
_OLH_PSYCHOLOGY_TERMS = (
    "psychoanal",
    "pathological body",
    "medieval brain",
    "audience psychology",
)
_OLH_ART_HISTORY_TERMS = (
    "visual art",
    "museum",
    "iconograph",
    "art history",
)
_OLH_ART_HISTORY_CURATORIAL_TERM = "curat"
_OLH_ART_HISTORY_CONTEXT_TERMS = (
    "archaeolog",
    "architectur",
    "exhibition",
    "gallery",
    "heritage",
    "iconograph",
    "manuscript",
    "museum",
    "painting",
    "sculptur",
)
_OLH_ART_CRITICISM_TERMS = (
    "art criticism",
    "cinema",
    "film",
    "cartoon",
    "visual rhetor",
    "game studies",
)
_OLH_HUMANITIES_TERMS = (
    "language",
    "writing",
    "textual",
    "literature",
    "culture",
    "medieval",
    "history",
)
_ELSEVIER_DISCIPLINE_RULES = {
    "art_criticism": (_ELSEVIER_ART_CRITICISM_TERMS, _ARTS),
    "art_history": (_ART_HISTORY_TERMS, _ARTS),
    "engineering": ((), _ENGINEERING),
    "humanities": ((), {"SOCI", "ECON", "BUSI", "DECI"}),
    "interdisciplinary": (_ELSEVIER_INTERDISCIPLINARY_TERMS, {"MULT"}),
    "materials_science": ((), _MATERIALS),
    "philosophy": (_ELSEVIER_PHILOSOPHY_TERMS, set()),
    "psychology": (_ELSEVIER_PSYCHOLOGY_TERMS, _PSYCHOLOGY),
    "technical_writing": (_TECHNICAL_WRITING_TERMS, set()),
}
_OLH_DISCIPLINE_RULES = {
    "art_criticism": (_OLH_ART_CRITICISM_TERMS, set()),
    "art_history": (
        _OLH_ART_HISTORY_TERMS + (_OLH_ART_HISTORY_CURATORIAL_TERM,),
        set(),
    ),
    "humanities": (_OLH_HUMANITIES_TERMS, set()),
    "interdisciplinary": (_OLH_INTERDISCIPLINARY_TERMS, set()),
    "philosophy": (_OLH_PHILOSOPHY_TERMS, set()),
    "psychology": (_OLH_PSYCHOLOGY_TERMS, set()),
    "technical_writing": (_TECHNICAL_WRITING_TERMS, set()),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
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
        for attempt in range(8):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.5)
    finally:
        temporary.unlink(missing_ok=True)


def _strip_markup(value: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(value or "")))).strip()


def _term_matches(text: str, term: str) -> bool:
    """Match a lexical rule at a token boundary while preserving stems."""

    return re.search(rf"(?<![a-z0-9]){re.escape(term.casefold())}", text.casefold()) is not None


def _normalise_doi(value: Any) -> str | None:
    raw = str(value or "").strip()
    raw = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.I).rstrip(".")
    return raw or None


def _olh_article_doi(content_path: Path) -> str | None:
    """Read the article-level DOI declared by the acquired OLH XML."""

    try:
        root = ET.parse(content_path).getroot()
    except (OSError, ET.ParseError):
        return None
    for element in root.iter():
        tag = str(element.tag).rsplit("}", 1)[-1]
        pub_id_type = next(
            (
                str(value)
                for key, value in element.attrib.items()
                if str(key).rsplit("}", 1)[-1] == "pub-id-type"
            ),
            "",
        )
        if tag != "article-id" or pub_id_type.casefold() != "doi":
            continue
        doi = _normalise_doi("".join(element.itertext()))
        if doi:
            return doi
    return None


def _keywords(metadata: dict[str, Any]) -> str:
    values = metadata.get("keywords", [])
    if not isinstance(values, list):
        values = []
    return " ".join(str(value) for value in values)


def _subject_codes(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        values = value
    elif value:
        values = [value]
    else:
        values = []
    return sorted({str(item).strip().upper() for item in values if str(item).strip()})


def _evidence_text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return " ".join(_evidence_text(item) for item in value)
    return _strip_markup(value)


def _discipline_evidence(
    *,
    discipline: str,
    fields: dict[str, Any],
    subject_codes: list[str],
    rule_terms: tuple[str, ...] | None = None,
    rule_subject_codes: set[str] | None = None,
    fallback_basis: str | None = None,
) -> dict[str, Any]:
    rule_terms = tuple(
        _DISCIPLINE_RULE_TERMS.get(discipline, ()) if rule_terms is None else rule_terms
    )
    text_by_field = {name: _evidence_text(value).casefold() for name, value in fields.items()}
    matched_evidence = {
        name: sorted({term for term in rule_terms if _term_matches(text, term)})
        for name, text in text_by_field.items()
        if any(_term_matches(text, term) for term in rule_terms)
    }
    normalised_subject_codes = _subject_codes(subject_codes)
    rule_subject_codes = sorted(
        _DISCIPLINE_SUBJECT_CODES.get(discipline, set())
        if rule_subject_codes is None
        else rule_subject_codes
    )
    matched_terms = sorted({term for terms in matched_evidence.values() for term in terms})
    matched_subject_codes = sorted(set(normalised_subject_codes).intersection(rule_subject_codes))
    if matched_subject_codes and "subjareas" in fields:
        matched_evidence["subjareas"] = matched_subject_codes
    evidence = {
        "criteria_id": DISCIPLINE_CRITERIA_ID,
        "review_status": "pending_human_review",
        "evidence_fields": list(fields),
        "subject_codes": normalised_subject_codes,
        "rule_subject_codes": rule_subject_codes,
        "matched_subject_codes": matched_subject_codes,
        "rule_terms": list(rule_terms),
        "matched_terms": matched_terms,
        "matched_evidence": matched_evidence,
        "classifier_predicate": {
            "text_any": list(rule_terms),
            "subject_any": rule_subject_codes,
        },
    }
    if fallback_basis is not None and not matched_terms and not matched_subject_codes:
        evidence["fallback_basis"] = fallback_basis
    return evidence


def classify_elsevier(metadata: dict[str, Any]) -> str | None:
    subjects = set(_subject_codes(metadata.get("subjareas")))
    text = f"{metadata.get('title', '')} {_keywords(metadata)}".lower()
    if any(_term_matches(text, token) for token in _TECHNICAL_WRITING_TERMS):
        return "technical_writing"
    if (
        any(_term_matches(text, token) for token in _ELSEVIER_INTERDISCIPLINARY_TERMS)
        or "MULT" in subjects
    ):
        return "interdisciplinary"
    if any(_term_matches(text, token) for token in _ELSEVIER_PHILOSOPHY_TERMS):
        return "philosophy"
    if (
        any(_term_matches(text, token) for token in _ELSEVIER_PSYCHOLOGY_TERMS)
        or subjects & _PSYCHOLOGY
    ):
        return "psychology"
    if subjects & _ARTS:
        if any(_term_matches(text, token) for token in _ELSEVIER_ART_CRITICISM_TERMS):
            return "art_criticism"
        if any(_term_matches(text, token) for token in _ART_HISTORY_TERMS):
            return "art_history"
        return None
    if subjects & _ENGINEERING:
        return "engineering"
    if subjects & _MATERIALS:
        return "materials_science"
    if subjects & {"SOCI", "ECON", "BUSI", "DECI"}:
        return "humanities"
    return None


def classify_olh(article: dict[str, Any]) -> str:
    text = " ".join(
        _evidence_text(article.get(key)) for key in ("title", "section", "abstract")
    ).lower()
    if any(_term_matches(text, token) for token in _TECHNICAL_WRITING_TERMS):
        return "technical_writing"
    if any(_term_matches(text, token) for token in _OLH_INTERDISCIPLINARY_TERMS):
        return "interdisciplinary"
    if any(_term_matches(text, token) for token in _OLH_PHILOSOPHY_TERMS):
        return "philosophy"
    if any(_term_matches(text, token) for token in _OLH_PSYCHOLOGY_TERMS):
        return "psychology"
    if _matches_olh_art_history(text):
        return "art_history"
    if any(_term_matches(text, token) for token in _OLH_ART_CRITICISM_TERMS):
        return "art_criticism"
    if any(_term_matches(text, token) for token in _OLH_HUMANITIES_TERMS):
        return "humanities"
    return "humanities"


def _matches_olh_art_history(text: str) -> bool:
    if any(_term_matches(text, token) for token in _OLH_ART_HISTORY_TERMS):
        return True
    return _term_matches(text, _OLH_ART_HISTORY_CURATORIAL_TERM) and any(
        _term_matches(text, token) for token in _OLH_ART_HISTORY_CONTEXT_TERMS
    )


def _semantic_assignment(year: int | None, discipline: str, ordinal: int) -> dict[str, Any]:
    del ordinal
    # The held-out designation is a declared domain policy, not a hash bucket:
    # the complete technical-writing domain is withheld. Human review remains
    # required before any candidate is promoted to a locked evaluation split.
    if discipline == "technical_writing":
        return {
            "partition": "ood",
            "criteria_id": OOD_CRITERIA_ID,
            "catalog_declared_held_out_domain": True,
            "domain_id": OOD_DOMAIN_ID,
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


def _license(
    *,
    rights_uri: str,
    evidence_uri: str,
    basis: str,
    verification: str = "article_level_verified",
) -> dict[str, str]:
    return {
        "spdx": "CC-BY-4.0",
        "uri": CC_BY_URI,
        "version": "4.0",
        "article_rights_uri": rights_uri,
        "verification": verification,
        "evidence_uri": evidence_uri,
        "verification_basis": basis,
    }


def _elsevier_licence(metadata: dict[str, Any]) -> dict[str, str]:
    """Return article-level rights only when the archive supplies them explicitly.

    The pinned dataset's ``openaccess=Full`` field is an acquisition lead, not
    article-level rights evidence.  Keep that lead visible in the catalog, but
    make the resulting record fail the runtime rights gate until an
    article-specific licence and notice are supplied.
    """

    article_license = metadata.get("article_license")
    if isinstance(article_license, dict):
        rights_uri = str(article_license.get("article_rights_uri") or "").strip()
        evidence_uri = str(article_license.get("evidence_uri") or "").strip()
        if (
            str(article_license.get("spdx") or "").strip().upper() == "CC-BY-4.0"
            and rights_uri
            and evidence_uri
        ):
            return _license(
                rights_uri=rights_uri,
                evidence_uri=evidence_uri,
                basis="explicit article-level licence record and article rights notice",
            )

    return _license(
        rights_uri="",
        evidence_uri="https://elsevier.digitalcommonsdata.com/datasets/zm33cdndxs/2",
        basis=(
            "dataset-level openaccess=Full marker only; article-level licence or notice "
            "was not inspected and candidate generation is blocked"
        ),
        verification="unverified",
    )


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
    rule_terms, rule_subject_codes = _ELSEVIER_DISCIPLINE_RULES[discipline]
    authors = []
    for author in metadata.get("authors", []):
        if isinstance(author, dict):
            name = " ".join(str(author.get(key) or "").strip() for key in ("first", "last")).strip()
            if name:
                authors.append(name)
    if not authors:
        return None
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
        "discipline_assignment": _discipline_evidence(
            discipline=discipline,
            fields={
                "title": metadata.get("title"),
                "keywords": _keywords(metadata),
                "subjareas": _subject_codes(metadata.get("subjareas")),
            },
            subject_codes=_subject_codes(metadata.get("subjareas")),
            rule_terms=rule_terms,
            rule_subject_codes=rule_subject_codes,
        ),
        "licence": _elsevier_licence(metadata),
        "attribution": f"Elsevier OA CC-BY Corpus, {metadata.get('title') or doc_id}, {', '.join(authors)}",
        "allowed_uses": ["candidate_generation", "human_annotation", "provenance_audit"],
        "third_party": {
            "status": "warning",
            "warning": "The dataset licence warns that further permission may be required for third-party content within an article.",
        },
        "semantic_split": _semantic_assignment(year, discipline, ordinal),
        "expected_sha256": None,
    }


def _olh_author_names(value: Any) -> list[str]:
    """Extract every bibliographic author name while preserving source order."""

    names: list[str] = []
    seen: set[str] = set()

    def add(candidate: Any) -> None:
        if isinstance(candidate, (dict, list, tuple, set)):
            return
        name = _strip_markup(candidate)
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    def collect(author: Any) -> None:
        if isinstance(author, (list, tuple, set)):
            for item in author:
                collect(item)
            return
        if isinstance(author, str):
            raw = author.strip()
            if raw[:1] in {"{", "["}:
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
                if parsed is not None:
                    collect(parsed)
                    return
            add(raw)
            return
        if not isinstance(author, dict):
            return

        direct_name = next(
            (author.get(key) for key in ("name", "full_name", "display_name") if author.get(key)),
            None,
        )
        if direct_name is not None:
            add(direct_name)
        else:
            components = [
                author.get(key)
                for key in (
                    "first_name",
                    "given_name",
                    "first",
                    "last_name",
                    "family_name",
                    "last",
                    "surname",
                )
                if author.get(key)
            ]
            if components:
                add(" ".join(_strip_markup(component) for component in components))

        for key in ("author", "person", "creator", "authors"):
            nested = author.get(key)
            if isinstance(nested, (dict, list, tuple, set)):
                collect(nested)

    collect(value)
    return names


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
    authors = _olh_author_names(article.get("frozenauthors"))
    if not authors:
        authors = _olh_author_names(article.get("authors"))
    if not authors:
        return None
    doi = _olh_article_doi(content_path)
    if not doi:
        return None
    year = None
    match = re.match(r"^(\d{4})", str(article.get("date_published") or ""))
    if match:
        year = int(match.group(1))
    rule_terms, rule_subject_codes = _OLH_DISCIPLINE_RULES[discipline]
    return {
        "source_id": f"olh-{article_id}",
        "doi": doi,
        "stable_uri": article_uri,
        "content_uri": str(content_path.resolve()),
        "title": _strip_markup(article.get("title")) or f"OLH article {article_id}",
        "authors": authors,
        "publisher": "Open Library of Humanities",
        "publication_date": str(article.get("date_published") or "undated"),
        "disciplines": [discipline],
        "discipline_assignment": _discipline_evidence(
            discipline=discipline,
            fields={
                "title": article.get("title"),
                "section": article.get("section"),
                "abstract": article.get("abstract"),
            },
            subject_codes=[],
            rule_terms=rule_terms,
            rule_subject_codes=rule_subject_codes,
            fallback_basis=(
                "official_olh_humanities_scope" if discipline == "humanities" else None
            ),
        ),
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
        # A path-only cache cannot prove that an existing byte copy came from
        # the current API galley. Reacquire it every run so current metadata
        # never binds to stale XML; the runtime acquisition lane remains
        # responsible for immutable digest reuse after this preparation step.
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
                "criteria_id": OOD_CRITERIA_ID,
                "definition": "catalog_declared_held_out_domain is true",
            },
        },
        "discipline_assignment_policy": {
            "criteria_id": DISCIPLINE_CRITERIA_ID,
            "version": "1.0.0",
            "review_status": "pending_human_review",
            "definition": (
                "Source-level candidate discipline is assigned only from official subject metadata "
                "and auditable title/keyword evidence; unresolved records are excluded from the catalog."
            ),
        },
        "provenance": {
            "elsevier_dataset_doi": ELSEVIER_DOI,
            "elsevier_archive_uri": ELSEVIER_ARCHIVE_URI,
            "elsevier_archive_sha256": archive_digest,
            "elsevier_archive_copy_uri": archive_path.as_uri(),
            "olh_api_uri": OLH_API_URI,
            "rights_policy": (
                "CC BY 4.0 only; Elsevier dataset-level open-access markers remain "
                "unresolved until article-level licence/notice evidence is supplied; "
                "OLH article API licence records are retained for independent review"
            ),
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
