"""US1 red tests for SQLite migration, chain, projection, and rebuild."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swos_runtime.programme_store import ProgrammeStore, StoreIntegrityError
from swos_runtime.research_memory import ResearchScope


class ProgrammeStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.db = Path(self.holder.name) / "rpm.sqlite"
        self.scope = ResearchScope("n", "p", "x")
        self.store = ProgrammeStore(self.db)
        self.store.initialize()

    def tearDown(self) -> None:
        self.holder.cleanup()

    def test_initialization_is_migrated_and_preflighted(self) -> None:
        self.assertEqual("2.0.0", self.store.schema_version())
        self.assertTrue(self.store.preflight().ok)
        self.assertEqual([], self.store.verify_chain(self.scope))

    def test_append_chain_and_projection_rebuild_are_deterministic(self) -> None:
        self.store.append_event(self.scope, "write", "item-1", {"status": "active", "value": 1})
        self.store.append_event(self.scope, "status_change", "item-1", {"status": "corrected", "value": 2})
        before = self.store.chain_head(self.scope)
        projection = self.store.rebuild_projection(self.scope)
        self.assertEqual("corrected", projection["item-1"]["status"])
        self.assertEqual(before, self.store.chain_head(self.scope))

    def test_tampering_is_detected_without_repairing_the_database(self) -> None:
        self.store.append_event(self.scope, "write", "item-1", {"status": "active"})
        self.store.tamper_for_test(self.scope, sequence=1, field="payload_json", value="{}")
        with self.assertRaises(StoreIntegrityError):
            self.store.assert_integrity(self.scope)
        self.assertTrue(self.db.is_file())


if __name__ == "__main__":
    unittest.main()
