from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evals.harness.deterministic_subject import build_deterministic_subject
from evals.harness.run_evals import PLANES, load_fixtures
from swos_runtime.evaluation import (
    EvaluationSubject,
    build_evaluation_result,
    canonical_digest,
)
from swos_runtime.release_approval import (
    SECTION_ORDER,
    ReleaseApprovalError,
    prepare_approval_pack,
    record_release_decision,
    verify_approval_pack,
    verify_release,
)

TIME = "2026-08-30T00:00:00+00:00"
AUTHOR = {"actor_type": "human", "actor_id": "author-1", "display_name": "Author"}
CONTRACT_OWNER = {
    "actor_type": "human",
    "actor_id": "contract-owner-1",
    "display_name": "Contract owner",
}
EVALUATION_OWNER = {
    "actor_type": "human",
    "actor_id": "evaluation-owner-1",
    "display_name": "Evaluation owner",
}
APPROVER = {
    "actor_type": "human",
    "actor_id": "approver-1",
    "display_name": "Approver",
}


class ReleaseApprovalTests(unittest.TestCase):
    def _prepare(self, root: Path, release: Path):
        outcome = build_deterministic_subject(root)
        self.assertEqual(outcome.status, "APPROVED", outcome.blocking_reasons)
        subject = EvaluationSubject.load(root)
        evaluation = build_evaluation_result(
            subject,
            {plane: load_fixtures(plane) for plane in PLANES},
            selected=PLANES,
            decided_at=TIME,
        )
        evaluation_path = root / "evaluation-result.json"
        evaluation_path.write_text(json.dumps(evaluation), encoding="utf-8")
        pack = prepare_approval_pack(
            root,
            evaluation_path,
            release,
            author=AUTHOR,
            contract_owner=CONTRACT_OWNER,
            evaluation_owner=EVALUATION_OWNER,
            created_at=TIME,
        )
        return pack

    @staticmethod
    def _decision(pack, *, choice="approve", approver=APPROVER):
        return {
            "decision": choice,
            "approver": approver,
            "rationale": "The exact evidence supports this bounded release decision.",
            "alternatives_considered": ["approve", "reject"],
            "reviewed_evidence": {
                **pack["bindings"],
                "approval_pack_sha256": canonical_digest(pack),
            },
            "policy_basis": "swos.release-gate",
            "timestamp": TIME,
        }

    def test_pack_is_risk_first_digest_bound_and_manuscript_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            release = Path(tmp) / "release"
            pack = self._prepare(root, release)

            self.assertEqual(pack["section_order"], list(SECTION_ORDER))
            self.assertEqual(pack["sections"][-1]["section_id"], "manuscript")
            self.assertEqual(verify_approval_pack(root, release), [])
            self.assertEqual(pack["release_status"], "awaiting_human_decision")

    def test_separate_human_approval_opens_release_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            release = Path(tmp) / "release"
            pack = self._prepare(root, release)
            ledger = record_release_decision(release, self._decision(pack))
            gate = verify_release(root, release)

            self.assertEqual(ledger["entries"][0]["human_approver"], APPROVER)
            self.assertEqual(gate["decision"], "allow", gate["reasons"])

    def test_automation_self_approval_and_bad_bindings_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            release = Path(tmp) / "release"
            pack = self._prepare(root, release)
            for mutation in (
                {"approver": {"actor_type": "orchestrator", "actor_id": "auto"}},
                {"approver": AUTHOR},
                {"rationale": ""},
                {"reviewed_evidence": {}},
            ):
                decision = {**self._decision(pack), **mutation}
                with self.subTest(mutation=mutation), self.assertRaises(ReleaseApprovalError):
                    record_release_decision(release, decision)

    def test_rejection_is_auditable_but_release_remains_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            release = Path(tmp) / "release"
            pack = self._prepare(root, release)
            record_release_decision(release, self._decision(pack, choice="reject"))
            gate = verify_release(root, release)
            self.assertEqual(gate["decision"], "deny")
            self.assertTrue(any("does not approve" in reason for reason in gate["reasons"]))

    def test_pack_tamper_and_cross_run_replay_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            second_root = Path(tmp) / "second-run"
            release = Path(tmp) / "release"
            pack = self._prepare(root, release)
            record_release_decision(release, self._decision(pack))

            second_outcome = build_deterministic_subject(second_root)
            self.assertEqual(second_outcome.status, "APPROVED")
            self.assertEqual(verify_release(second_root, release)["decision"], "deny")

            stored = json.loads((release / "approval-pack.json").read_text(encoding="utf-8"))
            stored["sections"][-1]["content"] += " tampered"
            (release / "approval-pack.json").write_text(json.dumps(stored), encoding="utf-8")
            self.assertEqual(verify_release(root, release)["decision"], "deny")


if __name__ == "__main__":
    unittest.main()
