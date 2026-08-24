from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.capabilities import CAPABILITY_CONTRACT_SET, CAPABILITY_CONTRACTS
from swos_runtime.finalizer import finalize_work_order_run
from swos_runtime.governance import verify_manifest
from swos_runtime.schema_validation import validate_frozen_run_schemas
from swos_runtime.work_orders import WorkOrderError, WorkOrderRun


class HostNativeFinalizerTests(unittest.TestCase):
    def _adapter(self):
        capabilities = {
            name: {"level": "native", "contract": contract}
            for name, contract in CAPABILITY_CONTRACTS.items()
        }
        for name in ("citation_support_audit", "hostile_review"):
            capabilities[name].update(
                {
                    "review_mode": "same-host-separate-context",
                    "independence": "limited",
                    "blind_review_supported": False,
                    "independence_limitations": ["same host/model family may be used"],
                    "assurance": ["bounded", "declared"],
                }
            )
        return {
            "contract_set": CAPABILITY_CONTRACT_SET,
            "adapter": "future-subscription",
            "model_host": "Future Host",
            "execution_mode": "host_native_subscription",
            "api_key_used": False,
            "paid_api_calls": 0,
            "capabilities": capabilities,
        }

    def _provenance(self):
        return {
            "adapter": "future-subscription",
            "model_host": "Future Host",
            "model": "future-model",
            "execution_mode": "host_native_subscription",
        }

    def _submit(self, run, payload):
        payload = dict(payload)
        payload.setdefault("contract", CAPABILITY_CONTRACTS[run.status()["next_stage"]])
        payload["provenance"] = self._provenance()
        run.submit(payload)

    @staticmethod
    def _sources():
        return [
            {
                "source_id": "host-a",
                "title": "Source A",
                "url": "https://example.org/a",
                "source_type": "scholarly",
                "provider": "host_web",
                "text": (
                    "Source A directly supports the first carefully bounded proposition in this test. "
                    "Source A also supports the second independent proposition without adding extra scope."
                ),
                "metadata_verified": True,
            },
            {
                "source_id": "host-b",
                "title": "Source B",
                "url": "https://example.org/b",
                "source_type": "scholarly",
                "provider": "host_web",
                "text": (
                    "Source B directly supports the third carefully bounded proposition in this test. "
                    "Source B also supports the fourth independent proposition without adding extra scope."
                ),
                "metadata_verified": True,
            },
            {
                "source_id": "host-c",
                "title": "Source C",
                "url": "https://example.org/c",
                "source_type": "scholarly",
                "provider": "host_web",
                "text": (
                    "Source C identifies an important limitation that prevents the conclusion from becoming universal."
                ),
                "metadata_verified": True,
            },
        ]

    @staticmethod
    def _claims(include_limitation=True):
        fifth_stance = "limitation" if include_limitation else "support"
        return [
            {
                "claim": "The first bounded proposition is supported.",
                "source_id": "host-a",
                "exact_quote": "Source A directly supports the first carefully bounded proposition in this test.",
                "stance": "support",
                "confidence": "high",
            },
            {
                "claim": "The second bounded proposition is supported.",
                "source_id": "host-a",
                "exact_quote": "Source A also supports the second independent proposition without adding extra scope.",
                "stance": "support",
                "confidence": "high",
            },
            {
                "claim": "The third bounded proposition is supported.",
                "source_id": "host-b",
                "exact_quote": "Source B directly supports the third carefully bounded proposition in this test.",
                "stance": "support",
                "confidence": "high",
            },
            {
                "claim": "The fourth bounded proposition is supported.",
                "source_id": "host-b",
                "exact_quote": "Source B also supports the fourth independent proposition without adding extra scope.",
                "stance": "support",
                "confidence": "high",
            },
            {
                "claim": "The conclusion has an important limitation.",
                "source_id": "host-c",
                "exact_quote": "Source C identifies an important limitation that prevents the conclusion from becoming universal.",
                "stance": fifth_stance,
                "confidence": "high",
            },
        ]

    @staticmethod
    def _article():
        body = " ".join(["analysis"] * 465)
        return f"# Governed Test Article\n\n{body} [S1] [S2] [S3]."

    def _ready_run(self, root, *, include_limitation=True):
        run = WorkOrderRun.start(
            request={
                "topic": "How should a governed research pipeline constrain its conclusions?",
                "length": 500,
                "audience": "intelligent general reader",
                "style": "scholarly-natural",
                "depth": "rigorous",
            },
            adapter_manifest=self._adapter(),
            root=root,
        )
        self._submit(
            run,
            {
                "research_question": "How should a governed research pipeline constrain its conclusions?",
                "scope": "A bounded methodological test.",
                "queries": ["query one", "query two", "query three"],
                "rival_theses": ["Strong conclusion", "Qualified conclusion"],
                "known_uncertainties": [],
                "out_of_scope": [],
            },
        )
        self._submit(run, {"sources": self._sources()})
        self._submit(
            run,
            {
                "scores": [
                    {"source_id": "host-a", "score": 95, "reason": "direct"},
                    {"source_id": "host-b", "score": 92, "reason": "direct"},
                    {"source_id": "host-c", "score": 90, "reason": "limitation"},
                ],
            },
        )
        self._submit(run, {"claims": self._claims(include_limitation=include_limitation)})
        self._submit(
            run,
            {
                "audits": [
                    {"index": index, "support_level": "directly_supports", "reason": "exact support"}
                    for index in range(5)
                ]
            },
        )
        self._submit(
            run,
            {
                "thesis": "Governed research should preserve scope and limitations.",
                "nodes": [
                    {
                        "local_id": "n1",
                        "node_type": "claim",
                        "statement": "The conclusion should remain bounded by verified evidence.",
                        "evidence_indices": [0, 1, 2, 3, 4],
                    },
                    {
                        "local_id": "n2",
                        "node_type": "qualifier",
                        "statement": "The limitation prevents universalisation.",
                        "evidence_indices": [4],
                    },
                ],
                "edges": [
                    {"from_local_id": "n2", "to_local_id": "n1", "relation": "qualifies"}
                ],
            },
        )
        article = self._article()
        self._submit(run, {"article": article})
        self._submit(run, {"candidate": article})
        self._submit(run, {"status": "PASS", "reason": "identity", "issues": []})
        self._submit(
            run,
            {
                "reviews": [
                    {
                        "role": "hostile_reviewer",
                        "verdict": "pass",
                        "findings": [],
                    }
                ]
            },
        )
        self.assertEqual(run.status()["status"], "READY_TO_FINALISE")
        return run

    def test_subscription_run_finalises_without_provider_identity_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._ready_run(tmp)
            output = Path(tmp) / "output"
            outcome = finalize_work_order_run(run, output)
            self.assertEqual(outcome.status, "APPROVED", outcome.blocking_reasons)
            self.assertEqual(validate_frozen_run_schemas(output), [])

            control = json.loads((output / "run-control.json").read_text(encoding="utf-8"))
            self.assertEqual(control["cross_encoder"]["capability"], "semantic_rerank")
            self.assertEqual(control["cross_encoder"]["contract"], "swos.semantic-rerank.v1")
            self.assertTrue(control["cross_encoder"]["contract_passed"])
            self.assertEqual(control["execution"]["adapter"], "future-subscription")
            self.assertFalse(control["execution"]["api_key_used"])
            self.assertEqual(control["execution"]["paid_api_calls"], 0)
            self.assertEqual(control["authority_boundary"], "Models propose or judge. SWOS decides.")

            assurance = json.loads((output / "review-assurance.json").read_text(encoding="utf-8"))
            self.assertEqual(assurance["hostile_review"]["independence"], "limited")
            self.assertFalse(assurance["hostile_review"]["blind_review_supported"])
            review = json.loads((output / "review-summary.json").read_text(encoding="utf-8"))
            self.assertTrue(review)
            self.assertFalse(review[0]["blind_review"])

            judgements = json.loads((output / "judgement-evidence.json").read_text(encoding="utf-8"))
            self.assertTrue(judgements["records"])
            self.assertTrue(
                all(
                    item["authority"] == "advisory_evidence_for_swos_governance"
                    for item in judgements["records"]
                )
            )

            bundle = json.loads((output / "host-bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(bundle["bundle_role"], "replay_interchange_debug_reproducibility")

            manifest = json.loads((output / "run-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(verify_manifest(output, manifest))

    def test_missing_counter_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._ready_run(tmp, include_limitation=False)
            outcome = finalize_work_order_run(run, Path(tmp) / "output")
            self.assertEqual(outcome.status, "REVIEW_REQUIRED")
            self.assertTrue(
                any("counter-evidence" in reason for reason in outcome.blocking_reasons)
            )

    def test_quote_not_in_source_is_rejected_before_argument_or_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = WorkOrderRun.start(
                request={"topic": "Question", "length": 500},
                adapter_manifest=self._adapter(),
                root=tmp,
            )
            self._submit(
                run,
                {
                    "research_question": "Question",
                    "scope": "scope",
                    "queries": ["q1", "q2", "q3"],
                    "rival_theses": ["a", "b"],
                },
            )
            self._submit(run, {"sources": self._sources()})
            self._submit(run, {"scores": []})
            bad = self._claims()
            bad[0]["exact_quote"] = "This quotation is not present in the retrieved source text at all."
            with self.assertRaisesRegex(WorkOrderError, "does not occur"):
                self._submit(run, {"claims": bad})
            self.assertEqual(run.status()["next_stage"], "evidence_extraction")
            self.assertEqual(run.status()["submissions"], 3)

    def test_unknown_review_independence_blocks_automatic_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._ready_run(tmp)
            run.state["adapter"]["capabilities"]["hostile_review"].pop("independence", None)
            run._save()
            outcome = finalize_work_order_run(run, Path(tmp) / "output")
            self.assertEqual(outcome.status, "REVIEW_REQUIRED")
            self.assertTrue(any("review independence" in reason for reason in outcome.blocking_reasons))


if __name__ == "__main__":
    unittest.main()
