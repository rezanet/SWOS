"""US1 red tests for immutable lifecycle transitions and exceptional reads."""

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


class ResearchMemoryLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.service = ResearchMemoryService(ProgrammeStore(Path(self.holder.name) / "rpm.sqlite"))
        self.service.store.initialize()
        self.scope = ResearchScope("n", "p", "x")
        self._commit(RPMOperation.register_project(self.scope, label="X", manifest_digest="a" * 64))

    def tearDown(self) -> None:
        self.holder.cleanup()

    def _candidate(self, item_id="item-1", expiry="2099-01-01T00:00:00Z") -> MemoryCandidate:
        return MemoryCandidate(item_id, "finding", f"ref:{item_id}", 0.8, DataClassification.PUBLIC, "owner", expiry, True, (f"epg:{item_id}",), f"sdl:{item_id}", parent_digest="b" * 64, origin="fixture")

    def _commit(self, operation: RPMOperation, *, as_of=None):
        assessment = self.service.assess_operation(self.scope, operation, as_of=as_of)
        approval = HumanApproval.for_assessment(assessment, approver="reviewer", role="memory_owner")
        return self.service.commit_operation(self.scope, assessment_id=assessment.assessment_id, approval=approval, as_of=as_of)

    def test_write_confirm_correct_supersede_contradict_expire_and_delete_are_append_only(self) -> None:
        self._commit(RPMOperation.write(self.scope, self._candidate()))
        self._commit(RPMOperation.confirm(self.scope, "item-1"))
        self._commit(RPMOperation.correct(self.scope, "item-1", self._candidate("item-2")))
        self._commit(RPMOperation.supersede(self.scope, "item-2", self._candidate("item-3")))
        self._commit(RPMOperation.contradiction_open(self.scope, "item-3", reason="counter-evidence"))
        self._commit(RPMOperation.contradiction_resolve(self.scope, "item-3", resolution="active"))
        self._commit(RPMOperation.expire(self.scope, "item-3"))
        self._commit(RPMOperation.delete(self.scope, "item-3"))
        events = self.service.store.events(self.scope)
        self.assertGreaterEqual(len(events), 9)
        self.assertEqual([], self.service.store.verify_chain(self.scope))

    def test_exact_expiry_excludes_normal_reads_but_governance_reads_are_receipted(self) -> None:
        self._commit(RPMOperation.write(self.scope, self._candidate(expiry="2026-09-01T00:00:00Z")), as_of="2026-08-31T00:00:00Z")
        normal = self.service.query(self.scope, MemoryQuery(), self.service.normal_read_policy(), as_of="2026-09-01T00:00:00Z")
        self.assertEqual([], normal.items)
        exceptional = self.service.query(self.scope, MemoryQuery(), self.service.governance_read_policy(), as_of="2026-09-01T00:00:00Z")
        self.assertTrue(exceptional.receipt.exceptional)

    def test_project_retirement_unbinding_and_programme_closure_preserve_history(self) -> None:
        self._commit(RPMOperation.retire_project(self.scope))
        with self.assertRaises(Exception):
            self.service.assess_operation(self.scope, RPMOperation.write(self.scope, self._candidate("after-retire")))
        self.assertTrue(self.service.store.events(self.scope))
        self._commit(RPMOperation.close_programme(self.scope))
        self.assertTrue(self.service.store.has_programme_history(self.scope))


if __name__ == "__main__":
    unittest.main()
