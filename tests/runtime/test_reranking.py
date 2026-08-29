from __future__ import annotations

import math
import unittest

from swos_runtime.broker import CapabilityBroker
from swos_runtime.models import SourceRecord
from swos_runtime.reranking import CrossEncoderReranker, RerankingError


def _source(source_id: str, text: str) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        title=source_id,
        url=f"https://example.org/{source_id}",
        source_type="scholarly",
        provider="test",
        text=text,
    )


class FakeCrossEncoder:
    def __init__(self, scores):
        self.scores = scores
        self.calls = []

    def predict(self, pairs):
        self.calls.append(pairs)
        return self.scores


class StageBindingThatMustNotRerank:
    model = "generative-stage-model"

    def rerank(self, *args, **kwargs):
        del args, kwargs
        raise AssertionError("the generative stage binding must not perform reranking")


class FakeRetriever:
    pass


class CrossEncoderRerankerTests(unittest.TestCase):
    def test_scores_query_document_pairs_and_records_identity(self):
        model = FakeCrossEncoder([0.25, 0.9, 0.25])
        reranker = CrossEncoderReranker(model=model, model_name="test/cross-encoder")
        sources = [_source("a", "alpha"), _source("b", "beta"), _source("c", "gamma")]

        ranked, evidence = reranker.rerank("query", sources, top_k=2)

        self.assertEqual([source.source_id for source in ranked], ["b", "a"])
        self.assertEqual(model.calls, [[("query", "alpha"), ("query", "beta"), ("query", "gamma")]])
        self.assertEqual(evidence["implementation"], "sentence-transformers.CrossEncoder")
        self.assertEqual(evidence["reranker_model"], "test/cross-encoder")
        self.assertEqual(evidence["scores"], {"a": 0.25, "b": 0.9, "c": 0.25})
        self.assertEqual(sources[1].rerank_score, 0.9)

    def test_invalid_score_outputs_fail_closed(self):
        sources = [_source("a", "alpha"), _source("b", "beta")]
        invalid = ([1.0], [1.0, True], [1.0, math.nan], [1.0, "bad"])
        for scores in invalid:
            with self.subTest(scores=scores):
                reranker = CrossEncoderReranker(model=FakeCrossEncoder(scores))
                with self.assertRaises(RerankingError):
                    reranker.rerank("query", sources)

    def test_empty_source_set_does_not_load_model(self):
        reranker = CrossEncoderReranker()
        ranked, evidence = reranker.rerank("query", [])
        self.assertEqual(ranked, [])
        self.assertEqual(evidence["scores"], {})

    def test_broker_uses_dedicated_rerank_binding(self):
        reranker = CrossEncoderReranker(model=FakeCrossEncoder([0.8]))
        broker = CapabilityBroker(
            stage_binding=StageBindingThatMustNotRerank(),
            retrieval_binding=FakeRetriever(),
            rerank_binding=reranker,
        )

        ranked, evidence = broker.semantic_rerank("query", [_source("a", "alpha")])

        self.assertEqual(ranked[0].source_id, "a")
        self.assertEqual(evidence["capability"], "semantic_rerank")
        self.assertEqual(evidence["contract"], "swos.semantic-rerank.v1")
        self.assertEqual(evidence["reranker_model"], reranker.model_name)
        self.assertEqual(evidence["model"], reranker.model_name)
        self.assertEqual(evidence["judgement"]["model"], reranker.model_name)
        self.assertTrue(evidence["contract_passed"])


if __name__ == "__main__":
    unittest.main()
