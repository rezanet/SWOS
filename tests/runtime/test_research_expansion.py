"""Pre-retrieval diversity expansion and limitation propagation contracts."""

from __future__ import annotations

import unittest

from swos_runtime.research_expansion import expansion_plan


class ResearchExpansionTests(unittest.TestCase):
    def test_required_strata_and_counter_position_become_bounded_queries(self) -> None:
        report = {
            "status": "fail",
            "dimensions": {"publisher": {"required_strata_missing": ["independent"]}, "stance": {"required_strata_missing": ["counter"]}},
            "counter_position": {"status": "missing"},
        }
        plan = expansion_plan(report, topic="research question", max_queries=4)
        self.assertLessEqual(len(plan.queries), 4)
        self.assertTrue(any("counter" in item.lower() for item in plan.queries))
        self.assertTrue(plan.requires_review)


if __name__ == "__main__":
    unittest.main()
