from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from swos_prose.models import VerificationStatus
from swos_prose.pipeline import verify_rewrite
from swos_prose.providers.openai_responses import (
    OPENAI_SEMANTIC_VERIFIER_SCHEMA,
    SEMANTIC_VERIFIER_INSTRUCTIONS,
    OpenAIResponsesSemanticVerifierProvider,
)


def proposition(
    prop_id: str,
    text: str,
    *,
    subject: str | None = None,
    relation: str | None = None,
    object_: str | None = None,
    modality: str | None = None,
    modality_scope: str | None = None,
    attribution: str | None = None,
    causal_force: str | None = "none",
    temporal_relation: str | None = None,
    normative_stance: str | None = "neutral",
):
    return {
        "id": prop_id,
        "text": text,
        "subject": subject,
        "relation": relation,
        "object": object_,
        "modality": modality,
        "modality_scope": modality_scope,
        "attribution": attribution,
        "causal_force": causal_force,
        "temporal_relation": temporal_relation,
        "normative_stance": normative_stance,
    }


def one_to_one_payload(source_prop: dict, candidate_prop: dict) -> dict:
    return {
        "equivalent": True,
        "source_propositions": [source_prop],
        "candidate_propositions": [candidate_prop],
        "source_to_candidate": [
            {
                "source_id": source_prop["id"],
                "candidate_ids": [candidate_prop["id"]],
                "preserved": True,
                "modality_preserved": True,
                "scope_preserved": True,
                "attribution_preserved": True,
                "causal_force_preserved": True,
                "relational_direction_preserved": True,
                "confidence": 0.99,
                "reason": "Equivalent proposition.",
            }
        ],
        "candidate_to_source": [
            {
                "candidate_id": candidate_prop["id"],
                "source_ids": [source_prop["id"]],
                "licensed": True,
                "new_claim": False,
                "confidence": 0.99,
                "reason": "Licensed by source.",
            }
        ],
        "unresolved": [],
        "notes": [],
    }


class FakeResponses:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="resp_test",
            output_text=json.dumps(self.payload),
            usage=SimpleNamespace(input_tokens=111, output_tokens=222, total_tokens=333),
        )


class FakeClient:
    def __init__(self, payload: dict):
        self.responses = FakeResponses(payload)


