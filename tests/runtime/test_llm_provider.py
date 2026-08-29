from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from swos_runtime.llm import OpenAIStageProvider


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        value = self.outputs.pop(0)
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(
            id=f"resp-{len(self.calls)}",
            output_text=value,
            usage={"input_tokens": 100, "output_tokens": 40, "total_tokens": 140},
        )


class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


class StageProviderTests(unittest.TestCase):
    def test_json_and_text_calls_are_stateless_and_recorded(self):
        client = FakeClient([json.dumps({"value": "ok"}), "Draft text"])
        provider = OpenAIStageProvider(model="writer", review_model="reviewer", client=client)
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        }
        result = provider.json_call(
            "unit_json",
            "Return JSON.",
            {"input": 1},
            schema,
            review=True,
            max_output_tokens=250,
        )
        text = provider.text_call("unit_text", "Return text.", {"input": 2})
        self.assertEqual(result, {"value": "ok"})
        self.assertEqual(text, "Draft text")
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(provider.calls[0].model, "reviewer")
        self.assertEqual(provider.calls[1].model, "writer")
        self.assertEqual(provider.calls[0].total_tokens, 140)
        self.assertFalse(client.responses.calls[0]["store"])
        self.assertEqual(
            client.responses.calls[0]["text"]["format"]["type"],
            "json_schema",
        )

    def test_plan_review_repair_uses_structured_query_contract(self):
        output = {
            "research_goal": "Find a direct documented counterexample.",
            "queries": [
                "historical pigment trade name multiple compositions",
                "museum conservation pigment synonym chemical identity",
            ],
        }
        client = FakeClient([json.dumps(output)])
        provider = OpenAIStageProvider(model="writer", client=client)
        result = provider.plan_review_repair(
            "Why historical pigment names are ambiguous",
            [
                {
                    "category": "unsupported_claim",
                    "description": "Need a direct historical example.",
                    "required_action": "Research a documented case.",
                }
            ],
        )
        self.assertEqual(result, output)
        call = client.responses.calls[0]
        self.assertIn("blocking_findings", call["input"])
        self.assertIn("review_research_plan", call["text"]["format"]["name"])
        self.assertFalse(call["store"])

    def test_empty_and_non_object_structured_outputs_fail_closed(self):
        provider = OpenAIStageProvider(client=FakeClient(["", "[]"]))
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
            "required": [],
        }
        with self.assertRaisesRegex(ValueError, "returned no structured output"):
            provider.json_call("empty", "x", {}, schema)
        with self.assertRaisesRegex(ValueError, "did not return an object"):
            provider.json_call("array", "x", {}, schema)

    def test_empty_text_output_fails_closed(self):
        provider = OpenAIStageProvider(client=FakeClient(["   "]))
        with self.assertRaisesRegex(ValueError, "returned no text"):
            provider.text_call("empty_text", "x", {})

    def test_usage_accepts_attribute_object_and_none(self):
        usage = SimpleNamespace(input_tokens=4, output_tokens=5, total_tokens=9)
        response = SimpleNamespace(usage=usage)
        self.assertEqual(
            OpenAIStageProvider._usage(response),
            {"input_tokens": 4, "output_tokens": 5, "total_tokens": 9},
        )
        self.assertIsNone(OpenAIStageProvider._usage(SimpleNamespace(usage=None)))


if __name__ == "__main__":
    unittest.main()
