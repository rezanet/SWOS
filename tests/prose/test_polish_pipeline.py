from __future__ import annotations

import json
import unittest

from swos_prose.models import VerificationStatus
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.providers.openai_rewrite import (
    OpenAIResponsesRewriteProvider,
    POLISH_REWRITER_INSTRUCTIONS,
)
from swos_prose.providers.rewrite_mock import StaticRewriteProvider
from swos_prose.rewrite import polish_text


def proposition(prop_id: str, text: str) -> dict:
    return {
        "id": prop_id,
        "text": text,
        "subject": None,
        "relation": None,
        "object": None,
        "modality": None,
        "modality_scope": None,
        "attribution": None,
        "causal_force": "none",
        "temporal_relation": None,
        "normative_stance": "neutral",
        "relation_sign": "neutral",
        "claim_type": "methodological",
        "epistemic_type": "method",
    }


def equivalent_payload(source: str, candidate: str) -> dict:
    return {
        "equivalent": True,
        "independent_of_rewriter": True,
        "source_propositions": [proposition("p1", source)],
        "candidate_propositions": [proposition("c1", candidate)],
        "source_to_candidate": [{
            "source_id": "p1",
            "candidate_ids": ["c1"],
            "preserved": True,
            "modality_preserved": True,
            "scope_preserved": True,
            "attribution_preserved": True,
            "causal_force_preserved": True,
            "relational_direction_preserved": True,
            "confidence": 0.99,
            "reason": "Equivalent polish paraphrase.",
        }],
        "candidate_to_source": [{
            "candidate_id": "c1",
            "source_ids": ["p1"],
            "licensed": True,
            "new_claim": False,
            "confidence": 0.99,
            "reason": "Licensed by source.",
        }],
        "unresolved": [],
        "notes": [],
    }


class PolishPipelineTests(unittest.TestCase):
    def test_safe_polish_candidate_is_returned(self):
        source = "The analysis was performed using a t-test."
        candidate = "The analysis used a t-test."
        rewriter = StaticRewriteProvider(candidate)
        verifier = StaticSemanticVerifierProvider(equivalent_payload(source, candidate))

        result = polish_text(
            source=source,
            rewrite_provider=rewriter,
            verifier_provider=verifier,
            assurance="strict",
        )

        self.assertEqual(result.verification_status, VerificationStatus.PASS.value)
        self.assertEqual(result.final_text, candidate)
        self.assertFalse(result.used_source_fallback)
        self.assertTrue(result.safe_for_automatic_use)

    def test_deterministic_number_drift_falls_back_before_verifier(self):
        source = "The response rate was 18.7%."
        candidate = "The response rate was 19%."
        rewriter = StaticRewriteProvider(candidate)
        verifier = StaticSemanticVerifierProvider(equivalent_payload(source, candidate))

        result = polish_text(
            source=source,
            rewrite_provider=rewriter,
            verifier_provider=verifier,
            assurance="strict",
        )

        self.assertEqual(result.verification_status, VerificationStatus.REJECT.value)
        self.assertEqual(result.final_text, source)
        self.assertTrue(result.used_source_fallback)
        self.assertEqual(verifier.calls, 0)

    def test_changed_candidate_without_verifier_falls_back(self):
        source = "This sentence is rather unnecessarily wordy in its construction."
        candidate = "This sentence is unnecessarily wordy."

        result = polish_text(
            source=source,
            rewrite_provider=StaticRewriteProvider(candidate),
            verifier_provider=None,
            assurance="strict",
        )

        self.assertEqual(result.verification_status, VerificationStatus.REVIEW.value)
        self.assertEqual(result.final_text, source)
        self.assertTrue(result.used_source_fallback)

    def test_repair_status_is_not_released_before_repair_loop_exists(self):
        source = "The analysis was performed using a t-test."
        candidate = "The analysis used a t-test."
        verifier = StaticSemanticVerifierProvider({
            "equivalent": True,
            "independent_of_rewriter": True,
            "deltas": [{
                "type": "condition_changed",
                "severity": "blocker",
                "repairable": True,
                "confidence": 1.0,
                "source_span": source,
                "candidate_span": candidate,
                "explanation": "Synthetic repairable delta for orchestration test.",
            }],
            "notes": [],
        })

        result = polish_text(
            source=source,
            rewrite_provider=StaticRewriteProvider(candidate),
            verifier_provider=verifier,
            assurance="standard",
        )

        self.assertEqual(result.verification_status, VerificationStatus.REPAIR.value)
        self.assertEqual(result.final_text, source)
        self.assertTrue(result.used_source_fallback)

    def test_protected_anchors_are_passed_verbatim_to_rewriter(self):
        source = "The response rate was 18.7% [12]."
        rewriter = StaticRewriteProvider(source)

        result = polish_text(
            source=source,
            rewrite_provider=rewriter,
            verifier_provider=None,
        )

        self.assertEqual(result.final_text, source)
        anchors = {item["text"] for item in rewriter.last_request["protected_anchors"]}
        self.assertIn("18.7%", anchors)
        self.assertIn("[12]", anchors)
        self.assertEqual(rewriter.last_request["mode"], "polish")

    def test_empty_source_is_a_noop_without_provider_call(self):
        rewriter = StaticRewriteProvider("unexpected")
        result = polish_text(
            source="   ",
            rewrite_provider=rewriter,
            verifier_provider=None,
        )
        self.assertEqual(result.final_text, "   ")
        self.assertEqual(rewriter.calls, 0)

    def test_invalid_assurance_fails_before_rewriter_call(self):
        rewriter = StaticRewriteProvider("candidate")
        with self.assertRaises(ValueError):
            polish_text(
                source="Source prose.",
                rewrite_provider=rewriter,
                verifier_provider=None,
                assurance="unsafe",
            )
        self.assertEqual(rewriter.calls, 0)

    def test_malformed_rewrite_provider_result_falls_back(self):
        class MalformedRewriteProvider:
            def rewrite(self, **kwargs):
                return {"candidate_text": "Changed prose."}

        source = "Source prose."
        result = polish_text(
            source=source,
            rewrite_provider=MalformedRewriteProvider(),
            verifier_provider=None,
        )
        self.assertEqual(result.final_text, source)
        self.assertTrue(result.used_source_fallback)
        self.assertIsNone(result.verification)


