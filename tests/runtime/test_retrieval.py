from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from swos_runtime.models import SourceRecord, swos_id
from swos_runtime.retrieval import (
    PublicWebRetriever,
    _TextExtractor,
    _html_text,
    _openalex_abstract,
    _query_terms,
    _walk_urls,
    _windows,
)


class FakeWebResponse:
    def model_dump(self):
        return {
            "output": [
                {
                    "action": {
                        "sources": [
                            {"url": "https://museum.example/pigment", "title": "Museum pigment"},
                            {"url": "https://museum.example/pigment", "title": "Duplicate"},
                            {"url": "https://bad.example/short", "title": "Short page"},
                        ]
                    }
                }
            ]
        }


class FakeResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeWebResponse()


class FakeWebClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


class RetrievalTests(unittest.TestCase):
    def test_text_helpers_strip_script_and_find_windows(self):
        parser = _TextExtractor()
        parser.feed("<html><script>ignore me</script><p>Pigment &amp; binder evidence</p></html>")
        self.assertEqual(parser.text(), "Pigment & binder evidence")
        text = "alpha\n\nimportant pigment statement\n\nomega"
        self.assertIn("important pigment", _windows(text, ["pigment"], radius=20))
        self.assertTrue(_windows("plain fallback text", ["missing"]).startswith("plain"))

    def test_html_text_rejects_pdf_and_parses_html(self):
        with patch("swos_runtime.retrieval._urlopen", return_value=b"%PDF-1.7 fake"):
            self.assertEqual(_html_text("https://example.invalid/file.pdf"), "")
        with patch(
            "swos_runtime.retrieval._urlopen",
            return_value=b"<html><body><p>Useful pigment page</p></body></html>",
        ):
            self.assertIn("Useful pigment page", _html_text("https://example.invalid/page"))

    def test_openalex_abstract_query_terms_and_url_walk(self):
        abstract = _openalex_abstract({"Pigment": [1], "names": [2], "ambiguous": [3]})
        self.assertEqual(abstract, "Pigment names ambiguous")
        self.assertEqual(_openalex_abstract([]), "")
        terms = _query_terms("Write article about historical pigment names pigment chemistry")
        self.assertIn("pigment", [term.lower() for term in terms])
        self.assertEqual(_query_terms("a an to"), ["a an to"])
        urls = _walk_urls(
            {
                "nested": [
                    {"url": "https://example.org/a", "title": "A"},
                    {"url": "ftp://example.org/no", "title": "No"},
                ]
            }
        )
        self.assertEqual(urls, [("https://example.org/a", "A")])

    def test_openalex_adapter_parses_verified_record_and_handles_error(self):
        payload = {
            "results": [
                "not-a-record",
                {"display_name": "No abstract", "id": "https://openalex.org/W0"},
                {
                    "display_name": "Historical pigment nomenclature",
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.1234/pigment",
                    "publication_date": "2025-01-02",
                    "abstract_inverted_index": {
                        "Historical": [0],
                        "pigment": [1],
                        "names": [2],
                        "can": [3],
                        "encode": [4],
                        "trade": [5],
                        "source": [6],
                        "appearance": [7],
                        "and": [8],
                        "material": [9],
                        "context": [10],
                        "rather": [11],
                        "than": [12],
                        "one": [13],
                        "formula": [14],
                    },
                    "primary_location": {"landing_page_url": "https://publisher.example/article"},
                    "authorships": [
                        {"author": {"display_name": "A. Conservator"}},
                        {"author": {"display_name": "B. Scientist"}},
                    ],
                },
            ]
        }
        with patch(
            "swos_runtime.retrieval._urlopen",
            return_value=json.dumps(payload).encode("utf-8"),
        ):
            records = PublicWebRetriever()._openalex("pigment nomenclature")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].identifiers["doi"], "10.1234/pigment")
        self.assertTrue(records[0].metadata_verified)
        self.assertIn("A. Conservator", records[0].author or "")

        retriever = PublicWebRetriever()
        with patch("swos_runtime.retrieval._urlopen", side_effect=OSError("offline")):
            self.assertEqual(retriever._openalex("x"), [])
        self.assertEqual(retriever.events[0]["provider"], "openalex")

    def test_crossref_adapter_parses_record_and_handles_error(self):
        payload = {
            "message": {
                "items": [
                    "bad",
                    {"title": ["No usable abstract"]},
                    {
                        "title": ["Pigment terminology in context"],
                        "DOI": "10.9999/context",
                        "URL": "https://doi.org/10.9999/context",
                        "abstract": "<jats:p>" + ("Direct historical context. " * 8) + "</jats:p>",
                        "author": [{"given": "Ada", "family": "Scholar"}],
                        "published": {"date-parts": [[2024, 7, 3]]},
                    },
                ]
            }
        }
        with patch(
            "swos_runtime.retrieval._urlopen",
            return_value=json.dumps(payload).encode("utf-8"),
        ):
            records = PublicWebRetriever()._crossref("pigment")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].author, "Ada Scholar")
        self.assertEqual(records[0].published_date, "2024-07-03")
        self.assertTrue(records[0].metadata_verified)

        retriever = PublicWebRetriever()
        with patch("swos_runtime.retrieval._urlopen", side_effect=ValueError("bad json")):
            self.assertEqual(retriever._crossref("x"), [])
        self.assertEqual(retriever.events[0]["provider"], "crossref")

    def test_web_discovery_fetches_page_not_search_summary(self):
        retriever = PublicWebRetriever()
        retriever._web_client = FakeWebClient()
        long_page = (
            "Museum conservation pigment nomenclature material chemistry trade source appearance. "
            * 20
        )

        def fake_html(url, *, timeout=30):
            self.assertEqual(timeout, 8)
            if "bad.example" in url:
                return "short"
            return long_page

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch(
            "swos_runtime.retrieval._html_text", side_effect=fake_html
        ):
            records = retriever._openai_web("pigment nomenclature chemistry", limit=2)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].url, "https://museum.example/pigment")
        self.assertIn("Museum conservation", records[0].text)
        self.assertEqual(records[0].provider, "openai_web_search")
        self.assertTrue(records[0].metadata_verified)
        self.assertEqual(len(retriever._web_client.responses.calls), 1)

    def test_web_discovery_fails_closed_without_key_or_on_provider_error(self):
        retriever = PublicWebRetriever()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(retriever._openai_web("pigment"), [])

        class BrokenResponses:
            def create(self, **kwargs):
                del kwargs
                raise RuntimeError("provider unavailable")

        class BrokenClient:
            responses = BrokenResponses()

        retriever._web_client = BrokenClient()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            self.assertEqual(retriever._openai_web("pigment"), [])
        self.assertEqual(retriever.events[-1]["provider"], "openai_web_search")

    def test_legal_seed_and_composite_retrieval_dedupe(self):
        legal_text = (
            "12 competence 13 competence 146 evidence produced 147 documents produced "
            "all persons understand questions personal knowledge accurate result authenticating "
            * 20
        )
        retriever = PublicWebRetriever()
        with patch("swos_runtime.retrieval._html_text", return_value=legal_text):
            sources = retriever._seed_legal_sources("machine witness evidence")
        self.assertEqual(len(sources), 5)
        self.assertTrue(any(source.primary for source in sources))
        self.assertTrue(all(source.metadata_verified for source in sources))

        duplicate = SourceRecord(
            source_id=swos_id("src"),
            title="Same",
            url="https://example.org/same",
            source_type="scholarly",
            provider="test",
            text="x" * 500,
            identifiers={"doi": "10.1/same"},
            metadata_verified=True,
        )
        another = SourceRecord(
            source_id=swos_id("src"),
            title="Another",
            url="https://example.org/another",
            source_type="web_reference",
            provider="test",
            text="y" * 500,
            metadata_verified=True,
        )
        with patch.object(retriever, "_openalex", return_value=[duplicate]), patch.object(
            retriever, "_crossref", return_value=[duplicate]
        ), patch.object(retriever, "_openai_web", return_value=[another]):
            results = retriever.retrieve("pigment names", ["q1", "q2"], max_sources=2)
        self.assertEqual(len(results), 2)
        self.assertEqual({source.title for source in results}, {"Same", "Another"})


if __name__ == "__main__":
    unittest.main()
