"""Static contract tests for the ordinary, offline Research Grade CI job."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "research-grade-ci.yml"
PROV_WORKFLOW = ROOT / ".github" / "workflows" / "prov-certification.yml"
REQUIRED_PR_WORKFLOWS = (
    ".github/workflows/swos-ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/research-grade-ci.yml",
    ".github/workflows/swos-prose-benchmark.yml",
    ".github/workflows/swos-portability-gate.yml",
    ".github/workflows/swos-quality.yml",
)
EXACT_PR_HEAD_REF = "ref: ${{ github.event.pull_request.head.sha || github.sha }}"


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

    def test_required_pr_workflows_check_out_the_exact_pr_head(self) -> None:
        for relative in REQUIRED_PR_WORKFLOWS:
            with self.subTest(workflow=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                checkout_count = text.count("uses: actions/checkout@v4")
                self.assertGreater(checkout_count, 0)
                self.assertEqual(checkout_count, text.count(EXACT_PR_HEAD_REF))

    def test_mutation_evidence_is_bound_to_the_checked_out_head(self) -> None:
        text = (ROOT / ".github/workflows/swos-quality.yml").read_text(encoding="utf-8")
        self.assertIn("SWOS_EXPECTED_SOURCE_SHA", text)
        self.assertIn("--expected-source-sha", text)

    def test_prov_certification_installs_release_validators(self) -> None:
        self.assertTrue(PROV_WORKFLOW.is_file())
        text = PROV_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(".[research-grade]", text)
        self.assertIn("python tools/certify_prov_roundtrip.py", text)

    def test_prov_certification_runs_the_frozen_corpus_manifest(self) -> None:
        text = PROV_WORKFLOW.read_text(encoding="utf-8")
        corpus_input = text.split("corpus_manifest:", 1)[1].split("oracle:", 1)[0]
        self.assertIn("required: true", corpus_input)
        self.assertNotIn("default:", corpus_input)
        self.assertIn("--corpus-manifest", text)
        self.assertNotIn("--epg", text)


if __name__ == "__main__":
    unittest.main()
