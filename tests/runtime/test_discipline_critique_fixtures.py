"""Fixture contract for every supported discipline pack."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from swos_runtime.discipline_critique import DisciplineCritic
from swos_runtime.discipline_ontology import SUPPORTED_DISCIPLINES, DisciplineOntologyRegistry

ROOT = Path(__file__).resolve().parents[2]


class DisciplineCritiqueFixtureTests(unittest.TestCase):
    def test_each_pack_has_reviewed_positive_negative_boundary_and_cross_cases(self) -> None:
        manifest = ROOT / "discipline-packs" / "manifest-v2.json"
        registry = DisciplineOntologyRegistry().load(manifest)
        critic = DisciplineCritic(registry)
        for discipline in SUPPORTED_DISCIPLINES:
            fixture = json.loads(
                (
                    ROOT / "evals" / "fixtures" / "discipline-critique" / f"{discipline}.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                {"positive", "negative", "boundary", "cross_discipline"}, set(fixture["cases"])
            )
            self.assertTrue(fixture["review"]["adjudicated"])
            profile = registry.profile(discipline)
            for case in fixture["cases"].values():
                report = critic.critique(
                    discipline=profile,
                    research_plan=case["research_plan"],
                    evidence_matrix=case["evidence_matrix"],
                    draft=case["draft"],
                )
                self.assertEqual(discipline, report.discipline)
                self.assertTrue(report.ontology_digest)


if __name__ == "__main__":
    unittest.main()
