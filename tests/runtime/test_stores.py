from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.stores import (
    GovernedJsonStore,
    ResearchProgrammeMemoryStore,
    StoreError,
    persist_run_stores,
    verify_run_stores,
)

ACTOR = {
    "actor_type": "orchestrator",
    "actor_id": "store-test",
    "display_name": "Store test",
    "version": "1.0",
}
TIME = "2026-08-30T00:00:00+00:00"


class GovernedStoreTests(unittest.TestCase):
    def test_append_reopen_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "epg.jsonl"
            store = GovernedJsonStore(path, store_name="epg", artifact_type="epg")
            first = store.append(
                {"schema_version": "1.0.0", "value": 1},
                actor=ACTOR,
                recorded_at=TIME,
                record_id="rec-11111111-1111-1111-1111-111111111111",
            )
            reopened = GovernedJsonStore(path, store_name="epg", artifact_type="epg")

            self.assertEqual(reopened.records(), [first])
            self.assertEqual(reopened.verification_errors(), [])
            self.assertEqual(reopened.active_records()[0]["record_id"], first["record_id"])

    def test_correction_and_supersession_preserve_prior_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = GovernedJsonStore(
                Path(tmp) / "sdl.jsonl", store_name="sdl", artifact_type="sdl"
            )
            first = store.append(
                {"value": 1},
                actor=ACTOR,
                recorded_at=TIME,
                record_id="rec-11111111-1111-1111-1111-111111111111",
            )
            correction = store.correct(
                first["record_id"],
                {"value": 2},
                actor=ACTOR,
                rationale="Correct a transcription error.",
                recorded_at="2026-08-30T00:01:00+00:00",
                record_id="rec-22222222-2222-2222-2222-222222222222",
            )
            history = store.lifecycle_records()

            self.assertEqual(len(store.records()), 2)
            self.assertEqual(store.records()[0]["payload"], {"value": 1})
            self.assertEqual(store.active_records(), [correction])
            self.assertEqual(history[0]["superseded_by"], [correction["record_id"]])
            with self.assertRaises(StoreError):
                store.supersede(
                    first["record_id"],
                    {"value": 3},
                    actor=ACTOR,
                    rationale="Cannot supersede an inactive record.",
                )

    def test_tamper_missing_reorder_duplicate_chain_and_malformed_fail_closed(self):
        mutations = ("tamper", "missing", "reorder", "duplicate", "chain", "malformed")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "store.jsonl"
                store = GovernedJsonStore(path, store_name="epg", artifact_type="epg")
                for index in range(3):
                    store.append(
                        {"value": index},
                        actor=ACTOR,
                        recorded_at=f"2026-08-30T00:0{index}:00+00:00",
                        record_id=f"rec-{index + 1:08d}-1111-1111-1111-111111111111",
                    )
                lines = path.read_text(encoding="utf-8").splitlines()
                if mutation == "tamper":
                    item = json.loads(lines[1])
                    item["payload"]["value"] = 99
                    lines[1] = json.dumps(item, sort_keys=True)
                elif mutation == "missing":
                    lines.pop(1)
                elif mutation == "reorder":
                    lines[0], lines[1] = lines[1], lines[0]
                elif mutation == "duplicate":
                    lines[1] = lines[0]
                elif mutation == "chain":
                    item = json.loads(lines[1])
                    item["previous_hash"] = "0" * 64
                    lines[1] = json.dumps(item, sort_keys=True)
                else:
                    lines[1] = "{not-json"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")

                reopened = GovernedJsonStore(path, store_name="epg", artifact_type="epg")
                self.assertTrue(reopened.verification_errors())
                with self.assertRaises(StoreError):
                    reopened.records()

    def test_rpm_write_requires_complete_human_approved_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchProgrammeMemoryStore(Path(tmp) / "rpm.jsonl")
            item = {
                "memory_id": "mem-11111111-1111-1111-1111-111111111111",
                "category": "research_agenda",
                "content": "Investigate the bounded open question.",
                "owner": ACTOR,
                "confidence": "medium",
                "source_grounded": True,
                "expiry": "2027-08-30",
                "provenance": {
                    "epg_node_ids": ["src-11111111-1111-1111-1111-111111111111"],
                    "sdl_decision_id": "dec-11111111-1111-1111-1111-111111111111",
                },
            }
            approval = {
                "actor_type": "human",
                "approver": "human-reviewer",
                "approved_at": TIME,
                "rationale": "The source-grounded item supports programme continuity.",
            }
            record = store.append_item(
                item,
                approval=approval,
                recorded_at=TIME,
                record_id="rec-11111111-1111-1111-1111-111111111111",
            )
            self.assertEqual(record["approval"], approval)

            for broken_item, broken_approval in (
                ({**item, "source_grounded": False}, approval),
                ({**item, "expiry": ""}, approval),
                ({**item, "provenance": {}}, approval),
                (item, {}),
                (item, {**approval, "actor_type": "orchestrator"}),
            ):
                with self.assertRaises(StoreError):
                    store.append_item(broken_item, approval=broken_approval)

    def test_run_store_set_binds_all_five_frozen_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = {
                "provenance.json": {"schema_version": "1.0.0", "kind": "epg"},
                "decision-ledger.json": {"schema_version": "1.0.0", "kind": "sdl"},
                "rpm.json": {"schema_version": "1.0.0", "kind": "rpm"},
                "evidence-matrix.json": {"schema_version": "1.0.0", "kind": "matrix"},
                "argument-graph.json": {"schema_version": "1.0.0", "kind": "argument"},
            }
            for name, payload in artifacts.items():
                (root / name).write_text(json.dumps(payload), encoding="utf-8")

            heads = persist_run_stores(root, actor=ACTOR, recorded_at=TIME)

            self.assertEqual(set(heads), {"epg", "sdl", "rpm", "evidence_matrix", "argument_graph"})
            self.assertEqual(verify_run_stores(root), [])
            self.assertEqual(verify_run_stores(root, expected_heads=heads), [])
            wrong_heads = {**heads, "epg": "0" * 64}
            self.assertTrue(
                any(
                    "declared store head" in error
                    for error in verify_run_stores(root, expected_heads=wrong_heads)
                )
            )
            self.assertEqual(
                verify_run_stores(root, expected_heads=[]),
                ["declared store heads must be an object"],
            )
            (root / "evidence-matrix.json").write_text(
                json.dumps({"schema_version": "1.0.0", "tampered": True}), encoding="utf-8"
            )
            self.assertTrue(any("evidence_matrix" in error for error in verify_run_stores(root)))


if __name__ == "__main__":
    unittest.main()
