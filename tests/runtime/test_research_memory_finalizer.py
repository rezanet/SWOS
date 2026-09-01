"""Integration contract for injecting the scoped RPM service into finalization."""

from __future__ import annotations

import unittest

from swos_runtime.finalizer import _rpm_snapshot
from swos_runtime.research_memory import MemoryQuery, ResearchScope


class _FakeRPM:
    def normal_read_policy(self):
        return "normal"

    def query(self, scope, query, policy, *, as_of=None):
        self.called = (scope, query, policy, as_of)
        return type(
            "Result",
            (),
            {
                "items": [{"item_id": "item-1"}],
                "receipt": type(
                    "Receipt", (), {"to_dict": lambda self: {"receipt_id": "read-1"}}
                )(),
            },
        )()


class ResearchMemoryFinalizerTests(unittest.TestCase):
    def test_rpm_snapshot_uses_injected_scoped_service_and_receipt(self) -> None:
        service = _FakeRPM()
        scope = ResearchScope("n", "p", "x")
        snapshot = _rpm_snapshot(service, scope)
        self.assertEqual("2.0.0", snapshot["schema_version"])
        self.assertEqual([{"item_id": "item-1"}], snapshot["items"])
        self.assertEqual({"receipt_id": "read-1"}, snapshot["read_receipt"])
        self.assertEqual(scope.to_dict(), snapshot["scope"])
        self.assertIsInstance(service.called[1], MemoryQuery)


if __name__ == "__main__":
    unittest.main()
