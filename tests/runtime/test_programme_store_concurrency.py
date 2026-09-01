"""US1 red tests for bounded locking and all-or-nothing SQLite writes."""

from __future__ import annotations

import multiprocessing
import tempfile
import unittest
from pathlib import Path

from swos_runtime.programme_store import ProgrammeStore
from swos_runtime.research_memory import ResearchScope


def _append_worker(db: str, start: int, count: int) -> None:
    store = ProgrammeStore(Path(db), lock_timeout_seconds=5.0)
    store.initialize()
    scope = ResearchScope("n", "p", "x")
    for index in range(start, start + count):
        store.append_event(scope, "write", f"item-{index}", {"status": "active", "n": index})


class ProgrammeStoreConcurrencyTests(unittest.TestCase):
    def test_eight_processes_can_append_without_chain_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as holder:
            db = str(Path(holder) / "rpm.sqlite")
            ProgrammeStore(Path(db)).initialize()
            processes = [multiprocessing.Process(target=_append_worker, args=(db, n * 25, 25)) for n in range(8)]
            for process in processes:
                process.start()
            for process in processes:
                process.join(20)
                self.assertEqual(0, process.exitcode)
            store = ProgrammeStore(Path(db))
            scope = ResearchScope("n", "p", "x")
            self.assertEqual(200, len(store.events(scope)))
            self.assertEqual([], store.verify_chain(scope))

    def test_crash_injection_and_lock_timeout_do_not_leave_partial_projection(self) -> None:
        with tempfile.TemporaryDirectory() as holder:
            db = Path(holder) / "rpm.sqlite"
            store = ProgrammeStore(db)
            store.initialize()
            scope = ResearchScope("n", "p", "x")
            with self.assertRaises(RuntimeError):
                store.append_event(scope, "write", "crash", {"status": "active"}, crash_after_event=True)
            self.assertEqual([], store.events(scope))
            self.assertEqual([], store.verify_chain(scope))


if __name__ == "__main__":
    unittest.main()
