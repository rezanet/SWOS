"""US1 red tests for evidence-bound assessment and commit-time revalidation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swos_runtime.models import SWOSRuntimeError
from swos_runtime.programme_store import ProgrammeStore
from swos_runtime.research_memory import (
    DataClassification,
    HumanApproval,
    MemoryCandidate,
    ResearchMemoryService,
    ResearchScope,
    RPMOperation,
)


class ResearchMemoryWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.service = ResearchMemoryService(ProgrammeStore(Path(self.holder.name) / "rpm.sqlite"))
        self.service.store.initialize()
        self.scope = ResearchScope("n", "p", "x")
        self._register()

    def tearDown(self) -> None:
        self.holder.cleanup()

    def _register(self) -> None:
        operation = RPMOperation.register_project(self.scope, label="X", manifest_digest="a" * 64)
        assessment = self.service.assess_operation(self.scope, operation)
        approval = HumanApproval.for_assessment(assessment, approver="reviewer", role="memory_owner")
        self.service.commit_operation(self.scope, assessment_id=assessment.assessment_id, approval=approval)

    def _candidate(self, *, classification=DataClassification.PUBLIC, expiry="2099-01-01T00:00:00Z") -> MemoryCandidate:
        return MemoryCandidate(
            item_id="item-1",
            category="finding",
            statement="ref:claim-1",
            confidence=0.9,
            data_classification=classification,
            owner="owner",
            expiry=expiry,
            source_grounded=True,
            epg_node_ids=("epg:claim-1",),
            sdl_decision_id="sdl:1",
            parent_digest="b" * 64,
            origin="project-x",
        )

    def test_missing_epg_sdl_approval_and_restricted_classification_fail_closed(self) -> None:
        invalid = self._candidate()
        invalid = MemoryCandidate(
            invalid.item_id,
            invalid.category,
            invalid.statement,
            invalid.confidence,
            invalid.data_classification,
            invalid.owner,
            invalid.expiry,
            invalid.source_grounded,
            (),
            invalid.sdl_decision_id,
            parent_digest=invalid.parent_digest,
            origin=invalid.origin,
        )
        assessment = self.service.assess_operation(self.scope, RPMOperation.write(self.scope, invalid))
        self.assertEqual("deny", assessment.status)
        self.assertTrue(assessment.denial_reasons)
        restricted = self._candidate(classification=DataClassification.RESTRICTED)
        assessment = self.service.assess_operation(self.scope, RPMOperation.write(self.scope, restricted))
        self.assertEqual("deny", assessment.status)

    def test_stale_policy_expired_assessment_and_commit_time_head_change_are_rejected(self) -> None:
        operation = RPMOperation.write(self.scope, self._candidate())
        assessment = self.service.assess_operation(self.scope, operation)
        self.service.policy_digest = "f" * 64
        with self.assertRaises(SWOSRuntimeError):
            self.service.commit_operation(
                self.scope,
                assessment_id=assessment.assessment_id,
                approval=HumanApproval.for_assessment(assessment, approver="reviewer", role="memory_owner"),
            )

    def test_operation_hash_and_approval_digest_are_bound(self) -> None:
        operation = RPMOperation.write(self.scope, self._candidate())
        assessment = self.service.assess_operation(self.scope, operation)
        approval = HumanApproval.for_assessment(assessment, approver="reviewer", role="memory_owner")
        forged = HumanApproval(**{**approval.to_dict(), "assessment_digest": "0" * 64})
        with self.assertRaises(SWOSRuntimeError):
            self.service.commit_operation(self.scope, assessment_id=assessment.assessment_id, approval=forged)


if __name__ == "__main__":
    unittest.main()
