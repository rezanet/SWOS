"""Credential-free, network-free ordinary CI checks for Research Grade."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ResearchGradeOfflineTests(unittest.TestCase):
    def test_bounded_safety_mutation_harness_kills_all_frozen_mutants(self) -> None:
        script = ROOT / "tools/run_mutation_checks.py"
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "mutation-report.json"
            result = subprocess.run(
                [sys.executable, str(script), "--report", str(report_path)],
                cwd=ROOT,
                env={
                    **os.environ,
                    "OPENAI_API_KEY": "SENTINEL_OPENAI_KEY",
                    "MODEL_REGISTRY_TOKEN": "SENTINEL_MODEL_TOKEN",
                    "HF_TOKEN": "SENTINEL_HF_TOKEN",
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual("2.0.0", report["schema_version"])
        self.assertEqual("passed", report["status"])
        self.assertGreaterEqual(report["mutant_count"], 4)
        self.assertEqual(report["mutant_count"], report["killed_count"])
        self.assertEqual([], report["surviving_mutants"])
        self.assertEqual([], report["error_mutants"])
        self.assertNotIn("SENTINEL", result.stdout + result.stderr)

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

        quality_workflow = (ROOT / ".github/workflows/swos-quality.yml").read_text(encoding="utf-8")
        self.assertIn("python tools/run_mutation_checks.py", quality_workflow)


if __name__ == "__main__":
    unittest.main()