class FakeResponse:
    def __init__(self, candidate: str):
        self.output_text = json.dumps({"candidate_text": candidate})
        self.id = "resp-polish-test"
        self.usage = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}


class FakeResponses:
    def __init__(self, candidate: str):
        self.candidate = candidate
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.candidate)


class FakeClient:
    def __init__(self, candidate: str):
        self.responses = FakeResponses(candidate)


class OpenAIRewriteAdapterTests(unittest.TestCase):
    def test_openai_polish_adapter_uses_strict_stateless_output(self):
        source = "The response rate was 18.7%."
        client = FakeClient("The response rate was 18.7%.")
        provider = OpenAIResponsesRewriteProvider(model="test-model", client=client)

        proposal = provider.rewrite(
            source=source,
            mode="polish",
            protected_anchors=[{"kind": "number", "text": "18.7%"}],
            rewrite_plan={"objectives": ["improve clarity"]},
        )

        self.assertEqual(proposal.candidate_text, source)
        self.assertEqual(proposal.token_usage["total_tokens"], 120)
        call = client.responses.calls[0]
        self.assertFalse(call["store"])
        self.assertEqual(call["temperature"], 0.0)
        self.assertTrue(call["text"]["format"]["strict"])
        request_payload = json.loads(call["input"])
        self.assertEqual(request_payload["protected_anchors"][0]["text"], "18.7%")
        self.assertIn("protected anchor", POLISH_REWRITER_INSTRUCTIONS.casefold())
        self.assertIn("do not add", POLISH_REWRITER_INSTRUCTIONS.casefold())

    def test_openai_polish_adapter_rejects_unimplemented_mode(self):
        provider = OpenAIResponsesRewriteProvider(model="test-model", client=FakeClient("x"))
        with self.assertRaises(ValueError):
            provider.rewrite(
                source="x",
                mode="naturalise",
                protected_anchors=[],
                rewrite_plan={},
            )


if __name__ == "__main__":
    unittest.main()
