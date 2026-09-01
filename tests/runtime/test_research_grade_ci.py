"""Static contract tests for the ordinary, offline Research Grade CI job."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "research-grade-ci.yml"


class ResearchGradeCIContractTests(unittest.TestCase):
    def test_workflow_runs_compatibility_and_example_validation(self) -> None:
        self.assertTrue(WORKFLOW.is_file())
        text = WORKFLOW.read_text(encoding="utf-8")
        for command in (
            "python tools/validate_contract_examples.py",
            "python tools/validate_schemas.py --strict",
            "python -m unittest tests.runtime.test_research_grade_compatibility",
            "python -m unittest tests.runtime.test_research_grade_schemas",
        ):
            self.assertIn(command, text)

    def test_workflow_checks_frozen_v1_bytes_and_stays_offline_for_models(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("v1-compatibility-manifest.json", text)
        self.assertIn("git diff --exit-code", text)
        self.assertIn("OPENAI_API_KEY", text)
        self.assertIn("MODEL_REGISTRY_TOKEN", text)
        self.assertNotIn("huggingface-cli download", text)
        self.assertNotIn("sentence-transformers", text)
        self.assertNotIn("pytest --run-live", text)


if __name__ == "__main__":
    unittest.main()
