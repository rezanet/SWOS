from __future__ import annotations

import unittest

from swos_runtime.capabilities import (
    AdapterCapabilities,
    CapabilityDeclaration,
    CapabilityError,
    capability_evidence,
    capability_satisfied,
)


class CapabilityContractTests(unittest.TestCase):
    def _adapter(self):
        return AdapterCapabilities(
            adapter="codex-subscription",
            model_host="ChatGPT/Codex",
            execution_mode="host_native_subscription",
            declarations={
                "semantic_rerank": CapabilityDeclaration(
                    name="semantic_rerank",
                    level="native",
                    contract="swos.semantic-rerank.v1",
                    assurance=("joint_query_document_scoring",),
                )
            },
        )

    def test_capability_identity_is_vendor_neutral(self):
        adapter = self._adapter()
        record = capability_evidence(
            capability="semantic_rerank",
            adapter=adapter,
            executed=True,
            model="host-model",
        )
        self.assertEqual(record["capability"], "semantic_rerank")
        self.assertEqual(record["contract"], "swos.semantic-rerank.v1")
        self.assertEqual(record["adapter"], "codex-subscription")
        self.assertTrue(capability_satisfied(record, "semantic_rerank"))

    def test_wrong_contract_fails_closed(self):
        adapter = AdapterCapabilities(
            adapter="bad-adapter",
            model_host="example",
            execution_mode="host_native_subscription",
            declarations={
                "semantic_rerank": CapabilityDeclaration(
                    name="semantic_rerank",
                    level="native",
                    contract="vendor.semantic-rerank.v9",
                )
            },
        )
        with self.assertRaises(CapabilityError):
            adapter.require("semantic_rerank")

    def test_vendor_method_name_cannot_substitute_for_contract(self):
        record = {
            "method": "openai_joint_query_document_cross_encoder",
            "executed": True,
        }
        self.assertFalse(capability_satisfied(record, "semantic_rerank"))


if __name__ == "__main__":
    unittest.main()
