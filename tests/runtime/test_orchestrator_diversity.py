"""Orchestrator-to-diversity admission boundary tests."""

from __future__ import annotations

import unittest

from swos_runtime.orchestrator import AutonomousSWOS
from swos_runtime.source_diversity import DiversityRequirement


class _FakeRun:
    def __init__(self) -> None:
        self.state = {
            "diversity_requirement": DiversityRequirement(
                requirement_id="req-orchestrator",
                dimensions=("publisher",),
                min_family_count=1,
            ).to_dict()
        }
        self.payloads = {
            "source_retrieval": {
                "sources": [
                    {
                        "source_id": "s-1",
                        "title": "One",
                        "url": "https://example.org/one",
                        "source_type": "article",
                        "provider": "provider-a",
                        "text": "One",
                        "metadata_verified": True,
                    },
                    {
                        "source_id": "s-2",
                        "title": "Two",
                        "url": "https://example.org/two",
                        "source_type": "article",
                        "provider": "provider-b",
                        "text": "Two",
                        "metadata_verified": True,
                    },
                ]
            },
            "citation_support_audit": {
                "audits": [
                    {
                        "index": 0,
                        "support_level": "directly_supports",
                        "eligibility": {"eligible": False, "state": "rule_rejected"},
                    },
                    {
                        "index": 1,
                        "support_level": "directly_supports",
                        "eligibility": {"eligible": True, "state": "eligible"},
                    },
                ]
            },
            "evidence_extraction": {"claims": [{"source_id": "s-1"}, {"source_id": "s-2"}]},
        }
        self.report = None

    def _latest(self, stage: str):
        return self.payloads.get(stage)

    def record_diversity_report(self, report) -> None:
        self.report = report


class OrchestratorDiversityTests(unittest.TestCase):
    def test_only_core_eligible_direct_support_enters_diversity_measurement(self) -> None:
        run = _FakeRun()
        report = AutonomousSWOS._measure_diversity(run)
        self.assertIsNotNone(report)
        self.assertEqual(1, report.family_count)
        self.assertIs(report, run.report)


if __name__ == "__main__":
    unittest.main()
