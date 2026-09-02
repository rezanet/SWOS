"""US1 red tests for deterministic, bounded and safe RPM exchange."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

from swos_runtime.programme_store import ProgrammeStore
from swos_runtime.research_memory import (
    DataClassification,
    HumanApproval,
    MemoryCandidate,
    ResearchMemoryService,
    ResearchScope,
    RPMOperation,
)
from swos_runtime.rpm_exchange import BundleLimits, ExchangeError, ExportSelection, RPMExchange


class RPMExchangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.root = Path(self.holder.name)
        self.service = ResearchMemoryService(ProgrammeStore(self.root / "rpm.sqlite"))
        self.service.store.initialize()
        self.scope = ResearchScope("n", "p", "x")
        self._commit(RPMOperation.register_project(self.scope, label="X", manifest_digest="a" * 64))
        candidate = MemoryCandidate(
            "item-1",
            "finding",
            "ref:item-1",
            0.8,
            DataClassification.PUBLIC,
            "owner",
            "2099-01-01T00:00:00Z",
            True,
            ("epg:item-1",),
            "sdl:item-1",
            parent_digest="b" * 64,
            origin="fixture",
        )
        self._commit(RPMOperation.write(self.scope, candidate))

    def tearDown(self) -> None:
        self.holder.cleanup()

    def _commit(self, operation):
        assessment = self.service.assess_operation(self.scope, operation)
        approval = HumanApproval.for_assessment(
            assessment, approver="reviewer", role="memory_owner"
        )
        self.service.commit_operation(
            self.scope, assessment_id=assessment.assessment_id, approval=approval
        )

    def test_export_inspect_commit_is_idempotent_and_preserves_origin_mapping(self) -> None:
        exchange = RPMExchange(self.service)
        approval = HumanApproval(
            "export-approval",
            "reviewer",
            "memory_owner",
            "2026-09-01T00:00:00Z",
            "a" * 64,
            "b" * 64,
            "sdl:export",
            "approved",
            "export",
        )
        out = self.root / "bundle"
        receipt = exchange.export_bundle(
            self.scope, ExportSelection(), approval, BundleLimits(), out
        )
        inspection = exchange.inspect_import(out, destination=self.scope, limits=BundleLimits())
        approval = replace(approval, assessment_digest=inspection.inspection_digest)
        committed = exchange.commit_import(
            inspection.inspection_id, inspection.inspection_digest, approval
        )
        self.assertEqual(receipt.origin_scope, committed.origin_scope)
        self.assertEqual(
            "noop",
            exchange.commit_import(
                inspection.inspection_id, inspection.inspection_digest, approval
            ).status,
        )

    def test_import_commits_inspected_snapshot_and_requires_bound_approval(self) -> None:
        exchange = RPMExchange(self.service)
        export_approval = HumanApproval(
            "export-approval",
            "reviewer",
            "memory_owner",
            "2026-09-01T00:00:00Z",
            "a" * 64,
            "b" * 64,
            "sdl:export",
            "approved",
            "export",
        )
        out = self.root / "snapshot-bundle"
        exchange.export_bundle(self.scope, ExportSelection(), export_approval, BundleLimits(), out)
        destination = ResearchScope("n", "p", "destination")
        self.service.register_project(destination, label="Destination", manifest_digest="c" * 64)
        inspection = exchange.inspect_import(out, destination=destination, limits=BundleLimits())
        inspected_ids = tuple(str(event["event_id"]) for event in inspection.events)

        # A later origin write must not alter the immutable inspected import set.
        self._commit(
            RPMOperation.write(
                self.scope,
                MemoryCandidate(
                    "item-2",
                    "finding",
                    "ref:item-2",
                    0.8,
                    DataClassification.PUBLIC,
                    "owner",
                    "2099-01-01T00:00:00Z",
                    True,
                    ("epg:item-2",),
                    "sdl:item-2",
                    parent_digest="d" * 64,
                    origin="fixture",
                ),
            )
        )

        with self.assertRaises(Exception):
            exchange.commit_import(
                inspection.inspection_id,
                inspection.inspection_digest,
                export_approval,
            )
        approval = replace(export_approval, assessment_digest=inspection.inspection_digest)
        committed = exchange.commit_import(
            inspection.inspection_id, inspection.inspection_digest, approval
        )
        self.assertEqual(inspected_ids, committed.imported_event_ids)
        self.assertNotIn(
            "item-2",
            [event.get("item_id") for event in inspection.events],
        )

    def test_collision_and_checksum_or_redaction_fail_closed(self) -> None:
        exchange = RPMExchange(self.service)
        approval = HumanApproval(
            "export-approval",
            "reviewer",
            "memory_owner",
            "2026-09-01T00:00:00Z",
            "a" * 64,
            "b" * 64,
            "sdl:export",
            "approved",
            "export",
        )
        out = self.root / "bundle"
        exchange.export_bundle(self.scope, ExportSelection(), approval, BundleLimits(), out)
        (out / "events.ndjson").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(Exception):
            exchange.inspect_import(out, destination=self.scope, limits=BundleLimits())

    def test_zip_slip_duplicate_path_and_decompression_limit_are_rejected(self) -> None:
        exchange = RPMExchange(self.service)
        with self.assertRaises(Exception):
            exchange.inspect_import(
                self.root / "../evil.zip", destination=self.scope, limits=BundleLimits(max_bytes=1)
            )

    def test_zip_slip_and_duplicate_member_paths_are_rejected(self) -> None:
        exchange = RPMExchange(self.service)
        zip_path = self.root / "unsafe.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("../outside.txt", "blocked")
            archive.writestr("manifest.json", "{}")
            archive.writestr("events.ndjson", "")
            archive.writestr("checksums.json", "{}")
            archive.writestr("limitations.json", "{}")
        with self.assertRaisesRegex(ExchangeError, "unsafe bundle path"):
            exchange._read_bundle(zip_path, BundleLimits())

        duplicate_path = self.root / "duplicate.zip"
        with zipfile.ZipFile(duplicate_path, "w") as archive:
            archive.writestr("manifest.json", "{}")
            archive.writestr("manifest.json", "{}")
        with self.assertRaisesRegex(ExchangeError, "duplicate bundle path"):
            exchange._read_bundle(duplicate_path, BundleLimits())


if __name__ == "__main__":
    unittest.main()
