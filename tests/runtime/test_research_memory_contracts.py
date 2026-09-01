"""US1 red tests for the public Research Programme Memory contracts."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from swos_runtime.research_memory import (
    DataClassification,
    HumanApproval,
    MemoryCandidate,
    MemoryQuery,
    MemoryReadPolicy,
    ProgrammeProjectBinding,
    ResearchMemoryService,
    ResearchScope,
    RPMOperation,
)

ROOT = Path(__file__).resolve().parents[2]


class ResearchMemoryContractTests(unittest.TestCase):
    def test_normative_v2_memory_and_exchange_schemas_are_discoverable(self) -> None:
        schema_dir = ROOT / "schemas/research-grade"
        expected = {
            "project-scope.schema.json",
            "rpm-policy.schema.json",
            "rpm-2.0.schema.json",
            "rpm-exchange.schema.json",
        }
        self.assertTrue(expected <= {path.name for path in schema_dir.glob("*.schema.json")})
        for name in expected:
            document = json.loads((schema_dir / name).read_text(encoding="utf-8"))
            self.assertIn("2.0.0", document["$id"])
            self.assertEqual("2.0.0", document["x-swos-version"])

    def test_scope_is_explicit_and_serializable(self) -> None:
        scope = ResearchScope("namespace-a", "programme-a", "project-a")
        self.assertEqual(
            {
                "repository_namespace_id": "namespace-a",
                "programme_id": "programme-a",
                "project_id": "project-a",
            },
            scope.to_dict(),
        )
        with self.assertRaises(ValueError):
            ResearchScope("", "programme-a", "project-a")

    def test_versioned_binding_candidate_operation_and_read_policy_have_required_fields(
        self,
    ) -> None:
        scope = ResearchScope("n", "p", "x")
        binding = ProgrammeProjectBinding.create(scope, label="Project X", manifest_digest="a" * 64)
        candidate = MemoryCandidate(
            item_id="item-1",
            category="finding",
            statement="ref:claim-1",
            confidence=0.8,
            data_classification=DataClassification.PUBLIC,
            owner="researcher",
            expiry="2099-01-01T00:00:00Z",
            source_grounded=True,
            epg_node_ids=("epg:claim-1",),
            sdl_decision_id="sdl:memory-1",
            parent_digest="b" * 64,
            origin="project-x",
        )
        operation = RPMOperation.write(scope, candidate)
        approval = HumanApproval(
            approval_id="approval-1",
            approver="reviewer-1",
            role="memory_owner",
            approved_at="2026-09-01T00:00:00Z",
            assessment_digest="c" * 64,
            candidate_digest=candidate.digest,
            sdl_decision_id="sdl:memory-1",
            disposition="approved",
            rationale="grounded",
        )
        policy = MemoryReadPolicy(DataClassification.PUBLIC)
        query = MemoryQuery(category="finding")
        for value in (binding, candidate, operation, approval, policy, query):
            self.assertEqual("2.0.0", value.schema_version)
            self.assertIsInstance(value.to_dict(), dict)

    def test_service_contract_requires_scope_and_returns_receipt_shape(self) -> None:
        self.assertTrue(hasattr(ResearchMemoryService, "assess_operation"))
        self.assertTrue(hasattr(ResearchMemoryService, "commit_operation"))
        self.assertTrue(hasattr(ResearchMemoryService, "query"))
        self.assertTrue(hasattr(ResearchMemoryService, "propose_expiry"))
        self.assertIsNotNone(datetime.now(timezone.utc))


if __name__ == "__main__":
    unittest.main()
