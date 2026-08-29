from __future__ import annotations

import unittest

from swos_runtime.finalizer import _evidence_matrix
from swos_runtime.models import SourceRecord
from swos_runtime.retrieval import _crossref_retraction, _licence_assurance


class FakeRun:
    def __init__(self, candidate, support="directly_supports"):
        self.payloads = {
            "evidence_extraction": {"claims": [candidate]},
            "citation_support_audit": {
                "audits": [{"index": 0, "support_level": support, "reason": "checked"}]
            },
        }

    def _latest(self, stage):
        return self.payloads.get(stage)


def _source(**changes):
    values = {
        "source_id": "src-11111111-1111-1111-1111-111111111111",
        "title": "Verified source",
        "url": "https://example.org/source",
        "source_type": "scholarly",
        "provider": "test",
        "text": "This exact passage directly supports the bounded claim.",
        "metadata_verified": True,
        "retraction_status": "clean",
        "retraction_checked_at": "2026-08-30T00:00:00+00:00",
        "retraction_check_source": "test-registry",
        "licence": "cc-by",
        "access_status": "open_access",
        "redistribution_allowed": True,
        "excerpt_limit_chars": 2400,
        "licence_cleared": True,
        "licence_checked_at": "2026-08-30T00:00:00+00:00",
        "licence_check_source": "test-registry",
    }
    values.update(changes)
    return SourceRecord(**values)


class CitationAssuranceTests(unittest.TestCase):
    def test_licence_and_retraction_normalization_fail_closed(self):
        self.assertTrue(_licence_assurance("cc-by", is_open=True)["licence_cleared"])
        self.assertFalse(_licence_assurance(None)["licence_cleared"])
        self.assertEqual(_crossref_retraction({"is-retracted-by": []}), "retracted")
        self.assertEqual(
            _crossref_retraction({"is-expression-of-concern-by": []}),
            "expression_of_concern",
        )
        self.assertEqual(_crossref_retraction({}), "clean")
        self.assertEqual(_crossref_retraction(None), "not_checked")
        self.assertEqual(_crossref_retraction("malformed"), "not_checked")

    def test_only_source_owned_clean_and_cleared_assurance_admits_claim(self):
        source = _source()
        candidate = {
            "claim": "A bounded claim.",
            "source_id": source.source_id,
            "exact_quote": source.text,
            "retraction_checked": False,
            "licence_cleared": False,
        }
        matrix, _, rejected, _ = _evidence_matrix(
            work_id="wrk-11111111-1111-1111-1111-111111111111",
            run=FakeRun(candidate),
            sources=[source],
            source_id_map={source.source_id: source.source_id},
        )
        self.assertEqual(len(matrix["rows"]), 1)
        self.assertFalse(rejected)
        citation = matrix["rows"][0]["citations"][0]
        self.assertTrue(citation["retraction_checked"])
        self.assertTrue(citation["licence_cleared"])

    def test_unsafe_sources_and_non_direct_support_are_rejected(self):
        cases = [
            (_source(retraction_status="retracted"), "directly_supports", "retraction"),
            (_source(retraction_status="not_checked"), "directly_supports", "retraction"),
            (_source(retraction_checked_at=None), "directly_supports", "retraction"),
            (_source(licence_cleared=False), "directly_supports", "licence"),
            (_source(licence_check_source=None), "directly_supports", "licence"),
        ]
        cases.extend(
            (_source(), support, support)
            for support in (
                "partially_supports",
                "context_only",
                "contradicts",
                "citation_laundering_risk",
                "invalid_citation",
            )
        )
        for source, support, reason in cases:
            with self.subTest(reason=reason):
                candidate = {
                    "claim": "A bounded claim.",
                    "source_id": source.source_id,
                    "exact_quote": source.text,
                    "retraction_checked": True,
                    "licence_cleared": True,
                }
                matrix, _, rejected, _ = _evidence_matrix(
                    work_id="wrk-11111111-1111-1111-1111-111111111111",
                    run=FakeRun(candidate, support=support),
                    sources=[source],
                    source_id_map={source.source_id: source.source_id},
                )
                self.assertFalse(matrix["rows"])
                self.assertIn(reason, rejected[0]["reason"])


if __name__ == "__main__":
    unittest.main()