class OpenAIProviderUnitTests(unittest.TestCase):
    def test_prompt_rejects_similarity_shortcuts_and_requires_modal_scope(self):
        lowered = SEMANTIC_VERIFIER_INSTRUCTIONS.casefold()
        self.assertIn("embedding similarity", lowered)
        self.assertIn("strictly licensed", lowered)
        self.assertIn("modal scope matters", lowered)

    def test_provider_uses_structured_stateless_response_request(self):
        payload = one_to_one_payload(
            proposition("p1", "The model performs poorly.", normative_stance="negative"),
            proposition("c1", "The model underperforms.", normative_stance="negative"),
        )
        client = FakeClient(payload)
        provider = OpenAIResponsesSemanticVerifierProvider(model="test-model", client=client)
        assessment = provider.verify(
            source="The model performs poorly.",
            candidate="The model underperforms.",
            source_anchors=[],
            candidate_anchors=[],
            assurance="strict",
            native_swos_context=None,
        )
        call = client.responses.calls[0]
        self.assertEqual(call["model"], "test-model")
        self.assertNotIn("temperature", call)
        self.assertFalse(call["store"])
        self.assertTrue(call["text"]["format"]["strict"])
        self.assertEqual(call["text"]["format"]["schema"], OPENAI_SEMANTIC_VERIFIER_SCHEMA)
        self.assertEqual(assessment.token_usage["total_tokens"], 333)
        self.assertIn("provider=openai_responses", assessment.notes)

    def test_provider_forwards_explicit_temperature(self):
        payload = one_to_one_payload(
            proposition("p1", "The model performs poorly."),
            proposition("c1", "The model underperforms."),
        )
        client = FakeClient(payload)
        provider = OpenAIResponsesSemanticVerifierProvider(
            model="test-model",
            client=client,
            temperature=0.25,
        )

        provider.verify(
            source="The model performs poorly.",
            candidate="The model underperforms.",
            source_anchors=[],
            candidate_anchors=[],
            assurance="strict",
            native_swos_context=None,
        )

        self.assertEqual(client.responses.calls[0]["temperature"], 0.25)

    def test_modal_scope_relocation_cannot_pass_even_if_provider_boolean_says_preserved(self):
        source = "The data may suggest that X causes Y."
        candidate = "The data suggests that X may cause Y."
        payload = one_to_one_payload(
            proposition(
                "p1",
                source,
                subject="data",
                relation="suggest",
                object_="X causes Y",
                modality="may",
                modality_scope="suggestion",
                causal_force="causal",
            ),
            proposition(
                "c1",
                candidate,
                subject="data",
                relation="suggest",
                object_="X may cause Y",
                modality="may",
                modality_scope="embedded causation",
                causal_force="causal",
            ),
        )
        provider = OpenAIResponsesSemanticVerifierProvider(
            model="test-model", client=FakeClient(payload)
        )
        result = verify_rewrite(
            source=source, candidate=candidate, assurance="strict", verifier_provider=provider
        )
        self.assertEqual(result.status, VerificationStatus.REVIEW)
        self.assertIn(
            "unresolved_equivalence", [item.delta_type.value for item in result.semantic_deltas]
        )

    def test_causal_force_weakening_is_rejected_from_structured_frames(self):
        source = "X caused Y."
        candidate = "X was associated with Y."
        payload = one_to_one_payload(
            proposition(
                "p1", source, subject="X", relation="caused", object_="Y", causal_force="causal"
            ),
            proposition(
                "c1",
                candidate,
                subject="X",
                relation="associated with",
                object_="Y",
                causal_force="association",
            ),
        )
        provider = OpenAIResponsesSemanticVerifierProvider(
            model="test-model", client=FakeClient(payload)
        )
        result = verify_rewrite(
            source=source, candidate=candidate, assurance="strict", verifier_provider=provider
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(
            "causal_strength_changed", [item.delta_type.value for item in result.semantic_deltas]
        )

    def test_temporal_inverse_wording_can_pass_when_canonical_chronology_matches(self):
        source = "The intervention preceded the outcome."
        candidate = "The outcome followed the intervention."
        canonical = "before(intervention,outcome)"
        payload = one_to_one_payload(
            proposition(
                "p1",
                source,
                subject="intervention",
                relation="preceded",
                object_="outcome",
                temporal_relation=canonical,
            ),
            proposition(
                "c1",
                candidate,
                subject="outcome",
                relation="followed",
                object_="intervention",
                temporal_relation=canonical,
            ),
        )
        provider = OpenAIResponsesSemanticVerifierProvider(
            model="test-model", client=FakeClient(payload)
        )
        result = verify_rewrite(
            source=source, candidate=candidate, assurance="strict", verifier_provider=provider
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_negative_performance_lexical_normalisation_can_pass(self):
        source = "The model performs poorly under these conditions."
        candidate = "The model underperforms under these conditions."
        payload = one_to_one_payload(
            proposition(
                "p1",
                source,
                subject="model",
                relation="performs",
                object_="poorly under these conditions",
                normative_stance="negative",
            ),
            proposition(
                "c1",
                candidate,
                subject="model",
                relation="underperforms",
                object_="under these conditions",
                normative_stance="negative",
            ),
        )
        provider = OpenAIResponsesSemanticVerifierProvider(
            model="test-model", client=FakeClient(payload)
        )
        result = verify_rewrite(
            source=source, candidate=candidate, assurance="strict", verifier_provider=provider
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_symmetric_association_swap_can_pass_with_structured_frame_proof(self):
        source = "Depression is associated with a sedentary lifestyle."
        candidate = "A sedentary lifestyle is associated with depression."
        payload = one_to_one_payload(
            proposition(
                "p1",
                source,
                subject="Depression",
                relation="associated with",
                object_="a sedentary lifestyle",
                causal_force="association",
            ),
            proposition(
                "c1",
                candidate,
                subject="A sedentary lifestyle",
                relation="associated with",
                object_="depression",
                causal_force="association",
            ),
        )
        provider = OpenAIResponsesSemanticVerifierProvider(
            model="test-model", client=FakeClient(payload)
        )
        result = verify_rewrite(
            source=source, candidate=candidate, assurance="strict", verifier_provider=provider
        )
        self.assertEqual(result.status, VerificationStatus.PASS)

    def test_temporal_relation_change_is_rejected_even_if_provider_claims_preserved(self):
        source = "The intervention preceded the outcome."
        candidate = "The intervention followed the outcome."
        payload = one_to_one_payload(
            proposition(
                "p1",
                source,
                subject="intervention",
                relation="preceded",
                object_="outcome",
                temporal_relation="before(intervention,outcome)",
            ),
            proposition(
                "c1",
                candidate,
                subject="intervention",
                relation="followed",
                object_="outcome",
                temporal_relation="before(outcome,intervention)",
            ),
        )
        provider = OpenAIResponsesSemanticVerifierProvider(
            model="test-model", client=FakeClient(payload)
        )
        result = verify_rewrite(
            source=source, candidate=candidate, assurance="strict", verifier_provider=provider
        )
        self.assertEqual(result.status, VerificationStatus.REJECT)
        self.assertIn(
            "chronology_changed", [item.delta_type.value for item in result.semantic_deltas]
        )


if __name__ == "__main__":
    unittest.main()
