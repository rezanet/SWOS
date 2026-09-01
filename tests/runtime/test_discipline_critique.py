"""Criterion-level, evidence-linked discipline critique contracts."""

from __future__ import annotations

import unittest

from swos_runtime.discipline_critique import DisciplineCritic, aggregate_critiques
from swos_runtime.discipline_ontology import DisciplineOntologyRegistry
from swos_runtime.evaluation import score_discipline_critique, score_ontology_profile


class DisciplineCritiqueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from pathlib import Path

        cls.registry = DisciplineOntologyRegistry().load(
            Path(__file__).resolve().parents[2] / "discipline-packs" / "manifest-v2.json"
        )

    def test_missing_mandatory_move_is_blocking_and_names_evidence_targets(self) -> None:
        profile = self.registry.profile("psychology")
        report = DisciplineCritic(self.registry).critique(
            discipline=profile,
            research_plan={"methods": ["observational"], "claim_type": "causal"},
            evidence_matrix={"rows": []},
            draft={"claims": [{"claim_id": "claim-1", "text": "X causes Y"}]},
        )
        self.assertTrue(report.mandatory_failures)
        self.assertTrue(any(f.severity == "blocking" for f in report.findings))
        self.assertTrue(all(f.claim_refs for f in report.findings))
        self.assertTrue(
            any("design" in (f.reasoning + f.limitation).lower() for f in report.findings)
        )

    def test_supported_criterion_is_evidence_linked_and_machine_proposed(self) -> None:
        profile = self.registry.profile("engineering")
        criterion = profile.required_criteria[0]["iri"]
        report = DisciplineCritic(self.registry).critique(
            discipline=profile,
            research_plan={"methods": ["verification"]},
            evidence_matrix={"rows": [{"criterion_iri": criterion, "evidence_refs": ["epg-1"]}]},
            draft={"claims": [{"claim_id": "claim-1", "text": "verified"}]},
        )
        result = next(item for item in report.criteria if item.criterion_iri == criterion)
        self.assertEqual("pass", result.status)
        self.assertEqual("machine_proposed", result.finding_state)
        self.assertEqual(["epg-1"], result.evidence_refs)

    def test_cross_discipline_disagreement_survives_aggregation(self) -> None:
        registry = self.registry
        engineering = registry.profile("engineering")
        philosophy = registry.profile("philosophy")
        critic = DisciplineCritic(registry)
        kwargs = {
            "research_plan": {"methods": ["verification"]},
            "evidence_matrix": {"rows": []},
            "draft": {"claims": [{"claim_id": "claim-1", "text": "claim"}]},
        }
        first = critic.critique(discipline=engineering, **kwargs)
        second = critic.critique(discipline=philosophy, **kwargs)
        aggregate = aggregate_critiques([first, second])
        self.assertEqual(2, len(aggregate.sections))
        self.assertIsInstance(aggregate.disagreements, list)
        self.assertNotIn("universal_score", aggregate.to_dict())
        self.assertIn("mandatory_failures", aggregate.to_dict())

    def test_scoring_is_multidimensional_and_binds_ontology_digest(self) -> None:
        profile = self.registry.profile("engineering")
        report = DisciplineCritic(self.registry).critique(
            discipline=profile,
            research_plan={"methods": ["verification"]},
            evidence_matrix={"rows": []},
            draft={"claims": [{"claim_id": "claim-score", "text": "claim"}]},
        )
        profile_metrics = score_ontology_profile(profile)
        critique_metrics = score_discipline_critique(report)
        self.assertEqual(profile.ontology_digest, profile_metrics["ontology_digest"])
        self.assertEqual(profile.ontology_digest, critique_metrics["ontology_digest"])
        self.assertIn("mandatory_failures", critique_metrics)
        self.assertNotIn("universal_score", critique_metrics)


if __name__ == "__main__":
    unittest.main()
