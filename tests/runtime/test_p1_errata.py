"""Regression tests for the authorised Research Grade P1 planning errata."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swos_runtime.image_analysis import assess_promotion
from swos_runtime.models import SWOSRuntimeError, canonical_digest
from swos_runtime.programme_store import ProgrammeStore, StoreIntegrityError
from swos_runtime.prov_interop import (
    INTERNAL_CANONICAL_PROV_FORMAT,
    PUBLIC_PROV_FORMATS,
    epg_to_prov,
    serialize_prov,
)
from swos_runtime.prov_model import ResourceLimits
from swos_runtime.prov_validation import canonical_fingerprint
from swos_runtime.research_memory import (
    DataClassification,
    HumanApproval,
    MemoryCandidate,
    MemoryQuery,
    MemoryStatus,
    ResearchMemoryService,
    ResearchScope,
    RPMOperation,
)
from swos_runtime.source_diversity import (
    DiversityRequirement,
    FamilyIdentityPolicy,
    canonicalize_source_families,
    measure_source_diversity,
)
from tests.runtime.test_epg_v2 import sample_epg


class P1MemoryErrataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.service = ResearchMemoryService(ProgrammeStore(Path(self.holder.name) / "rpm.sqlite"))
        self.service.store.initialize()
        self.scope = ResearchScope("namespace", "programme", "project")
        self._commit(
            RPMOperation.register_project(self.scope, label="Project", manifest_digest="a" * 64)
        )

    def tearDown(self) -> None:
        self.holder.cleanup()

    def _candidate(self, item_id: str = "item-1") -> MemoryCandidate:
        return MemoryCandidate(
            item_id=item_id,
            category="finding",
            statement=f"statement:{item_id}",
            confidence=0.9,
            data_classification=DataClassification.PUBLIC,
            owner="owner",
            expiry="2099-01-01T00:00:00Z",
            source_grounded=True,
            epg_node_ids=(f"epg:{item_id}",),
            sdl_decision_id=f"sdl:{item_id}",
            parent_digest="b" * 64,
            origin="fixture",
        )

    def _commit(
        self,
        operation: RPMOperation,
        *,
        scope: ResearchScope | None = None,
        approval: HumanApproval | None = None,
    ):
        scope = scope or self.scope
        assessment = self.service.assess_operation(scope, operation)
        approval = approval or HumanApproval.for_assessment(
            assessment, approver="reviewer", role="memory_owner"
        )
        return self.service.commit_operation(
            scope, assessment_id=assessment.assessment_id, approval=approval
        )

    def test_resolved_by_scope_is_a_disposition_and_not_a_projection_status(self) -> None:
        self._commit(RPMOperation.write(self.scope, self._candidate()))
        self._commit(RPMOperation.contradiction_open(self.scope, "item-1", reason="counter"))
        result = self._commit(
            RPMOperation.contradiction_resolve(
                self.scope,
                "item-1",
                disposition="resolved_by_scope",
                scoped_positions=(
                    {
                        "scope": "jurisdiction:AU",
                        "assumptions": ["assumption-a"],
                        "position": "retain original claim",
                    },
                ),
            )
        )
        self.assertEqual("active", result.projection["status"])
        self.assertEqual(
            "resolved_by_scope",
            result.projection["contradiction_resolution"]["disposition"],
        )
        self.assertEqual(
            "jurisdiction:AU",
            result.projection["contradiction_resolution"]["scoped_positions"][0]["scope"],
        )
        self.assertEqual(
            [],
            self.service.query(self.scope, MemoryQuery(), self.service.normal_read_policy()).items,
        )
        self.assertEqual(
            ["item-1"],
            [
                item["item_id"]
                for item in self.service.query(
                    self.scope,
                    MemoryQuery(position_scope="jurisdiction:AU"),
                    self.service.normal_read_policy(),
                ).items
            ],
        )
        with self.assertRaises(ValueError):
            MemoryStatus("resolved_by_scope")
        with self.assertRaises(StoreIntegrityError):
            self.service.store.append_event(
                self.scope,
                "invalid-status",
                "item-invalid",
                {"status": "resolved_by_scope"},
                operation_id="invalid-status-operation",
            )

    def test_mutation_requires_bound_approval_scope_digests_and_freshness(self) -> None:
        operation = RPMOperation.write(self.scope, self._candidate("item-2"))
        assessment = self.service.assess_operation(self.scope, operation)
        with self.assertRaises(SWOSRuntimeError):
            self.service.commit_operation(
                self.scope, assessment_id=assessment.assessment_id, approval=None
            )

        other_scope = ResearchScope("namespace", "programme", "other-project")
        self._commit(
            RPMOperation.register_project(other_scope, label="Other", manifest_digest="c" * 64),
            scope=other_scope,
        )
        with self.assertRaises(SWOSRuntimeError):
            self.service.commit_operation(
                other_scope,
                assessment_id=assessment.assessment_id,
                approval=HumanApproval.for_assessment(
                    assessment, approver="reviewer", role="memory_owner"
                ),
            )

        approval = HumanApproval.for_assessment(
            assessment, approver="reviewer", role="memory_owner"
        )
        with self.assertRaises(SWOSRuntimeError):
            self.service.commit_operation(
                self.scope,
                assessment_id=assessment.assessment_id,
                approval=HumanApproval(**{**approval.to_dict(), "epg_digest": "0" * 64}),
            )
        with self.assertRaises(SWOSRuntimeError):
            self.service.commit_operation(
                self.scope,
                assessment_id=assessment.assessment_id,
                approval=HumanApproval(
                    **{
                        **approval.to_dict(),
                        "operation_digest": "0" * 64,
                    }
                ),
            )
        with self.assertRaises(SWOSRuntimeError):
            self.service.commit_operation(
                self.scope,
                assessment_id=assessment.assessment_id,
                approval=HumanApproval(
                    **{
                        **approval.to_dict(),
                        "approved_at": "2020-01-01T00:00:00Z",
                    }
                ),
            )

    def test_future_dated_approval_is_rejected_against_commit_time(self) -> None:
        operation = RPMOperation.write(self.scope, self._candidate("future-approval"))
        assessment = self.service.assess_operation(self.scope, operation)
        approval = HumanApproval.for_assessment(
            assessment, approver="reviewer", role="memory_owner"
        )
        with self.assertRaises(SWOSRuntimeError):
            self.service.commit_operation(
                self.scope,
                assessment_id=assessment.assessment_id,
                approval=HumanApproval(
                    **{
                        **approval.to_dict(),
                        "approved_at": "2099-01-01T00:00:00Z",
                    }
                ),
            )


class P1ProvErrataTests(unittest.TestCase):
    def test_public_formats_exclude_internal_n_quads_canonicalization(self) -> None:
        self.assertEqual(("prov-json", "prov-n", "prov-o-trig"), PUBLIC_PROV_FORMATS)
        self.assertNotIn("n-quads", PUBLIC_PROV_FORMATS)
        self.assertEqual("n-quads", INTERNAL_CANONICAL_PROV_FORMAT)
        document = epg_to_prov(sample_epg(), base_iri="https://example.org/prov/")
        fingerprint = canonical_fingerprint(document, ResourceLimits())
        self.assertEqual("internal-n-quads", fingerprint.rdfc10_representation)
        with self.assertRaises(ValueError):
            serialize_prov(document, "n-quads")


def _diversity_source(index: int, *, provider: str | None = None) -> dict:
    return {
        "source_id": f"source-{index}",
        "title": f"Distinct Work {index}",
        "doi": f"10.2000/{index}",
        "provider": provider or f"provider-{index}",
        "publisher": f"publisher-{index}",
        "venue": f"venue-{index}",
        "region": "AU",
        "language": "en",
        "period": "2020s",
        "methodology": "empirical",
        "source_type": "article",
        "access_mode": "open",
        "stance": "support",
        "metadata_status": {
            dimension: "observed"
            for dimension in (
                "work_family",
                "publisher",
                "venue",
                "author_cluster",
                "geography",
                "language",
                "period",
                "methodology",
                "source_type",
                "access_mode",
                "stance",
            )
        },
    }


class P1DiversityErrataTests(unittest.TestCase):
    def _families(self):
        first = _diversity_source(1)
        mirror = {**first, "source_id": "mirror-1", "provider": "provider-mirror"}
        return canonicalize_source_families(
            [first, mirror] + [_diversity_source(index) for index in range(2, 6)],
            FamilyIdentityPolicy(),
        )

    def test_claim_exposure_counts_unique_claim_family_edges_and_uses_worse_balance(self) -> None:
        families = self._families()
        report = measure_source_diversity(
            families=families,
            admitted_claims=[
                {"claim_id": "claim-1", "source_ids": ["source-1", "mirror-1"]},
                {"claim_id": "claim-2", "source_ids": ["source-1"]},
                {"claim_id": "claim-3", "source_ids": ["source-2"]},
                {"claim_id": "claim-4", "source_ids": ["source-3"]},
                {"claim_id": "claim-5", "source_ids": ["source-4"]},
                {"claim_id": "claim-6", "source_ids": ["source-5"]},
            ],
            requirements=DiversityRequirement(
                requirement_id="edge-unique",
                dimensions=("publisher",),
                min_family_count=5,
                max_hhi=1.0,
                max_share=1.0,
                min_composite=0.1,
            ),
        )
        dimension = report.dimensions["publisher"]
        self.assertEqual(2, dimension.claim_exposure_counts["publisher-1"])
        self.assertEqual(1, dimension.claim_exposure_counts["publisher-2"])
        self.assertAlmostEqual(2 / 6, dimension.claim_exposure_shares["publisher-1"])
        expected_balance = (1 - ((2 / 6) ** 2 + 4 * (1 / 6) ** 2)) / (1 - 1 / 5)
        self.assertAlmostEqual(expected_balance, dimension.normalized_balance)
        self.assertAlmostEqual(expected_balance, report.research_grade_composite)

    def test_worse_claim_exposure_max_share_fails_even_when_source_counts_are_balanced(
        self,
    ) -> None:
        families = self._families()
        claims = [
            {"claim_id": f"dominant-{index}", "source_ids": ["source-1"]} for index in range(7)
        ] + [
            {"claim_id": f"other-{index}", "source_ids": [f"source-{index}"]}
            for index in range(2, 6)
        ]
        report = measure_source_diversity(
            families=families,
            admitted_claims=claims,
            requirements=DiversityRequirement(
                requirement_id="worse-max-share",
                dimensions=("publisher",),
                min_family_count=5,
                max_hhi=1.0,
                max_share=0.60,
                min_composite=0.1,
            ),
        )
        self.assertEqual("fail", report.raw_status)
        self.assertGreater(report.dimensions["publisher"].max_share, 0.60)

    def test_empty_required_exposure_and_zero_applicable_dimensions_are_not_run(self) -> None:
        families = self._families()
        report = measure_source_diversity(
            families=families,
            admitted_claims=[],
            requirements=DiversityRequirement(
                requirement_id="required-exposure",
                dimensions=("publisher",),
                claim_exposure_required=True,
            ),
        )
        self.assertEqual("not_run", report.raw_status)
        self.assertEqual("not_run", report.status)
        empty = measure_source_diversity(
            families=canonicalize_source_families([], FamilyIdentityPolicy()),
            admitted_claims=[],
            requirements=DiversityRequirement(
                requirement_id="no-families",
                dimensions=("publisher",),
            ),
        )
        self.assertEqual("not_run", empty.status)
        no_applicable = measure_source_diversity(
            families=families,
            admitted_claims=[{"claim_id": "claim", "source_ids": ["source-1"]}],
            requirements=DiversityRequirement(
                requirement_id="no-applicable",
                dimensions=("not-a-real-dimension",),
            ),
        )
        self.assertEqual("not_run", no_applicable.status)


class P1PromotionErrataTests(unittest.TestCase):
    def _evidence(self, **changes):
        manifest_digest = "1" * 64
        value = {
            "source_sha": "a" * 40,
            "artifact_digest": "b" * 64,
            "case_ids": ["case-1", "case-2", "case-3"],
            "provider": "fake",
            "model": "m",
            "config_digest": "d" * 64,
            "prompt_digest": "e" * 64,
            "seed": 7,
            "draw_digest": "f" * 64,
            "evaluation_manifest_digest": manifest_digest,
            "live_exact_head": True,
            "human_quorum": True,
            "role_separation": True,
            "safety_regressions": [],
            "rollback_tested": True,
            "pack_only_fallback": True,
            "case_results": [
                {"case_id": "case-1", "draws": [0.60, 0.62], "human_reviewed": True},
                {"case_id": "case-2", "draws": [0.60, 0.62], "human_reviewed": True},
                {"case_id": "case-3", "draws": [0.60, 0.62], "human_reviewed": True},
            ],
        }
        value.update(changes)
        return value

    def test_multimodal_primary_metric_uses_case_level_paired_bootstrap(self) -> None:
        baseline = self._evidence(
            case_results=[
                {"case_id": "case-1", "metrics": {"cross_modal_f1": 0.60}, "human_reviewed": True},
                {"case_id": "case-2", "metrics": {"cross_modal_f1": 0.60}, "human_reviewed": True},
                {"case_id": "case-3", "metrics": {"cross_modal_f1": 0.60}, "human_reviewed": True},
            ]
        )
        candidate = self._evidence(
            case_results=[
                {"case_id": "case-1", "metrics": {"cross_modal_f1": 0.70}, "human_reviewed": True},
                {"case_id": "case-2", "metrics": {"cross_modal_f1": 0.71}, "human_reviewed": True},
                {"case_id": "case-3", "metrics": {"cross_modal_f1": 0.72}, "human_reviewed": True},
            ]
        )
        assessment = assess_promotion(
            capability="multimodal_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=baseline,
            candidate=candidate,
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("cross_modal_f1", assessment.evidence["primary_metric"])
        self.assertEqual(3, assessment.evidence["case_count"])
        self.assertEqual(10_000, assessment.evidence["bootstrap_resamples"])
        self.assertEqual(
            canonical_digest(["case-1", "case-2", "case-3"]),
            assessment.evidence["case_id_digest"],
        )
        self.assertEqual(3, len(assessment.evidence["case_differences"]))
        self.assertEqual("1" * 64, assessment.evidence["evaluation_manifest_digest"])

        repeated = assess_promotion(
            capability="multimodal_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=baseline,
            candidate=candidate,
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual(assessment.lower_confidence_bound, repeated.lower_confidence_bound)

    def test_declared_case_ids_without_results_are_not_run(self) -> None:
        baseline = self._evidence(metric=0.60)
        candidate = self._evidence(metric=0.71, lower_95_ci=0.01)
        baseline.pop("case_results")
        candidate.pop("case_results")
        assessment = assess_promotion(
            capability="multimodal_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=baseline,
            candidate=candidate,
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("not_run", assessment.evidence["evaluation_status"])
        self.assertIn("evaluation_not_run", assessment.reasons)
        self.assertFalse(assessment.eligible)

        scalar_only_baseline = self._evidence(cross_modal_f1=0.60)
        scalar_only_candidate = self._evidence(cross_modal_f1=0.71, lower_95_ci=0.01)
        scalar_only_baseline.pop("case_results")
        scalar_only_candidate.pop("case_results")
        scalar_only_baseline.pop("case_ids")
        scalar_only_candidate.pop("case_ids")
        scalar_only = assess_promotion(
            capability="multimodal_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=scalar_only_baseline,
            candidate=scalar_only_candidate,
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("not_run", scalar_only.evidence["evaluation_status"])
        self.assertFalse(scalar_only.eligible)

    def test_named_primary_metric_does_not_accept_generic_aliases(self) -> None:
        baseline = self._evidence(
            case_results=[
                {"case_id": "case-1", "score": 0.60, "human_reviewed": True},
                {"case_id": "case-2", "score": 0.60, "human_reviewed": True},
                {"case_id": "case-3", "score": 0.60, "human_reviewed": True},
            ]
        )
        candidate = self._evidence(
            case_results=[
                {"case_id": "case-1", "score": 0.70, "human_reviewed": True},
                {"case_id": "case-2", "score": 0.71, "human_reviewed": True},
                {"case_id": "case-3", "score": 0.72, "human_reviewed": True},
            ]
        )
        assessment = assess_promotion(
            capability="multimodal_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=baseline,
            candidate=candidate,
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("not_run", assessment.evidence["evaluation_status"])
        self.assertIn("evaluation_not_run", assessment.reasons)
        self.assertFalse(assessment.eligible)

    def test_specialist_routing_uses_discipline_weighted_score_and_missing_truth_is_not_run(
        self,
    ) -> None:
        baseline = self._evidence(
            case_results=[
                {
                    "case_id": "case-1",
                    "metrics": {"discipline_weighted_score": 0.60},
                    "human_reviewed": True,
                },
                {
                    "case_id": "case-2",
                    "metrics": {"discipline_weighted_score": 0.60},
                    "human_reviewed": True,
                },
                {
                    "case_id": "case-3",
                    "metrics": {"discipline_weighted_score": 0.60},
                    "human_reviewed": True,
                },
            ]
        )
        candidate = self._evidence(
            case_results=[
                {
                    "case_id": "case-1",
                    "metrics": {"discipline_weighted_score": 0.70},
                    "human_reviewed": True,
                },
                {
                    "case_id": "case-2",
                    "metrics": {"discipline_weighted_score": 0.71},
                    "human_reviewed": True,
                },
                {
                    "case_id": "case-3",
                    "metrics": {"discipline_weighted_score": 0.72},
                    "human_reviewed": True,
                },
            ]
        )
        assessment = assess_promotion(
            capability="specialist_routing",
            pack="art_criticism",
            stage="specialist_agent",
            baseline=baseline,
            candidate=candidate,
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("discipline_weighted_score", assessment.evidence["primary_metric"])
        missing_truth = assess_promotion(
            capability="multimodal_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=baseline,
            candidate=self._evidence(
                case_results=[
                    {
                        "case_id": "case-1",
                        "metrics": {"cross_modal_f1": 0.70},
                        "human_reviewed": True,
                    },
                    {"case_id": "case-2", "metrics": {"cross_modal_f1": 0.71}},
                    {
                        "case_id": "case-3",
                        "metrics": {"cross_modal_f1": 0.72},
                        "human_reviewed": True,
                    },
                ]
            ),
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("not_run", missing_truth.evidence["evaluation_status"])
        self.assertIn("evaluation_not_run", missing_truth.reasons)

    def test_missing_case_result_and_nonfinite_case_score_never_become_zero_or_pass(self) -> None:
        baseline = self._evidence(
            case_results=[
                {"case_id": "case-1", "score": 0.60, "human_reviewed": True},
                {"case_id": "case-2", "score": 0.60, "human_reviewed": True},
                {"case_id": "case-3", "score": 0.60, "human_reviewed": True},
            ]
        )
        missing = assess_promotion(
            capability="image_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=baseline,
            candidate=self._evidence(
                case_results=[
                    {"case_id": "case-1", "score": 0.70, "human_reviewed": True},
                    {"case_id": "case-2", "score": 0.71, "human_reviewed": True},
                ]
            ),
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("not_run", missing.evidence["evaluation_status"])
        nonfinite = assess_promotion(
            capability="image_analysis",
            pack="art_history",
            stage="art_history_agent",
            baseline=baseline,
            candidate=self._evidence(
                case_results=[
                    {"case_id": "case-1", "score": float("nan"), "human_reviewed": True},
                    {"case_id": "case-2", "score": 0.71, "human_reviewed": True},
                    {"case_id": "case-3", "score": 0.72, "human_reviewed": True},
                ]
            ),
            policy={"minimum_improvement": 0.08, "lower_confidence_bound_minimum": 0.0},
        )
        self.assertEqual("not_run", nonfinite.evidence["evaluation_status"])
        self.assertFalse(nonfinite.eligible)


if __name__ == "__main__":
    unittest.main()
