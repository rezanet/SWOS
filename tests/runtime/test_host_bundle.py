from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from swos_runtime.host_bundle import (
    HostBundleError,
    HostBundleRetriever,
    HostBundleStageProvider,
    host_prose_transform,
    load_host_bundle,
)


class HostBundleTests(unittest.TestCase):
    def _bundle(self):
        return {
            "host": {
                "adapter": "codex",
                "model_host": "ChatGPT",
                "model": "GPT-5.6 Sol",
                "execution_mode": "host_native_subscription",
                "blind_review_supported": False,
                "api_key_used": False,
                "paid_api_calls": 0,
            },
            "sources": [
                {
                    "source_id": "src-00000000-0000-0000-0000-000000000001",
                    "title": "Source one",
                    "url": "https://example.org/one",
                    "source_type": "scholarly",
                    "provider": "host_web",
                    "text": "This exact passage directly supports the evidence claim and is long enough.",
                    "metadata_verified": True,
                }
            ],
            "stages": {
                "research_plan": {
                    "research_question": "Question",
                    "scope": "Scope",
                    "out_of_scope": [],
                    "queries": ["q1", "q2", "q3"],
                    "rival_theses": ["r1", "r2"],
                    "known_uncertainties": [],
                    "reviewer_roles": ["citation_auditor"],
                },
                "rerank_scores": [
                    {
                        "source_id": "src-00000000-0000-0000-0000-000000000001",
                        "score": 91,
                        "reason": "direct",
                    }
                ],
                "evidence_build": {"claims": []},
                "evidence_audit": {"audits": []},
                "argument_build": {"thesis": "t", "nodes": [], "edges": []},
                "draft": "# Draft\n\nText [S1].",
                "reviews": [{"reviews": []}],
            },
            "prose": {
                "adapter_mode": "host_native_swos_prose_contract",
                "safe_for_automatic_use": True,
            },
        }

    def test_load_rejects_incomplete_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            path.write_text(json.dumps({"host": {}}), encoding="utf-8")
            with self.assertRaises(HostBundleError):
                load_host_bundle(path)

    def test_retriever_and_reranker_use_no_runtime_network_or_api_key(self):
        bundle = self._bundle()
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            retriever = HostBundleRetriever(bundle)
            sources = retriever.retrieve("topic", ["q"])
            provider = HostBundleStageProvider(bundle)
            ranked, record = provider.rerank("topic", sources)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].rerank_score, 91)
        self.assertTrue(record["executed"])
        self.assertEqual(record["capability"], "joint_query_document_cross_encoder")
        self.assertFalse(provider.execution_metadata["api_key_used"])
        self.assertEqual(provider.execution_metadata["paid_api_calls"], 0)
        self.assertFalse(provider.blind_review_supported)
        self.assertFalse(retriever.events[0]["network_used_by_runtime"])

    def test_missing_stage_fails_closed(self):
        bundle = self._bundle()
        del bundle["stages"]["draft"]
        provider = HostBundleStageProvider(bundle)
        with self.assertRaises(HostBundleError):
            provider.draft({}, {}, [], {}, {})

    def test_prose_changed_text_requires_safe_flag(self):
        bundle = self._bundle()
        bundle["prose"]["final_text"] = "Changed text"
        bundle["prose"]["safe_for_automatic_use"] = False
        final, evidence = host_prose_transform(bundle)("Original text", None)
        self.assertEqual(final, "Original text")
        self.assertTrue(evidence["chunks"][0]["used_source_fallback"])
        self.assertTrue(evidence["all_changed_text_safe"])

    def test_provider_reads_stage_outputs_and_records_zero_cost_host_calls(self):
        provider = HostBundleStageProvider(self._bundle())
        plan = provider.plan({}, "scope")
        self.assertEqual(plan["research_question"], "Question")
        draft = provider.draft({}, {}, [], {}, {})
        self.assertIn("Draft", draft)
        review = provider.review("", [], {}, [], iteration=1)
        self.assertEqual(review, {"reviews": []})
        self.assertTrue(provider.calls)
        self.assertTrue(all(call.get("cost_estimate_usd") == 0 for call in provider.calls))


if __name__ == "__main__":
    unittest.main()
