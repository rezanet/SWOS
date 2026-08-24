from __future__ import annotations

import json
import tempfile
import unittest

from swos_runtime.capabilities import CAPABILITY_CONTRACT_SET, CAPABILITY_CONTRACTS
from swos_runtime.work_orders import WorkOrderError, WorkOrderRun


class WorkOrderTests(unittest.TestCase):
    def _adapter(self):
        capabilities = {
            name: {"level": "native", "contract": contract}
            for name, contract in CAPABILITY_CONTRACTS.items()
        }
        return {
            "contract_set": CAPABILITY_CONTRACT_SET,
            "adapter": "codex-subscription",
            "model_host": "ChatGPT/Codex",
            "execution_mode": "host_native_subscription",
            "api_key_used": False,
            "paid_api_calls": 0,
            "capabilities": capabilities,
        }

    def _provenance(self):
        return {
            "adapter": "codex-subscription",
            "model_host": "ChatGPT/Codex",
            "model": "host-model",
            "execution_mode": "host_native_subscription",
        }

    def _submit(self, run, payload):
        payload = dict(payload)
        payload.setdefault("contract", CAPABILITY_CONTRACTS[run.status()["next_stage"]])
        payload["provenance"] = self._provenance()
        return run.submit(payload)

    def test_swos_chooses_next_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = WorkOrderRun.start(
                request={"topic": "A question"},
                adapter_manifest=self._adapter(),
                root=tmp,
            )
            order = run.work_order()
            self.assertEqual(order["next_stage"], "research_planning")
            self.assertEqual(order["contract"], "swos.research-planning.v1")
            self._submit(
                run,
                {
                    "research_question": "A question",
                    "scope": "scope",
                    "queries": ["q1", "q2", "q3"],
                    "rival_theses": ["r1", "r2"],
                },
            )
            self.assertEqual(run.work_order()["next_stage"], "source_retrieval")

    def test_host_cannot_submit_for_wrong_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = WorkOrderRun.start(
                request={"topic": "A question"},
                adapter_manifest=self._adapter(),
                root=tmp,
            )
            provenance = self._provenance()
            provenance["adapter"] = "different-host"
            with self.assertRaises(WorkOrderError):
                run.submit(
                    {
                        "research_question": "A question",
                        "scope": "scope",
                        "queries": ["q1", "q2", "q3"],
                        "rival_theses": ["r1", "r2"],
                        "provenance": provenance,
                    }
                )

    def test_review_blocker_routes_to_revision_not_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = WorkOrderRun.start(
                request={"topic": "A question"},
                adapter_manifest=self._adapter(),
                root=tmp,
            )
            run.state["stage"] = "hostile_review"
            run._save()
            self._submit(
                run,
                {
                    "reviews": [
                        {
                            "role": "hostile_reviewer",
                            "findings": [
                                {
                                    "severity": "major",
                                    "category": "unsupported_claim",
                                    "description": "repair it",
                                }
                            ],
                        }
                    ]
                },
            )
            self.assertEqual(run.status()["next_stage"], "revision")
            self.assertEqual(run.status()["status"], "ACTIVE")

    def test_no_blockers_reaches_ready_to_finalise(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = WorkOrderRun.start(
                request={"topic": "A question"},
                adapter_manifest=self._adapter(),
                root=tmp,
            )
            run.state["stage"] = "hostile_review"
            run._save()
            self._submit(
                run,
                {"reviews": [{"role": "hostile_reviewer", "findings": []}]},
            )
            self.assertEqual(run.status()["status"], "READY_TO_FINALISE")
            self.assertIsNone(run.work_order())

    def test_subscription_flow_is_swos_driven_and_exports_replay_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = WorkOrderRun.start(
                request={
                    "topic": "Can a machine be a witness?",
                    "length": 2500,
                    "audience": "intelligent general reader",
                    "style": "scholarly-natural",
                    "depth": "rigorous",
                },
                adapter_manifest=self._adapter(),
                root=tmp,
            )

            expected = [
                "research_planning",
                "source_retrieval",
                "semantic_rerank",
                "evidence_extraction",
                "citation_support_audit",
                "argument_construction",
                "draft_generation",
                "prose_transformation",
                "semantic_verification",
                "hostile_review",
            ]
            observed = []

            observed.append(run.work_order()["next_stage"])
            self._submit(
                run,
                {
                    "research_question": "Can a machine be a witness?",
                    "scope": "comparative legal analysis",
                    "queries": ["q1", "q2", "q3"],
                    "rival_theses": ["yes", "no"],
                    "known_uncertainties": [],
                },
            )

            observed.append(run.work_order()["next_stage"])
            self._submit(
                run,
                {
                    "sources": [
                        {
                            "source_id": "src-1",
                            "title": "Authority",
                            "url": "https://example.org/authority",
                            "source_type": "primary_law",
                            "provider": "host_web",
                            "text": "The witness rule is stated here exactly.",
                            "metadata_verified": True,
                        }
                    ]
                },
            )

            observed.append(run.work_order()["next_stage"])
            self._submit(
                run,
                {
                    "capability": "semantic_rerank",
                    "scores": [{"source_id": "src-1", "score": 95, "reason": "direct"}],
                },
            )

            observed.append(run.work_order()["next_stage"])
            self._submit(
                run,
                {
                    "claims": [
                        {
                            "claim": "The authority states the witness rule.",
                            "source_id": "src-1",
                            "exact_quote": "The witness rule is stated here exactly.",
                        }
                    ]
                },
            )

            observed.append(run.work_order()["next_stage"])
            self._submit(
                run,
                {"audits": [{"index": 0, "support_level": "directly_supports"}]},
            )

            observed.append(run.work_order()["next_stage"])
            self._submit(
                run,
                {
                    "thesis": "The category requires governed legal analysis.",
                    "nodes": [{"local_id": "n1", "node_type": "claim", "statement": "Claim"}],
                    "edges": [],
                },
            )

            observed.append(run.work_order()["next_stage"])
            self._submit(run, {"article": "# Draft\n\nA supported article [S1]."})

            observed.append(run.work_order()["next_stage"])
            self._submit(
                run,
                {"candidate": "# Draft\n\nA supported article [S1]."},
            )

            observed.append(run.work_order()["next_stage"])
            self._submit(run, {"status": "PASS", "deltas": []})

            observed.append(run.work_order()["next_stage"])
            self._submit(
                run,
                {"reviews": [{"role": "hostile_reviewer", "findings": []}]},
            )

            self.assertEqual(observed, expected)
            self.assertEqual(run.status()["status"], "READY_TO_FINALISE")
            self.assertEqual(run.status()["submissions"], len(expected))
            self.assertFalse((run.run_dir / "next-work.json").exists())

            bundle_path = run.export_host_bundle()
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            self.assertEqual(bundle["host"]["adapter"], "codex-subscription")
            self.assertEqual(bundle["host"]["execution_mode"], "host_native_subscription")
            self.assertFalse(bundle["host"]["api_key_used"])
            self.assertEqual(bundle["host"]["paid_api_calls"], 0)
            self.assertEqual(bundle["stages"]["draft"], "# Draft\n\nA supported article [S1].")
            self.assertTrue(bundle["prose"]["safe_for_automatic_use"])

    def test_start_fails_closed_when_adapter_lacks_required_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = self._adapter()
            del adapter["capabilities"]["semantic_rerank"]
            with self.assertRaises(WorkOrderError):
                WorkOrderRun.start(
                    request={"topic": "A question"},
                    adapter_manifest=adapter,
                    root=tmp,
                )


if __name__ == "__main__":
    unittest.main()
