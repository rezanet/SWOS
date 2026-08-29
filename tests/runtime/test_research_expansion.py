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


class ReviewerRepairProvider(FakeProvider):
    def plan_review_repair(self, topic, findings):
        del topic, findings
        return {
            "research_goal": "Find direct evidence that resolves the reviewer evidence gap.",
            "queries": ["direct evidence gap", "bounded counterexample"],
        }

    def build_evidence(self, topic, sources):
        result = super().build_evidence(topic, sources)
        expansion = next((source for source in sources if source.provider == "delta"), None)
        if expansion is not None:
            result["claims"].append(
                {
                    "claim": "A bounded counter-position is directly documented.",
                    "source_id": expansion.source_id,
                    "exact_quote": "Delta evidence records a genuine counter-position.",
                    "locator": "paragraph 1",
                    "epistemic_type": "source_backed_claim",
                    "confidence": "high",
                    "stance": "limitation",
                    "rationale": "Direct repair evidence",
                }
            )
        return result

    def draft(self, request, plan, evidence_rows, argument, source_labels):
        del request, plan, evidence_rows, argument
        self.draft_called = True
        markers = list(source_labels.values())
        cited = markers[:4] if len(markers) >= 4 else markers[:3]
        marker_text = ", ".join(f"[{marker}]" for marker in cited)
        sentence = (
            "Governed research distinguishes evidence from inference and preserves counter-evidence "
            f"through independently verified sources {marker_text}. "
        )
        body = (sentence * 75).strip()
        return f"# Governed research\n\n{body}\n\n## Conclusion\n\n{sentence * 8}"

    def review(self, article, evidence_rows, argument, sources, iteration):
        del article, evidence_rows, argument
        roles = [
            "citation_auditor",
            "argument_examiner",
            "discipline_expert",
            "hostile_reviewer",
            "editor",
            "governance_reviewer",
        ]
        repaired = any(source.provider == "delta" for source in sources)
        reviews = []
        for role in roles:
            findings = []
            verdict = "pass"
            if iteration == 1 and role == "citation_auditor" and not repaired:
                verdict = "fail"
                findings = [
                    {
                        "severity": "major",
                        "category": "unsupported_claim",
                        "locus": "thesis",
                        "description": "A direct evidentiary example is missing.",
                        "required_action": "Research and add direct evidence before delivery.",
                    }
                ]
            reviews.append(
                {
                    "role": role,
                    "verdict": verdict,
                    "attack_summary": f"{role} completed iteration {iteration}.",
                    "findings": findings,
                }
            )
        return {"reviews": reviews}


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
            retrieval = json.loads((Path(tmp) / "retrieval.json").read_text(encoding="utf-8"))
            self.assertEqual(len(retrieval["research_expansions"]), 1)
            self.assertEqual(retrieval["research_expansions"][0]["new_sources"], 1)
            matrix = json.loads((Path(tmp) / "evidence-matrix.json").read_text(encoding="utf-8"))
            self.assertTrue(matrix["coverage"]["counter_evidence_present"])

    def test_major_reviewer_evidence_finding_routes_back_to_research(self):
        provider = ReviewerRepairProvider()
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
            retrieval = json.loads((Path(tmp) / "retrieval.json").read_text(encoding="utf-8"))
            repair = retrieval["research_expansions"][-1]
            self.assertEqual(repair["phase"], "review_repair")
            self.assertEqual(repair["review_iteration"], 1)
            self.assertEqual(repair["new_sources"], 1)
            matrix = json.loads((Path(tmp) / "evidence-matrix.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(matrix["rows"]), 7)
            control = json.loads((Path(tmp) / "run-control.json").read_text(encoding="utf-8"))
            self.assertEqual(control["revision_count"], 1)


if __name__ == "__main__":
    unittest.main()
