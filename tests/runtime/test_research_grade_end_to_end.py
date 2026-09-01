"""Three-project Research Grade integrity path through public proof."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.discipline_critique import DisciplineCritic
from swos_runtime.discipline_ontology import DisciplineOntologyRegistry
from swos_runtime.evaluation import EvaluationSubject
from swos_runtime.image_analysis import VisualObservation
from swos_runtime.media import RegionSelector
from swos_runtime.programme_store import ProgrammeStore
from swos_runtime.public_proof import run_public_proof
from swos_runtime.research_memory import (
    HumanApproval,
    MemoryCandidate,
    MemoryQuery,
    ResearchMemoryService,
    ResearchScope,
    RPMOperation,
)

ROOT = Path(__file__).resolve().parents[2]


class ResearchGradeEndToEndTests(unittest.TestCase):
    def test_three_project_research_memory_critique_finalization_prov_public_proof(self) -> None:
        project_template = json.loads((ROOT / "examples" / "public-proof" / "project.json").read_text(encoding="utf-8"))
        registry = DisciplineOntologyRegistry().load(ROOT / "discipline-packs" / "manifest-v2.json")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = ResearchMemoryService(ProgrammeStore(root / "programme.sqlite"))
            seen_projects: set[str] = set()
            for index in range(1, 4):
                project = dict(project_template)
                project["project_id"] = f"swos-e2e-project-{index}"
                project_path = root / f"project-{index}.json"
                project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
                proof_dir = root / f"proof-{index}"
                scope = ResearchScope("swos", "research-grade-e2e", project["project_id"])
                memory.register_project(scope, label=project["project_id"], manifest_digest="a" * 64)
                proof = run_public_proof(project_path, proof_dir)
                subject = EvaluationSubject.load(proof_dir / "run")
                self.assertEqual(project["project_id"], proof["project_id"])
                self.assertTrue((proof_dir / "run" / "provenance-v2.json").is_file())
                self.assertEqual("not_run", json.loads((proof_dir / "run" / "provenance-v2-certificate.json").read_text(encoding="utf-8"))["status"])

                observation = VisualObservation(
                    observation_id=f"observation-{index}",
                    object_id=f"object-{index}",
                    asset_id=f"asset-{index}",
                    asset_digest="b" * 64,
                    description="A bounded visible feature.",
                    origin="machine",
                    selector=RegionSelector("iiif_pixel", "0,0,10,10", "b" * 64, asset_width=10, asset_height=10, normalized=(0, 0, 10, 10), validation_status="valid"),
                )
                critique = DisciplineCritic(registry).staged_multimodal_critique(
                    research_plan={},
                    evidence_matrix={"rows": []},
                    draft={"claims": [{"claim_id": f"claim-{index}"}]},
                    observations=[observation],
                )
                self.assertEqual(("art_history", "art_criticism"), critique.stage_order)

                candidate = MemoryCandidate(
                    f"item-{index}",
                    "research-finding",
                    f"ref:project-{index}",
                    0.9,
                    "public",
                    "e2e-owner",
                    "2099-01-01T00:00:00Z",
                    True,
                    (f"epg:{subject.work_id}",),
                    f"sdl:{index}",
                    parent_digest=proof["run_manifest_sha256"],
                    origin="research-grade-e2e",
                )
                operation = RPMOperation.write(scope, candidate)
                assessment = memory.assess_operation(scope, operation)
                committed = memory.commit_operation(
                    scope,
                    assessment_id=assessment.assessment_id,
                    approval=HumanApproval.for_assessment(assessment, approver="e2e-human", role="memory_owner"),
                )
                self.assertEqual("committed", committed.status)
                self.assertIn(candidate.item_id, memory.query(scope, MemoryQuery(), memory.normal_read_policy()).receipt.returned_item_ids)
                seen_projects.add(project["project_id"])
            self.assertEqual({"swos-e2e-project-1", "swos-e2e-project-2", "swos-e2e-project-3"}, seen_projects)


if __name__ == "__main__":
    unittest.main()
