"""Credential-free, network-free ordinary CI checks for Research Grade."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ResearchGradeOfflineTests(unittest.TestCase):
    def test_ordinary_contract_harness_runs_with_network_trap_and_sentinel_credentials(
        self,
    ) -> None:
        code = """
import socket
class Trap(socket.socket):
    def connect(self, *args, **kwargs):
        raise AssertionError('ordinary CI attempted a network connection')
socket.socket = Trap
from evals.harness.run_evals import run_plane
result = run_plane('retrieval')
assert result['mode'] == 'contract_mode'
assert 'SENTINEL' not in repr(result)
print('offline-ok')
"""
        environment = os.environ.copy()
        environment.update(
            {
                "OPENAI_API_KEY": "SENTINEL_OPENAI_KEY",
                "MODEL_REGISTRY_TOKEN": "SENTINEL_MODEL_TOKEN",
                "HF_TOKEN": "SENTINEL_HF_TOKEN",
            }
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("offline-ok\n", result.stdout)
        self.assertNotIn("SENTINEL", result.stderr)

    def test_ordinary_workflow_contains_no_live_model_or_paid_call_step(self) -> None:
        workflow = (ROOT / ".github/workflows/research-grade-ci.yml").read_text(encoding="utf-8")
        forbidden = ("--run-live", "huggingface-cli download", "openai responses", "curl https")
        for value in forbidden:
            self.assertNotIn(value, workflow.lower())
        self.assertIn('test -z "${OPENAI_API_KEY:-}"', workflow)
        self.assertIn('test -z "${MODEL_REGISTRY_TOKEN:-}"', workflow)


if __name__ == "__main__":
    unittest.main()
