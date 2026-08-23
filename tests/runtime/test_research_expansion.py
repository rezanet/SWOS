from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from test_runtime import FakeProvider, FakeRetriever, safe_prose

from swos_runtime.models import ResearchRequest, SourceRecord, swos_id
from swos_runtime.orchestrator import AutonomousSWOS


class ExpandingRetriever(FakeRetriever):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def retrieve(self, topic, queries):
        self.calls += 1
        if self.calls == 1:
            return super().retrieve(topic, queries)
        return [
            SourceRecord(
                source_id=swos_id("src"),
                title="Expansion Source",
                url="https://example.invalid/expansion",
                source_type="scholarly",
                provider="delta",
                text=(
                    "Delta evidence records a genuine counter-position. "
                    "The terminology remains useful in bounded contexts while requiring qualification."
                ),
                metadata_verified=True,
                retrieval_query="counter-position",
            )
        ]


class CoverageGapProvider(FakeProvider):
    def build_evidence(self, topic, sources):
        result = super().build_evidence(topic, sources)
        if len(sources) <= 3:
            for claim in result["claims"]:
                claim["stance"] = "support"
        return result


class ResearchExpansionTests(unittest.TestCase):
    def test_missing_counter_evidence_triggers_bounded_research_then_approves(self):
        provider = CoverageGapProvider()
        retriever = ExpandingRetriever()
        runtime = AutonomousSWOS(
            stage_provider=provider,
            retriever=retriever,
            prose_transform=safe_prose,
        )
        with tempfile.TemporaryDirectory() as tmp:
            outcome = runtime.run(
                ResearchRequest(
                    topic="Does governed retrieval improve scholarly control?",
                    length=1500,
                ),
                tmp,
            )
            self.assertEqual(outcome.status, "APPROVED", outcome.blocking_reasons)
            self.assertEqual(retriever.calls, 2)
            retrieval = json.loads(
                (Path(tmp) / "retrieval.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(retrieval["research_expansions"]), 1)
            self.assertEqual(retrieval["research_expansions"][0]["new_sources"], 1)
            matrix = json.loads(
                (Path(tmp) / "evidence-matrix.json").read_text(encoding="utf-8")
            )
            self.assertTrue(matrix["coverage"]["counter_evidence_present"])


if __name__ == "__main__":
    unittest.main()
