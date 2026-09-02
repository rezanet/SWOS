"""Default-off exact-head paired-promotion tests."""

from __future__ import annotations

import unittest

from swos_runtime.image_analysis import assess_promotion, commit_promotion
from swos_runtime.models import canonical_digest


class CapabilityPromotionTests(unittest.TestCase):
    def _evidence(self, **changes):
        value = {
            "source_sha": "a" * 40,
            "artifact_digest": "b" * 64,
            "case_ids": ["c1", "c2"],
            "provider": "fake",
            "model": "m",
            "config_digest": "d" * 64,
            "prompt_digest": "e" * 64,
            "seed": 7,
            "draw_digest": "f" * 64,
            "evaluation_manifest_digest": "1" * 64,
            "epg_digest": "g" * 64,
            "sdl_digest": "h" * 64,
            "live_exact_head": True,
            "human_quorum": True,
            "role_separation": True,
            "safety_regressions": [],
            "rollback_tested": True,
            "pack_only_fallback": True,
            "case_results": [
                {"case_id": "c1", "metrics": {"cross_modal_f1": 0.70}, "human_reviewed": True},
                {"case_id": "c2", "metrics": {"cross_modal_f1": 0.70}, "human_reviewed": True},
            ],
        }
        value.update(changes)
        if "metric" in value:
            metric = value.pop("metric")
            value["case_results"] = [
                {"case_id": case_id, "metrics": {"cross_modal_f1": metric}, "human_reviewed": True}
                for case_id in value["case_ids"]
            ]
        return value

    def _approval(self, assessment, **changes):
        value = {
            "approval_id": "promotion-approval",
            "approver_id": "human-1",
            "approver_role": "promotion_owner",
            "approved_at": assessment.created_at,
            "disposition": "approved",
            "assessment_digest": canonical_digest(assessment.to_dict()),
            "candidate_digest": assessment.candidate_digest,
            "scope_digest": assessment.evidence["scope_digest"],
            "operation_digest": assessment.evidence["operation_digest"],
            "epg_digest": assessment.evidence["epg_digest"],
            "sdl_digest": assessment.evidence["sdl_digest"],
            "policy_digest": assessment.evidence["policy_digest"],
        }
        value.update(changes)
        return value

    def test_default_off_and_mismatched_heads_are_disabled(self) -> None:
        assessment = assess_promotion(
            capability="image_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=self._evidence(),
            candidate=self._evidence(source_sha="c" * 40),
            policy={"minimum_improvement": 0.08},
        )
        self.assertEqual("disabled", assessment.status)
        self.assertFalse(assessment.eligible)

    def test_improvement_ci_live_and_approval_are_required(self) -> None:
        assessment = assess_promotion(
            capability="image_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=self._evidence(metric=0.70),
            candidate=self._evidence(metric=0.80, live_exact_head=False),
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("disabled", assessment.status)
        decision = commit_promotion(
            assessment,
            self._approval(assessment),
        )
        self.assertEqual("disabled", decision.status)

    def test_eligible_pair_requires_artifact_identity_and_can_roll_back(self) -> None:
        baseline = self._evidence(metric=0.70)
        candidate = self._evidence(metric=0.80, lower_95_ci=0.01)
        assessment = assess_promotion(
            capability="image_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=baseline,
            candidate=candidate,
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertTrue(assessment.eligible)
        decision = commit_promotion(
            assessment,
            self._approval(assessment),
        )
        self.assertTrue(decision.enabled)
        rolled_back = __import__(
            "swos_runtime.image_analysis", fromlist=["rollback_promotion"]
        ).rollback_promotion(decision, reason="safety regression")
        self.assertEqual("rolled_back", rolled_back.status)
        self.assertFalse(rolled_back.enabled)

    def test_promotion_approval_must_bind_exact_assessment_digest(self) -> None:
        assessment = assess_promotion(
            capability="image_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=self._evidence(metric=0.70),
            candidate=self._evidence(metric=0.80, lower_95_ci=0.01),
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        unbound = commit_promotion(
            assessment,
            {"disposition": "approved", "approver_id": "human-1"},
        )
        self.assertFalse(unbound.enabled)
        self.assertEqual("disabled", unbound.status)

    def test_expired_or_unbound_artifact_evidence_stays_disabled(self) -> None:
        expired = self._evidence(metric=0.80, lower_95_ci=0.01, expired=True)
        assessment = assess_promotion(
            capability="image_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=self._evidence(metric=0.70),
            candidate=expired,
        )
        self.assertFalse(assessment.eligible)
        self.assertIn("candidate_evidence_expired", assessment.reasons)
        mismatched = assess_promotion(
            capability="image_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=self._evidence(metric=0.70),
            candidate=self._evidence(metric=0.80, lower_95_ci=0.01, artifact_digest="c" * 64),
        )
        self.assertFalse(mismatched.eligible)
        self.assertIn("paired_evidence_mismatch:artifact_digest", mismatched.reasons)


if __name__ == "__main__":
    unittest.main()
