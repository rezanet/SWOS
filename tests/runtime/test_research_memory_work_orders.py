"""Work-order RPM bindings must retain exact run and EPG evidence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.programme_store import ProgrammeStore
from swos_runtime.research_memory import (
    MemoryCandidate,
    MemoryQuery,
    ResearchMemoryService,
    ResearchScope,
    RPMOperation,
)
from swos_runtime.work_orders import WorkOrderRun


class ResearchMemoryWorkOrderTests(unittest.TestCase):
    def test_work_order_rpm_read_and_write_are_bound_to_run_scope_and_epg(self) -> None:
        with tempfile.TemporaryDirectory() as holder:
            root = Path(holder)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "run-state.json").write_text(
                json.dumps({"run_id": "run-1", "work_id": "work-1", "status": "ACTIVE", "history": []}),
                encoding="utf-8",
            )
            run = WorkOrderRun(run_dir)
            service = ResearchMemoryService(ProgrammeStore(root / "rpm.sqlite"))
            scope = ResearchScope("n", "p", "x")
            run.bind_rpm(service, scope)
            register = RPMOperation.register_project(scope, label="X", manifest_digest="a" * 64)
            run.rpm_write(register)
            candidate = MemoryCandidate(
                "item-1", "finding", "ref:item-1", 0.8, "public", "owner",
                "2099-01-01T00:00:00Z", True, ("epg:item-1",), "sdl:item-1",
                parent_digest="b" * 64, origin="work-order",
            )
            run.rpm_write(RPMOperation.write(scope, candidate))
            result = run.rpm_read(MemoryQuery())
            self.assertEqual("run-1", result.receipt.run_id)
            self.assertIn("epg:item-1", result.receipt.epg_node_ids)
            self.assertTrue(any(item.get("event") == "rpm_read" for item in run.state["history"]))
            self.assertTrue(any(item.get("event") == "rpm_write" for item in run.state["history"]))


if __name__ == "__main__":
    unittest.main()
