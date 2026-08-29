"""Public-source retrieval adapters for Autonomous SWOS."""

from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from .governance import detect_prompt_injection
from .models import SourceRecord, swos_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _licence_assurance(value: Any, *, is_open: bool = False) -> dict[str, Any]:
    licence = str(value or "").strip().lower()
    cleared = licence.startswith("cc-") or licence.startswith(
        ("https://creativecommons.org/licenses/", "https://creativecommons.org/publicdomain/")
    )
    return {
        "licence": licence or "unknown",
        "access_status": "open_access" if is_open else "unknown",
        "redistribution_allowed": cleared,
        "excerpt_limit_chars": 2400 if cleared else 0,
        "licence_cleared": cleared,
    }


def _crossref_retraction(relation: Any) -> str:
    if relation is None:
        return "not_checked"
    if not isinstance(relation, dict):
        return "not_checked"
    keys = {str(key).lower().replace("_", "-") for key in relation}
    if keys & {"is-retracted-by", "retracts"}:
        return "retracted"
    if keys & {"is-expression-of-concern-by", "has-expression-of-concern"}:
        return "expression_of_concern"
    if keys & {"is-corrected-by", "updates", "is-updated-by"}:
        return "corrected"
    return "clean"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return html.unescape("\n".join(self.parts))


