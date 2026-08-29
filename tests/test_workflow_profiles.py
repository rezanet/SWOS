"""Tests for deterministic separation of ordinary and live workflow profiles."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.check_workflow_profiles import inspect_workflow_files

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class WorkflowProfileInspectionTests(unittest.TestCase):
    def test_repository_workflows_have_safe_profile_boundaries(self) -> None:
        self.assertEqual(inspect_workflow_files(REPOSITORY_ROOT), [])

    def test_pull_request_portability_release_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(REPOSITORY_ROOT / ".github", root / ".github")
            workflow = root / ".github" / "workflows" / "swos-portability-gate.yml"
            text = workflow.read_text(encoding="utf-8")
            text = text.replace(
                "if: github.event_name == 'workflow_dispatch'",
                "if: github.event_name == 'workflow_dispatch' || github.event.pull_request.draft == false",
                1,
            )
            workflow.write_text(text, encoding="utf-8")

            errors = inspect_workflow_files(root)

        self.assertTrue(
            any("must not run from pull_request conditions" in error for error in errors)
        )

    def test_provider_job_without_dispatch_guard_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(REPOSITORY_ROOT / ".github", root / ".github")
            workflow = root / ".github" / "workflows" / "swos-prose-benchmark.yml"
            text = workflow.read_text(encoding="utf-8")
            text = text.replace(
                "if: github.event_name == 'workflow_dispatch'",
                "if: env.OPENAI_API_KEY != ''",
                1,
            )
            workflow.write_text(text, encoding="utf-8")

            errors = inspect_workflow_files(root)

        self.assertTrue(
            any("provider job is not manual-dispatch-only" in error for error in errors)
        )

    def test_provider_job_with_compound_dispatch_or_pull_request_guard_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(REPOSITORY_ROOT / ".github", root / ".github")
            workflow = root / ".github" / "workflows" / "swos-prose-benchmark.yml"
            text = workflow.read_text(encoding="utf-8")
            text = text.replace(
                "if: github.event_name == 'workflow_dispatch'",
                "if: github.event_name == 'workflow_dispatch' || github.event_name == 'pull_request'",
                1,
            )
            workflow.write_text(text, encoding="utf-8")

            errors = inspect_workflow_files(root)

        self.assertTrue(
            any("provider job is not manual-dispatch-only" in error for error in errors)
        )

    def test_live_benchmark_cannot_suppress_provider_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(REPOSITORY_ROOT / ".github", root / ".github")
            workflow = root / ".github" / "workflows" / "swos-prose-benchmark.yml"
            text = workflow.read_text(encoding="utf-8")
            text = text.replace(
                "id: live-benchmark\n        run:",
                "id: live-benchmark\n        continue-on-error: true\n        run:",
                1,
            )
            workflow.write_text(text, encoding="utf-8")

            errors = inspect_workflow_files(root)

        self.assertTrue(
            any("must fail closed on provider or benchmark failure" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
