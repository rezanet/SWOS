from __future__ import annotations

import unittest

from swos_runtime.broker import CapabilityBroker


class FakeStageBinding:
    model = "vendor-model"

    def rerank(self, topic, sources, top_k=10):
        del topic
        return sources[:top_k], {
            "method": "vendor_specific_reranker_name",
            "scores": [],
        }


class FakeRetriever:
    def retrieve(self, topic, queries):
        del topic, queries
        return ["source"]


class CapabilityBrokerTests(unittest.TestCase):
    def test_rerank_is_normalized_to_swos_capability_contract(self):
        broker = CapabilityBroker(
            stage_binding=FakeStageBinding(),
            retrieval_binding=FakeRetriever(),
            adapter="future-model-adapter",
            model_host="Future Host",
            execution_mode="host_native_subscription",
        )
        ranked, record = broker.semantic_rerank("query", ["a", "b"], top_k=1)
        self.assertEqual(ranked, ["a"])
        self.assertEqual(record["capability"], "semantic_rerank")
        self.assertEqual(record["contract"], "swos.semantic-rerank.v1")
        self.assertTrue(record["executed"])
        self.assertEqual(record["adapter"], "future-model-adapter")
        self.assertEqual(record["method"], "vendor_specific_reranker_name")

    def test_source_retrieval_records_capability_not_vendor(self):
        broker = CapabilityBroker(
            stage_binding=FakeStageBinding(),
            retrieval_binding=FakeRetriever(),
            adapter="codex-subscription",
            model_host="ChatGPT/Codex",
            execution_mode="host_native_subscription",
        )
        self.assertEqual(broker.source_retrieval("topic", ["q"]), ["source"])
        self.assertEqual(broker.events[-1]["capability"], "source_retrieval")
        self.assertEqual(broker.events[-1]["contract"], "swos.source-retrieval.v1")


if __name__ == "__main__":
    unittest.main()
