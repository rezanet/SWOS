"""US1 red tests for explicit scope and project visibility isolation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swos_runtime.programme_store import ProgrammeStore
from swos_runtime.research_memory import (
    DataClassification,
    HumanApproval,
    MemoryCandidate,
    MemoryQuery,
    ResearchMemoryService,
    ResearchScope,
    RPMOperation,
)


class ResearchMemoryIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.service = ResearchMemoryService(ProgrammeStore(Path(self.holder.name) / "rpm.sqlite"))
        self.service.store.initialize()
        self.a = ResearchScope("n-a", "programme-a", "project-a")
        self.b = ResearchScope("n-b", "programme-a", "project-b")

    def tearDown(self) -> None:
        self.holder.cleanup()

    def _candidate(self, item_id: str) -> MemoryCandidate:
        return MemoryCandidate(
            item_id=item_id,
            category="finding",
            statement=f"ref:{item_id}",
            confidence=0.9,
            data_classification=DataClassification.PUBLIC,
            owner="owner",
            expiry="2099-01-01T00:00:00Z",
            source_grounded=True,
            epg_node_ids=(f"epg:{item_id}",),
            sdl_decision_id=f"sdl:{item_id}",
            parent_digest="a" * 64,
            origin="fixture",
        )

    def _commit(self, scope: ResearchScope, operation: RPMOperation) -> None:
        assessment = self.service.assess_operation(scope, operation)
        approval = HumanApproval.for_assessment(
            assessment, approver="reviewer", role="memory_owner"
        )
        self.service.commit_operation(
            scope, assessment_id=assessment.assessment_id, approval=approval
        )

    def test_missing_or_unregistered_scope_is_denied(self) -> None:
        with self.assertRaises(Exception):
            self.service.query(self.a, MemoryQuery(), self.service.normal_read_policy())

    def test_namespace_and_project_cannot_observe_or_influence_each_other(self) -> None:
        self._commit(
            self.a, RPMOperation.register_project(self.a, label="A", manifest_digest="a" * 64)
        )
        self._commit(self.a, RPMOperation.write(self.a, self._candidate("item-a")))
        with self.assertRaises(Exception):
            self.service.query(self.b, MemoryQuery(), self.service.normal_read_policy())
        self.assertEqual(
            ["item-a"],
            [
                item["item_id"]
                for item in self.service.query(
                    self.a, MemoryQuery(), self.service.normal_read_policy()
                ).items
            ],
        )

    def test_cross_scope_candidate_reference_is_rejected(self) -> None:
        self._commit(
            self.a, RPMOperation.register_project(self.a, label="A", manifest_digest="a" * 64)
        )
        candidate = self._candidate("item-a")
        forged = RPMOperation.write(self.b, candidate)
        with self.assertRaises(Exception):
            self.service.assess_operation(self.b, forged)


if __name__ == "__main__":
    unittest.main()
