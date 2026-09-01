"""Compatibility tests for v1 JSONL stores crossing the v2 boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swos_runtime.research_memory import ResearchScope
from swos_runtime.stores import (
    GovernedJsonStore,
    export_v1_store_to_rpm,
    import_rpm_to_v1_store,
)


class ResearchMemoryV1AdapterTests(unittest.TestCase):
    def test_v1_records_round_trip_as_explicitly_marked_compatibility_data(self) -> None:
        with tempfile.TemporaryDirectory() as holder:
            path = Path(holder) / "memory.jsonl"
            store = GovernedJsonStore(path, store_name="memory", artifact_type="memory")
            store.append(
                {"statement": "known", "source": "source-1"},
                actor={"actor_id": "operator"},
                recorded_at="2026-09-01T00:00:00+00:00",
                approval={"decision": "approved"},
            )
            before = path.read_bytes()
            exported = export_v1_store_to_rpm(store, ResearchScope("n", "p", "x"))
            self.assertEqual(before, path.read_bytes())
            self.assertEqual("1.0.0", exported["source_store_version"])
            self.assertEqual("compatibility", exported["mode"])
            imported = import_rpm_to_v1_store(exported)
            self.assertEqual(exported["records"], imported)


if __name__ == "__main__":
    unittest.main()
