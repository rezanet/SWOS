"""Dependency manifest and lock contract tests."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ResearchGradeDependencyTests(unittest.TestCase):
    def test_optional_dependencies_have_pinned_licences_and_distribution_hashes(self) -> None:
        manifest = ROOT / "config/research-grade-dependencies.md"
        self.assertTrue(manifest.is_file())
        text = manifest.read_text(encoding="utf-8")
        for package in ("rdflib", "pyshacl", "prov", "sentence-transformers"):
            self.assertIn(package, text)
        hashes = re.findall(r"sha256:[0-9a-f]{64}", text)
        self.assertGreaterEqual(len(hashes), 4)
        self.assertIn("License", text)
        self.assertIn("ordinary CI", text)

    def test_pyproject_and_developer_lock_reference_the_manifest_packages(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        lock = (ROOT / "requirements-dev.lock").read_text(encoding="utf-8")
        for group in ("ontology", "training", "prov", "research-grade"):
            self.assertIn(group, pyproject)
        for package in (
            "rdflib==7.6.0",
            "pyshacl==0.40.1",
            "prov==3.1.0",
            "sentence-transformers==6.0.1",
        ):
            self.assertIn(package, lock)


if __name__ == "__main__":
    unittest.main()
