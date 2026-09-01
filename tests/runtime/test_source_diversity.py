"""Source-family identity and multidimensional diversity contracts."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from swos_runtime.source_diversity import (
    DIMENSIONS,
    DiversityRequirement,
    FamilyIdentityPolicy,
    canonicalize_source_families,
    measure_source_diversity,
)


def source(
    index: int, *, provider: str = "provider-a", owner: str | None = None, stance: str = "support"
) -> dict:
    return {
        "source_id": f"s-{index}",
        "title": f"Work {index}",
        "url": f"https://example.org/{index}",
        "provider": provider,
        "doi": f"10.1000/{index}",
        "publisher": owner or f"Owner {index}",
        "venue": f"Venue {index}",
        "region": "AU" if index % 2 else "UK",
        "language": "en",
        "period": "2020s",
        "methodology": "empirical" if index % 2 else "review",
        "source_type": "article",
        "access_mode": "open",
        "stance": stance,
        "metadata_status": {dimension: "observed" for dimension in DIMENSIONS},
    }


class SourceDiversityTests(unittest.TestCase):
    def test_family_identity_is_invariant_to_order_provider_and_mirror(self) -> None:
        one = source(1)
        mirror = {
            **one,
            "source_id": "mirror",
            "url": "https://mirror.invalid/one",
            "provider": "provider-b",
        }
        first = canonicalize_source_families([one, mirror, source(2)], FamilyIdentityPolicy())
        second = canonicalize_source_families([source(2), mirror, one], FamilyIdentityPolicy())
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(2, len(first.families))

    def test_unknown_metadata_does_not_improve_score_and_concentration_uses_claim_exposure(
        self,
    ) -> None:
        sources = [source(i, owner="same" if i < 4 else f"owner-{i}") for i in range(1, 7)]
        families = canonicalize_source_families(sources, FamilyIdentityPolicy())
        requirements = DiversityRequirement(
            requirement_id="req-1",
            dimensions=tuple(DIMENSIONS),
            min_family_count=5,
            required_strata={"stance": ["support", "counter"]},
            counter_position_required=True,
        )
        admitted = [{"source_id": item["source_id"]} for item in sources]
        report = measure_source_diversity(
            families=families, admitted_claims=admitted, requirements=requirements
        )
        self.assertIn("publisher", report.dimensions)
        self.assertLessEqual(report.dimensions["publisher"].hhi, 1.0)
        self.assertLessEqual(report.research_grade_composite, 1.0)
        self.assertTrue(report.corrective_queries)
        self.assertIn(report.status, {"pass", "review_required", "fail"})

    def test_fewer_than_three_families_blocks_and_narrow_exception_discloses_limit(self) -> None:
        families = canonicalize_source_families(
            [source(1), source(1, provider="other")], FamilyIdentityPolicy()
        )
        requirements = DiversityRequirement(
            requirement_id="req-2", dimensions=("publisher",), min_family_count=5
        )
        report = measure_source_diversity(
            families=families,
            admitted_claims=[{"source_id": "s-1"}],
            requirements=requirements,
            exception={
                "sdl_decision_id": "dec-1",
                "rationale": "field is narrow",
                "scope": "question",
                "expires_at": "2099-01-01T00:00:00Z",
            },
        )
        self.assertEqual("fail", report.raw_status)
        self.assertTrue(report.limitations)
        self.assertEqual("dec-1", report.exception["sdl_decision_id"])

    def test_configured_minimum_family_count_controls_overall_gate(self) -> None:
        sources = [source(index) for index in range(1, 6)]
        report = measure_source_diversity(
            families=canonicalize_source_families(sources, FamilyIdentityPolicy()),
            admitted_claims=[{"source_id": item["source_id"]} for item in sources],
            requirements=DiversityRequirement(
                requirement_id="req-custom-minimum",
                dimensions=("publisher",),
                min_family_count=10,
            ),
        )
        self.assertEqual("review_required", report.raw_status)
        self.assertIn("10", " ".join(report.limitations))

    def test_exception_expiry_preserves_aware_timestamp_instant(self) -> None:
        expired = datetime.now(timezone.utc) - timedelta(minutes=1)
        local_expiry = expired.astimezone(timezone(timedelta(hours=14))).isoformat()
        report = measure_source_diversity(
            families=canonicalize_source_families(
                [source(1), source(1, provider="other")], FamilyIdentityPolicy()
            ),
            admitted_claims=[{"source_id": "s-1"}],
            requirements=DiversityRequirement(
                requirement_id="req-expiry",
                dimensions=("publisher",),
                min_family_count=5,
            ),
            exception={
                "sdl_decision_id": "expired-dec",
                "rationale": "field is narrow",
                "scope": "question",
                "expires_at": local_expiry,
            },
        )
        self.assertEqual({}, report.exception)


if __name__ == "__main__":
    unittest.main()
