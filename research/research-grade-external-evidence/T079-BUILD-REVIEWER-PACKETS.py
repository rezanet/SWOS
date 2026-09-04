#!/usr/bin/env python3
"""Build 108 reviewer-ready T079 source-diversity candidates from real metadata.

PREPARATION ONLY / NOT RELEASE EVIDENCE.

The builder uses OpenAlex as the primary CC0 metadata discovery substrate and
Crossref as a second provider for duplicate/fake-diversity cases. It deliberately
constructs the frozen T079 stress patterns, canonicalizes source families through
the production SWOS implementation, executes the production diversity metric,
and writes packets with `review: null`.

No human expected outcome, approval, competence, independence, methodology truth,
stance truth, or locked disposition is invented. Metadata that cannot be directly
observed from the provider is marked `unknown` or `inferred`, and therefore cannot
improve the Research Grade diversity score.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.models import canonical_digest  # noqa: E402
from swos_runtime.source_diversity import (  # noqa: E402
    DiversityRequirement,
    FamilyIdentityPolicy,
    canonicalize_source_families,
    measure_source_diversity,
)

OPENALEX = "https://api.openalex.org/works"
CROSSREF = "https://api.crossref.org/works/{doi}"
USER_AGENT = "SWOS-T079-diversity-preparation/1.0 (research; contact supplied by --mailto)"

DISCIPLINE_QUERIES = {
    "art_history": ["art history", "visual culture history", "museum collections history"],
    "art_criticism": [
        "art criticism",
        "aesthetic criticism visual art",
        "contemporary art criticism",
    ],
    "engineering": ["engineering design", "mechanical engineering", "civil engineering"],
    "humanities": ["humanities literature history", "cultural history", "literary studies"],
    "interdisciplinary": [
        "interdisciplinary research",
        "transdisciplinary research",
        "digital humanities interdisciplinary",
    ],
    "materials_science": [
        "materials science",
        "materials characterization",
        "materials engineering",
    ],
    "philosophy": ["philosophy epistemology", "philosophy ethics", "philosophy ontology"],
    "psychology": ["psychology cognition", "social psychology", "experimental psychology"],
    "technical_writing": [
        "technical writing",
        "technical communication",
        "documentation usability",
    ],
}

# Frozen 12-candidate allocation from T079-CANDIDATE-PACKET-SET.json.
ALLOCATION = {
    1: ("tuning_candidate", "balanced"),
    2: ("tuning_candidate", "balanced"),
    3: ("locked_candidate", "concentrated"),
    4: ("locked_candidate", "concentrated"),
    5: ("locked_candidate", "sparse"),
    6: ("locked_candidate", "narrow"),
    7: ("locked_candidate", "multilingual"),
    8: ("locked_candidate", "historical"),
    9: ("locked_candidate", "method_monoculture"),
    10: ("locked_candidate", "duplicate"),
    11: ("locked_candidate", "fake_diversity"),
    12: ("locked_candidate", "missing_strata"),
}

PREFIX = {
    "art_history": "DIV-ART-HISTORY",
    "art_criticism": "DIV-ART-CRITICISM",
    "engineering": "DIV-ENGINEERING",
    "humanities": "DIV-HUMANITIES",
    "interdisciplinary": "DIV-INTERDISCIPLINARY",
    "materials_science": "DIV-MATERIALS-SCIENCE",
    "philosophy": "DIV-PHILOSOPHY",
    "psychology": "DIV-PSYCHOLOGY",
    "technical_writing": "DIV-TECHNICAL-WRITING",
}


def utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent) as h:
        h.write(data)
        tmp = Path(h.name)
    os.replace(tmp, path)


def fetch_json(url: str, *, mailto: str, retries: int = 4) -> tuple[dict[str, Any], bytes]:
    headers = {"User-Agent": f"{USER_AGENT}; mailto={mailto}", "Accept": "application/json"}
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read()
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"JSON response is not an object: {url}")
            return payload, raw
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise OSError(f"metadata acquisition failed for {url}: {last}")


def norm_doi(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    return text or None


def decade(year: Any) -> str | None:
    try:
        value = int(year)
    except (TypeError, ValueError):
        return None
    return f"{value // 10 * 10}s"


def first_institution_country(work: dict[str, Any]) -> str | None:
    for authorship in work.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        for inst in authorship.get("institutions") or []:
            if isinstance(inst, dict) and inst.get("country_code"):
                return str(inst["country_code"]).upper()
    return None


def author_cluster(work: dict[str, Any]) -> str | None:
    names = []
    for authorship in work.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author") or {}
        if isinstance(author, dict) and author.get("display_name"):
            names.append(str(author["display_name"]).strip())
        if len(names) == 3:
            break
    return " | ".join(names) if names else None


def openalex_source(work: dict[str, Any], snapshot_uri: str) -> dict[str, Any]:
    doi = norm_doi(work.get("doi"))
    location = work.get("primary_location") or {}
    source = location.get("source") or {} if isinstance(location, dict) else {}
    oa = work.get("open_access") or {}
    values = {
        "publisher": source.get("host_organization_name") if isinstance(source, dict) else None,
        "venue": source.get("display_name") if isinstance(source, dict) else None,
        "author_cluster": author_cluster(work),
        "geography": first_institution_country(work),
        "language": work.get("language"),
        "period": decade(work.get("publication_year")),
        "methodology": None,
        "source_type": work.get("type"),
        "access_mode": "open_access"
        if isinstance(oa, dict) and oa.get("is_oa") is True
        else "closed_or_unknown",
        "stance": None,
    }
    states = {
        key: ("observed" if value not in (None, "") else "unknown") for key, value in values.items()
    }
    return {
        "source_id": "openalex-"
        + str(work.get("id") or canonical_digest(work)[:24]).rstrip("/").split("/")[-1],
        "provider": "openalex",
        "retrieved_uri": snapshot_uri,
        "canonical_work_id": f"doi:{doi}" if doi else str(work.get("id") or ""),
        "doi": doi,
        "title": str(work.get("display_name") or work.get("title") or "").strip(),
        **values,
        "metadata_status": states,
        "metadata_provenance": snapshot_uri,
        "provider_record_id": str(work.get("id") or ""),
    }


def crossref_source(doi: str, *, mailto: str, cache_dir: Path) -> dict[str, Any] | None:
    encoded = urllib.parse.quote(doi, safe="")
    url = CROSSREF.format(doi=encoded)
    cache = cache_dir / "crossref" / (hashlib.sha256(doi.encode()).hexdigest() + ".json")
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.is_file():
        raw = cache.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    else:
        payload, raw = fetch_json(url, mailto=mailto)
        cache.write_bytes(raw)
    message = payload.get("message")
    if not isinstance(message, dict):
        return None
    title_values = message.get("title") or []
    title = str(title_values[0] if isinstance(title_values, list) and title_values else "")
    container = message.get("container-title") or []
    venue = str(container[0] if isinstance(container, list) and container else "") or None
    publisher = str(message.get("publisher") or "") or None
    author_names = []
    for author in message.get("author") or []:
        if isinstance(author, dict):
            name = " ".join(str(author.get(k) or "").strip() for k in ("given", "family")).strip()
            if name:
                author_names.append(name)
        if len(author_names) == 3:
            break
    year = None
    for date_key in ("published-print", "published-online", "issued", "created"):
        value = message.get(date_key)
        if not isinstance(value, dict):
            continue
        parts = value.get("date-parts")
        try:
            year = int(parts[0][0])
            break
        except (TypeError, ValueError, IndexError):
            pass
    values = {
        "publisher": publisher,
        "venue": venue,
        "author_cluster": " | ".join(author_names) if author_names else None,
        "geography": None,
        "language": message.get("language"),
        "period": decade(year),
        "methodology": None,
        "source_type": message.get("type"),
        "access_mode": None,
        "stance": None,
    }
    return {
        "source_id": "crossref-" + hashlib.sha256(doi.encode()).hexdigest()[:24],
        "provider": "crossref",
        "retrieved_uri": url,
        "canonical_work_id": f"doi:{doi}",
        "doi": doi,
        "title": title,
        **values,
        "metadata_status": {
            key: ("observed" if val not in (None, "") else "unknown") for key, val in values.items()
        },
        "metadata_provenance": url,
        "provider_record_id": doi,
    }


def acquire_pool(
    discipline: str, *, mailto: str, cache_dir: Path, target: int = 90
) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in DISCIPLINE_QUERIES[discipline]:
        params = {
            "search": query,
            "per-page": "50",
            "select": "id,doi,display_name,title,publication_year,language,type,primary_location,open_access,authorships",
            "mailto": mailto,
        }
        url = OPENALEX + "?" + urllib.parse.urlencode(params)
        cache = cache_dir / "openalex" / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        cache.parent.mkdir(parents=True, exist_ok=True)
        if cache.is_file():
            raw = cache.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
        else:
            payload, raw = fetch_json(url, mailto=mailto)
            cache.write_bytes(raw)
        for work in payload.get("results") or []:
            if not isinstance(work, dict):
                continue
            source = openalex_source(work, url)
            key = str(source.get("canonical_work_id") or source["source_id"])
            if key in seen or not source.get("title"):
                continue
            seen.add(key)
            pool.append(source)
            if len(pool) >= target:
                return pool
    return pool


def known(source: dict[str, Any], key: str) -> bool:
    return source.get(key) not in (None, "") and source.get("metadata_status", {}).get(key) in {
        "observed",
        "externally_verified",
    }


def different_by(
    pool: Iterable[dict[str, Any]], dimensions: tuple[str, ...], limit: int
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    signatures: set[tuple[str, ...]] = set()
    for source in pool:
        sig = tuple(str(source.get(dim) or "<unknown>") for dim in dimensions)
        if sig in signatures:
            continue
        signatures.add(sig)
        selected.append(source)
        if len(selected) == limit:
            break
    return selected


def concentrated(pool: list[dict[str, Any]], dimension: str, limit: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in pool:
        if known(source, dimension):
            buckets[str(source[dimension])].append(source)
    if not buckets:
        return pool[:limit]
    dominant = max(buckets.values(), key=len)
    remainder = [source for source in pool if source not in dominant]
    return (dominant[: max(3, limit - 2)] + remainder[:2])[:limit]


def multilingual(pool: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in pool:
        if known(source, "language"):
            groups[str(source["language"])].append(source)
    languages = sorted(groups, key=lambda key: len(groups[key]), reverse=True)
    chosen: list[dict[str, Any]] = []
    for lang in languages[:4]:
        chosen.extend(groups[lang][: max(1, limit // max(2, len(languages[:4])))])
    for source in pool:
        if source not in chosen:
            chosen.append(source)
        if len(chosen) >= limit:
            break
    return chosen[:limit]


def historical(pool: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    rows = sorted(pool, key=lambda source: str(source.get("period") or "9999s"))
    return rows[:limit]


def duplicate_sources(
    base: list[dict[str, Any]], *, mailto: str, cache_dir: Path, limit: int
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source in base:
        result.append(source)
        doi = source.get("doi")
        if doi:
            try:
                second = crossref_source(str(doi), mailto=mailto, cache_dir=cache_dir)
            except OSError:
                second = None
            if second:
                result.append(second)
        if len(result) >= limit:
            break
    return result[:limit]


def make_claims(source_records: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    # Structural exposure fixtures only. These are not asserted scholarly truths.
    # The production diversity metric consumes source identity edges, so the
    # packet explicitly labels these as synthetic structural evaluation claims.
    claims = []
    unique = []
    seen_family_key = set()
    for source in source_records:
        key = str(source.get("canonical_work_id") or source["source_id"])
        if key in seen_family_key:
            continue
        seen_family_key.add(key)
        unique.append(source)
    for index, source in enumerate(unique):
        repeats = 1
        if category == "concentrated" and index == 0:
            repeats = 8
        for rep in range(repeats):
            claims.append(
                {
                    "claim_id": f"STRUCT-{index + 1:02d}-{rep + 1:02d}",
                    "claim_kind": "synthetic_structural_exposure_only",
                    "source_ids": [source["source_id"]],
                }
            )
    return claims


def requirement_for(
    packet_id: str, category: str, sources: list[dict[str, Any]]
) -> DiversityRequirement:
    dims = ("publisher", "venue", "geography", "language", "period", "source_type", "access_mode")
    required: dict[str, tuple[str, ...]] = {}
    counter_required = False
    if category == "multilingual":
        langs = tuple(dict.fromkeys(str(s["language"]) for s in sources if known(s, "language")))[
            :2
        ]
        if langs:
            required["language"] = langs
    elif category == "historical":
        periods = tuple(dict.fromkeys(str(s["period"]) for s in sources if known(s, "period")))[:2]
        if periods:
            required["period"] = periods
    elif category == "method_monoculture":
        # Methodology is intentionally included but remains unknown/inferred
        # until a qualified reviewer verifies method-family metadata.
        dims = dims + ("methodology",)
    elif category == "missing_strata":
        required["language"] = ("__INTENTIONALLY_ABSENT_STRATUM__",)
    return DiversityRequirement(
        requirement_id=f"REQ-{packet_id}",
        dimensions=dims,
        required_strata=required,
        min_family_count=5,
        max_hhi=0.40,
        max_share=0.60,
        min_composite=0.50,
        max_unknown_rate=0.10,
        counter_position_required=counter_required,
        research_question=f"T079 structural source-diversity evaluation for {packet_id}",
        ontology_digest="PENDING_FINAL_ONTOLOGY_APPROVAL",
        declared_before_retrieval=True,
        claim_exposure_required=True,
    )


def select_for_category(
    pool: list[dict[str, Any]], category: str, ordinal: int, *, mailto: str, cache_dir: Path
) -> list[dict[str, Any]]:
    offset = (ordinal * 7) % max(1, len(pool))
    # A packet is an immutable evidence snapshot. Category-specific structural
    # annotations must never mutate source dictionaries shared by other packets.
    rotated = copy.deepcopy(pool[offset:] + pool[:offset])
    if category == "balanced":
        return different_by(rotated, ("publisher", "venue", "geography", "period"), 8)
    if category == "concentrated":
        return concentrated(rotated, "publisher", 8)
    if category == "sparse":
        return rotated[:2]
    if category == "narrow":
        return concentrated(rotated, "venue", 4)
    if category == "multilingual":
        return multilingual(rotated, 8)
    if category == "historical":
        return historical(rotated, 8)
    if category == "method_monoculture":
        result = rotated[:7]
        for item in result:
            item = item
            item["methodology"] = "candidate_method_family_requires_human_verification"
            item["metadata_status"]["methodology"] = "inferred"
        return result
    if category in {"duplicate", "fake_diversity"}:
        return duplicate_sources(rotated[:5], mailto=mailto, cache_dir=cache_dir, limit=10)
    if category == "missing_strata":
        return rotated[:7]
    raise ValueError(category)


def source_snapshot_digest(records: list[dict[str, Any]]) -> str:
    return canonical_digest(records)


def packet_digest_payload(packet: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in packet.items() if key not in {"packet_digest", "review"}}


def build_packet(
    discipline: str, ordinal: int, pool: list[dict[str, Any]], *, mailto: str, cache_dir: Path
) -> dict[str, Any]:
    partition, category = ALLOCATION[ordinal]
    packet_id = f"{PREFIX[discipline]}-{ordinal:02d}"
    records = select_for_category(pool, category, ordinal, mailto=mailto, cache_dir=cache_dir)
    if not records:
        raise ValueError(f"{packet_id}: no source records selected")
    families = canonicalize_source_families(records, FamilyIdentityPolicy())
    claims = make_claims(records, category)
    requirement = requirement_for(packet_id, category, records)
    report = measure_source_diversity(
        families=families,
        admitted_claims=claims,
        requirements=requirement,
    )
    packet = {
        "schema_version": "2.0.0-candidate",
        "packet_id": packet_id,
        "discipline": discipline,
        "partition": partition,
        "stress_category": category,
        "status": "READY_FOR_HUMAN_REVIEW",
        "research_question": requirement.research_question,
        "construction": {
            "generator": "T079-BUILD-REVIEWER-PACKETS.py",
            "generated_at": utc(),
            "source_metadata_snapshot_digest": source_snapshot_digest(records),
            "construction_intent": category,
            "construction_notes": [
                "Stress category is construction intent only, not the human expected outcome.",
                "Claim exposure records are explicit synthetic structural metric fixtures and contain no asserted scholarly proposition.",
                "Unknown/inferred methodology or stance cannot improve the metric.",
            ],
        },
        "pre_retrieval_requirement": requirement.to_dict(),
        "source_records": records,
        "canonical_families": [family.to_dict() for family in families.families],
        "claim_exposure_records": claims,
        "machine_result": report.to_dict(),
        "review": None,
    }
    packet["packet_digest"] = canonical_digest(packet_digest_payload(packet))
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument(
        "--mailto",
        required=True,
        help="Contact email sent to metadata providers; never written as secret material.",
    )
    parser.add_argument("--pool-size", type=int, default=90)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    cache_dir = args.cache_dir.resolve()
    try:
        packets = []
        by_discipline: dict[str, int] = {}
        for discipline in DISCIPLINE_QUERIES:
            pool = acquire_pool(
                discipline, mailto=args.mailto, cache_dir=cache_dir, target=args.pool_size
            )
            if len(pool) < 12:
                raise ValueError(f"{discipline}: insufficient real metadata pool ({len(pool)})")
            discipline_packets = [
                build_packet(discipline, ordinal, pool, mailto=args.mailto, cache_dir=cache_dir)
                for ordinal in range(1, 13)
            ]
            for packet in discipline_packets:
                atomic_json(output_dir / "packets" / f"{packet['packet_id']}.json", packet)
            packets.extend(discipline_packets)
            by_discipline[discipline] = len(discipline_packets)
        if len(packets) != 108:
            raise ValueError(f"expected exactly 108 candidate packets, generated {len(packets)}")
        manifest = {
            "schema_version": "research-handoff.t079.candidate-manifest.v1",
            "status": "READY_FOR_HUMAN_REVIEW",
            "generated_at": utc(),
            "packet_count": len(packets),
            "packets_by_discipline": by_discipline,
            "categories": dict(
                sorted(Counter(packet["stress_category"] for packet in packets).items())
            ),
            "packet_records": [
                {
                    "packet_id": packet["packet_id"],
                    "discipline": packet["discipline"],
                    "partition": packet["partition"],
                    "stress_category": packet["stress_category"],
                    "packet_digest": packet["packet_digest"],
                    "review_status": "not_run",
                }
                for packet in packets
            ],
            "human_review": {
                "status": "not_run",
                "required_locked_packets_per_discipline": 10,
                "template": "T079-INDEPENDENT-REVIEW-TEMPLATE.json",
            },
            "release_evidence": False,
        }
        atomic_json(output_dir / "manifest.json", manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "PREPARATION_INCOMPLETE", "reason": str(exc)}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "status": "READY_FOR_HUMAN_REVIEW",
                "packet_count": 108,
                "by_discipline": by_discipline,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