def _urlopen(url: str, *, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SWOS/1.1-reference-runtime (+https://github.com/rezanet/SWOS)",
            "Accept": "text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read(2_500_000)


def _html_text(url: str, *, timeout: int = 30) -> str:
    raw = _urlopen(url, timeout=timeout)
    if raw.startswith(b"%PDF"):
        return ""
    parser = _TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return parser.text()


def _windows(text: str, terms: list[str], *, radius: int = 3200) -> str:
    compact = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    pieces: list[str] = []
    lowered = compact.lower()
    for term in terms:
        index = lowered.find(term.lower())
        if index >= 0:
            pieces.append(compact[max(0, index - radius) : index + radius])
    return ("\n\n--- relevant passage ---\n\n".join(pieces) if pieces else compact[:18000])[:24000]


def _openalex_abstract(inverted: Any) -> str:
    if not isinstance(inverted, dict):
        return ""
    positions: list[tuple[int, str]] = []
    for word, slots in inverted.items():
        if isinstance(word, str) and isinstance(slots, list):
            positions.extend((int(pos), word) for pos in slots if isinstance(pos, int))
    positions.sort()
    return " ".join(word for _, word in positions)


def _query_terms(query: str) -> list[str]:
    stop = {
        "about",
        "after",
        "against",
        "article",
        "because",
        "between",
        "could",
        "evidence",
        "historical",
        "should",
        "their",
        "these",
        "through",
        "under",
        "which",
        "with",
        "would",
        "write",
    }
    words = re.findall(r"[A-Za-z][A-Za-z'-]{3,}", query)
    terms: list[str] = []
    for word in words:
        lowered = word.lower()
        if lowered in stop or lowered in {term.lower() for term in terms}:
            continue
        terms.append(word)
        if len(terms) >= 10:
            break
    return terms or [query[:80]]


def _walk_urls(value: Any) -> list[tuple[str, str]]:
    """Collect source URLs/titles from a Responses API payload without trusting prose output."""
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        url = value.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            title = value.get("title")
            found.append((url, str(title or url)))
        for child in value.values():
            found.extend(_walk_urls(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_urls(child))
    return found


class PublicWebRetriever:
    """Reference retrieval across primary law, open scholarship and authoritative web sources."""

    AU_EVIDENCE_ACT = (
        "https://www.legislation.gov.au/C2004A04858/2025-06-10/"
        "2025-06-10/text/1/epub/OEBPS/document_1/document_1.html"
    )
    UK_WITNESS_COMPETENCE = "https://www.legislation.gov.uk/ukpga/1999/23/section/53"
    FRE_601 = "https://www.law.cornell.edu/rules/fre/rule_601"
    FRE_602 = "https://www.law.cornell.edu/rules/fre/rule_602"
    FRE_901 = "https://www.law.cornell.edu/rules/fre/rule_901"

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._web_client: Any | None = None

    @staticmethod
    def _is_legal_topic(topic: str) -> bool:
        lowered = topic.lower()
        return any(word in lowered for word in ("court", "witness", "evidence", "legal", "law"))

    def _seed_legal_sources(self, query: str) -> list[SourceRecord]:
        specs = [
            (
                "Evidence Act 1995 (Cth), ss 12–13 and 146–147",
                self.AU_EVIDENCE_ACT,
                "primary_law",
                "Australia",
                True,
                [
                    "12 competence",
                    "13 competence",
                    "146 evidence produced",
                    "147 documents produced",
                ],
            ),
            (
                "Youth Justice and Criminal Evidence Act 1999 (UK), s 53",
                self.UK_WITNESS_COMPETENCE,
                "primary_law",
                "England and Wales",
                True,
                ["competence of witnesses", "all persons", "understand questions"],
            ),
            (
                "Federal Rule of Evidence 601 — Competency to Testify in General",
                self.FRE_601,
                "legal_rule",
                "United States federal",
                False,
                ["every person is competent", "competency"],
            ),
            (
                "Federal Rule of Evidence 602 — Need for Personal Knowledge",
                self.FRE_602,
                "legal_rule",
                "United States federal",
                False,
                ["personal knowledge", "testify"],
            ),
            (
                "Federal Rule of Evidence 901 — Authenticating or Identifying Evidence",
                self.FRE_901,
                "legal_rule",
                "United States federal",
                False,
                ["process or system", "accurate result", "authenticating"],
            ),
        ]
        found: list[SourceRecord] = []
        for rank, (title, url, source_type, jurisdiction, primary, terms) in enumerate(
            specs, start=1
        ):
            try:
                text = _html_text(url)
            except Exception as exc:
                self.events.append({"provider": "seed_legal", "url": url, "error": str(exc)})
                continue
            targeted = _windows(text, terms)
            verified = len(targeted) > 300 and any(
                term.split()[0].lower() in targeted.lower() for term in terms
            )
            found.append(
                SourceRecord(
                    source_id=swos_id("src"),
                    title=title,
                    url=url,
                    source_type=source_type,
                    provider="seed_legal",
                    text=targeted,
                    jurisdiction=jurisdiction,
                    metadata_verified=verified,
                    primary=primary,
                    retrieval_query=query,
                    raw_rank=rank,
                    injection_detected=detect_prompt_injection(targeted),
                )
            )
        return found

    def _openalex(self, query: str, *, limit: int = 3) -> list[SourceRecord]:
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
            {"search": query, "per-page": str(limit)}
        )
        try:
            payload = json.loads(_urlopen(url).decode("utf-8"))
        except Exception as exc:
            self.events.append({"provider": "openalex", "query": query, "error": str(exc)})
            return []
        found: list[SourceRecord] = []
        for rank, item in enumerate(payload.get("results", []), start=1):
            if not isinstance(item, dict):
                continue
            abstract = _openalex_abstract(item.get("abstract_inverted_index"))
            title = str(item.get("display_name") or "").strip()
            if not title or len(abstract) < 80:
                continue
            doi = str(item.get("doi") or "").replace("https://doi.org/", "")
            primary_location = item.get("primary_location") or {}
            open_access = item.get("open_access") or {}
            licence = _licence_assurance(
                primary_location.get("license"), is_open=bool(open_access.get("is_oa"))
            )
            retraction_status = (
                "retracted"
                if item.get("is_retracted") is True
                else "clean"
                if item.get("is_retracted") is False
                else "not_checked"
            )
            checked_at = _now()
            landing = str(primary_location.get("landing_page_url") or item.get("id") or "")
            authors = []
            for authorship in (item.get("authorships") or [])[:6]:
                name = ((authorship or {}).get("author") or {}).get("display_name")
                if name:
                    authors.append(str(name))
            found.append(
                SourceRecord(
                    source_id=swos_id("src"),
                    title=title,
                    url=landing,
                    source_type="scholarly",
                    provider="openalex",
                    text=abstract,
                    author=", ".join(authors) or None,
                    published_date=str(item.get("publication_date") or "") or None,
                    identifiers={"doi": doi} if doi else {},
                    metadata_verified=bool(item.get("id") and title),
                    retrieval_query=query,
                    raw_rank=rank,
                    injection_detected=detect_prompt_injection(abstract),
                    retraction_status=retraction_status,
                    retraction_checked_at=(
                        checked_at if retraction_status != "not_checked" else None
                    ),
                    retraction_check_source=(
                        "openalex.is_retracted" if retraction_status != "not_checked" else None
                    ),
                    **licence,
                    licence_checked_at=checked_at,
                    licence_check_source="openalex.primary_location.license",
                )
            )
        return found

    def _crossref(self, query: str, *, limit: int = 3) -> list[SourceRecord]:
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
            {
                "query.bibliographic": query,
                "rows": str(limit),
                "select": "DOI,title,author,published,URL,abstract,relation,license",
            }
        )
        try:
            payload = json.loads(_urlopen(url).decode("utf-8"))
        except Exception as exc:
            self.events.append({"provider": "crossref", "query": query, "error": str(exc)})
            return []
        found: list[SourceRecord] = []
        for rank, item in enumerate(payload.get("message", {}).get("items", []), start=1):
            if not isinstance(item, dict):
                continue
            titles = item.get("title") or []
            title = str(titles[0] if titles else "").strip()
            abstract = re.sub(r"<[^>]+>", " ", str(item.get("abstract") or ""))
            abstract = html.unescape(" ".join(abstract.split()))
            if not title or len(abstract) < 80:
                continue
            authors = []
            for author in (item.get("author") or [])[:6]:
                name = " ".join(str(author.get(k) or "") for k in ("given", "family")).strip()
                if name:
                    authors.append(name)
            parts = ((item.get("published") or {}).get("date-parts") or [[]])[0]
            date = "-".join(f"{int(v):02d}" for v in parts) if parts else None
            doi = str(item.get("DOI") or "")
            licences = item.get("license") or []
            licence_url = next(
                (
                    str(entry.get("URL") or "")
                    for entry in licences
                    if isinstance(entry, dict) and entry.get("URL")
                ),
                "",
            )
            licence = _licence_assurance(licence_url, is_open=bool(licence_url))
            retraction_status = _crossref_retraction(item.get("relation"))
            checked_at = _now()
            found.append(
                SourceRecord(
                    source_id=swos_id("src"),
                    title=title,
                    url=str(item.get("URL") or (f"https://doi.org/{doi}" if doi else "")),
                    source_type="scholarly",
                    provider="crossref",
                    text=abstract,
                    author=", ".join(authors) or None,
                    published_date=date,
                    identifiers={"doi": doi} if doi else {},
                    metadata_verified=bool(doi and title),
                    retrieval_query=query,
                    raw_rank=rank,
                    injection_detected=detect_prompt_injection(abstract),
                    retraction_status=retraction_status,
                    retraction_checked_at=(
                        checked_at if retraction_status != "not_checked" else None
                    ),
                    retraction_check_source=(
                        "crossref.relation" if retraction_status != "not_checked" else None
                    ),
                    **licence,
                    licence_checked_at=checked_at,
                    licence_check_source="crossref.license",
                )
            )
        return found

    def _openai_web(self, query: str, *, limit: int = 3) -> list[SourceRecord]:
        """Discover authoritative URLs with web search, then fetch page text ourselves."""
        if not os.environ.get("OPENAI_API_KEY"):
            return []
        try:
            if self._web_client is None:
                from openai import OpenAI

                self._web_client = OpenAI()
            response = self._web_client.responses.create(
                model=os.environ.get("SWOS_RUNTIME_MODEL", "gpt-5.6-luna"),
                tools=[{"type": "web_search"}],
                tool_choice="required",
                include=["web_search_call.action.sources"],
                input=(
                    "Find authoritative source pages directly relevant to this research query. "
                    "Prefer museums, conservation institutes, universities, government or standards "
                    "bodies, scholarly publishers, and digitised primary sources where appropriate. "
                    "Do not answer the research question; use web search only to discover sources.\n\n"
                    f"QUERY: {query}"
                ),
                max_output_tokens=250,
                store=False,
            )
            payload = response.model_dump() if hasattr(response, "model_dump") else response
            discovered = _walk_urls(payload)
        except Exception as exc:
            self.events.append({"provider": "openai_web_search", "query": query, "error": str(exc)})
            return []

        terms = _query_terms(query)
        found: list[SourceRecord] = []
        seen: set[str] = set()
        for url, title in discovered:
            if url in seen:
                continue
            seen.add(url)
            try:
                text = _html_text(url, timeout=8)
            except Exception as exc:
                self.events.append(
                    {"provider": "openai_web_fetch", "query": query, "url": url, "error": str(exc)}
                )
                continue
            if len(text) < 400:
                continue
            targeted = _windows(text, terms)
            if len(targeted) < 300:
                continue
            found.append(
                SourceRecord(
                    source_id=swos_id("src"),
                    title=title.strip() or url,
                    url=url,
                    source_type="web_reference",
                    provider="openai_web_search",
                    text=targeted,
                    metadata_verified=True,
                    retrieval_query=query,
                    raw_rank=len(found) + 1,
                    injection_detected=detect_prompt_injection(targeted),
                )
            )
            if len(found) >= limit:
                break
        return found

    def retrieve(
        self, topic: str, queries: list[str], *, max_sources: int = 14
    ) -> list[SourceRecord]:
        queries = [q.strip() for q in queries if isinstance(q, str) and q.strip()]
        if not queries:
            queries = [topic]
        found: list[SourceRecord] = []
        if self._is_legal_topic(topic):
            found.extend(self._seed_legal_sources(queries[0]))
        for query in queries[:6]:
            found.extend(self._openalex(query, limit=2))
            found.extend(self._crossref(query, limit=2))
        for query in queries[:3]:
            found.extend(self._openai_web(query, limit=2))
        deduped: list[SourceRecord] = []
        seen: set[str] = set()
        for source in found:
            key = (source.identifiers.get("doi") or source.url or source.title).lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(source)
            if len(deduped) >= max_sources:
                break
        return deduped
