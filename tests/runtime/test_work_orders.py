from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swos_runtime.capabilities import CAPABILITY_CONTRACTS, CAPABILITY_CONTRACT_SET
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
            run.submit(
                {
                    "contract": "swos.research-planning.v1",
                    "research_question": "A question",
                    "scope": "scope",
                    "queries": ["q1", "q2", "q3"],
                    "rival_theses": ["r1", "r2"],
                    "provenance": self._provenance(),
                }
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
            run.submit(
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
                    ],
                    "provenance": self._provenance(),
                }
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
            run.submit(
                {
                    "reviews": [{"role": "hostile_reviewer", "findings": []}],
                    "provenance": self._provenance(),
                }
            )
            self.assertEqual(run.status()["status"], "READY_TO_FINALISE")
            self.assertIsNone(run.work_order())


if __name__ == "__main__":
    unittest.main()
