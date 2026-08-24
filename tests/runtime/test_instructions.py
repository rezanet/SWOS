from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from swos_runtime.instructions import INSTRUCTION_SET, instruction_record, instruction_text
from swos_runtime.llm import OpenAIStageProvider


class FakeResponses:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(id="resp-1", output_text=self.output, usage=None)


class FakeClient:
    def __init__(self, output):
        self.responses = FakeResponses(output)


class InstructionOwnershipTests(unittest.TestCase):
    def test_every_scholarly_stage_has_canonical_instruction_identity_and_hash(self):
        stages = [
            "research_planning",
            "research_repair_planning",
            "source_retrieval",
            "semantic_rerank",
            "evidence_extraction",
            "citation_support_audit",
            "argument_construction",
            "draft_generation",
            "prose_transformation",
            "semantic_verification",
            "hostile_review",
            "revision",
        ]
        for stage in stages:
            record = instruction_record(stage)
            self.assertEqual(record["instruction_set"], INSTRUCTION_SET)
            self.assertTrue(record["instruction_id"].startswith("swos.instruction."))
            self.assertEqual(len(record["sha256"]), 64)
            self.assertTrue(record["text"])

    def test_openai_adapter_delivers_canonical_instruction_verbatim(self):
        output = json.dumps(
            {
                "research_question": "Q",
                "scope": "S",
                "out_of_scope": [],
                "queries": ["q1", "q2", "q3"],
                "rival_theses": ["r1", "r2"],
                "known_uncertainties": [],
                "reviewer_roles": [],
            }
        )
        client = FakeClient(output)
        provider = OpenAIStageProvider(model="transport-model", client=client)
        provider.plan({"topic": "Q"}, "scope")
        self.assertEqual(
            client.responses.calls[0]["instructions"],
            instruction_text("research_planning"),
        )

    def test_review_instruction_forbids_fake_independence_claims(self):
        text = instruction_text("hostile_review").lower()
        self.assertIn("do not claim independence", text)
        self.assertIn("not the final authority", text)


if __name__ == "__main__":
    unittest.main()
