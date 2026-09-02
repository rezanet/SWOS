"""Credential-free, network-free ordinary CI checks for Research Grade."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.run_mutation_checks import (
    _run_probe,
    _source_worktree_clean,
    _subprocess_environment,
    run_mutation_checks,
)

ROOT = Path(__file__).resolve().parents[2]


class ResearchGradeOfflineTests(unittest.TestCase):
    def test_bounded_safety_mutation_harness_kills_all_frozen_mutants(self) -> None:
        script = ROOT / "tools/run_mutation_checks.py"
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "mutation-report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--report",
                    str(report_path),
                    "--expected-source-sha",
                    subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout.strip(),
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    "OPENAI_API_KEY": "SENTINEL_OPENAI_KEY",
                    "MODEL_REGISTRY_TOKEN": "SENTINEL_MODEL_TOKEN",
                    "HF_TOKEN": "SENTINEL_HF_TOKEN",
                    "AWS_SECRET_ACCESS_KEY": "SENTINEL_AWS_KEY",
                    "GITHUB_TOKEN": "SENTINEL_GITHUB_TOKEN",
                    "GH_TOKEN": "SENTINEL_GH_TOKEN",
                },
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
        expected_clean = _source_worktree_clean()
        self.assertEqual(
            0 if expected_clean else 1, result.returncode, result.stdout + result.stderr
        )
        self.assertEqual("2.0.0", report["schema_version"])
        self.assertEqual("passed" if expected_clean else "failed", report["status"])
        self.assertEqual(expected_clean, report["source_worktree_clean"])
        self.assertTrue(report["source_sha_matches_expected"])
        self.assertGreaterEqual(report["mutant_count"], 4)
        self.assertEqual(report["mutant_count"], report["killed_count"])
        self.assertEqual([], report["surviving_mutants"])
        self.assertEqual([], report["error_mutants"])
        self.assertNotIn("SENTINEL", result.stdout + result.stderr)

    def test_mutation_probe_environment_is_an_allowlist(self) -> None:
        with unittest.mock.patch.dict(
            os.environ,
            {
                "AWS_SECRET_ACCESS_KEY": "SENTINEL_AWS_KEY",
                "GITHUB_TOKEN": "SENTINEL_GITHUB_TOKEN",
                "GH_TOKEN": "SENTINEL_GH_TOKEN",
            },
            clear=False,
        ):
            environment = _subprocess_environment(Path("C:/temporary-sandbox"))
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", environment)
        self.assertNotIn("GITHUB_TOKEN", environment)
        self.assertNotIn("GH_TOKEN", environment)
        self.assertEqual(str(Path("C:/temporary-sandbox")), environment["PYTHONPATH"])

    def test_mutation_probe_output_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            (sandbox / "tests" / "runtime").mkdir(parents=True)
            (sandbox / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (sandbox / "tests" / "runtime" / "__init__.py").write_text("", encoding="utf-8")
            (sandbox / "tests" / "runtime" / "test_noisy_probe.py").write_text(
                "import sys\nsys.stdout.write('x' * 200000)\n", encoding="utf-8"
            )
            result = _run_probe(sandbox, "tests.runtime.test_noisy_probe", 10.0, 1024)
        self.assertEqual("error", result["status"])
        self.assertTrue(result["output_limit_exceeded"])
        self.assertLessEqual(result["stdout_bytes"], 1024)

    def test_mutation_success_requires_clean_expected_source(self) -> None:
        mutants = [{"mutant_id": f"m-{index}", "status": "killed"} for index in range(1)]
        with (
            unittest.mock.patch("tools.run_mutation_checks.MUTANTS", tuple()),
            unittest.mock.patch(
                "tools.run_mutation_checks._run_mutations", return_value=([], mutants)
            ),
            unittest.mock.patch(
                "tools.run_mutation_checks._source_worktree_clean", return_value=False
            ),
        ):
            report = run_mutation_checks(expected_source_sha="a" * 40)
        self.assertEqual("failed", report["status"])
        self.assertFalse(report["source_worktree_clean"])

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
