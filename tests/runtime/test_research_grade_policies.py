"""Contract tests for Research Grade policy boundaries."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = ROOT / "governance" / "policies"
EXPECTED = {
    "research-programme-memory-v2.policy.json",
    "rpm-exchange.policy.json",
    "source-diversity.policy.json",
    "media-rights.policy.json",
    "research-grade-promotion.policy.json",
}


class ResearchGradePolicyTests(unittest.TestCase):
    def test_v2_policies_are_explicit_fail_closed_governance_artifacts(self) -> None:
        for name in EXPECTED:
            path = POLICY_DIR / name
            self.assertTrue(path.is_file(), name)
            policy = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("2.0.0", policy["version"], name)
            self.assertIn(policy["default_effect"], {"deny", "escalate"})
            self.assertTrue(policy["rules"], name)
            self.assertTrue(policy["nist_ai_rmf"], name)

    def test_rights_policy_lists_each_distinct_media_action(self) -> None:
        policy = json.loads((POLICY_DIR / "media-rights.policy.json").read_text(encoding="utf-8"))
        actions = policy["rights_actions"]
        self.assertEqual(
            {
                "view",
                "analyse",
                "transform",
                "create_derivative",
                "quote",
                "cache",
                "export",
                "redistribute",
            },
            set(actions),
        )
        self.assertEqual("deny", policy["unknown_rights_effect"])

    def test_policy_document_preserves_v1_memory_relationship(self) -> None:
        document = ROOT / "docs" / "architecture" / "research-grade-v2-governance.md"
        self.assertTrue(document.is_file())
        text = document.read_text(encoding="utf-8")
        self.assertIn("memory-write.policy.json", text)
        self.assertIn("parallel", text)
        self.assertIn("v1", text)


if __name__ == "__main__":
    unittest.main()
