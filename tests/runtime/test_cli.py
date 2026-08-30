from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from swos_runtime.capabilities import CAPABILITY_CONTRACT_SET, CAPABILITY_CONTRACTS
from swos_runtime.cli import main


class RuntimeCliTests(unittest.TestCase):
    def test_start_is_deterministic_and_does_not_require_provider_credentials(self):
        manifest = {
            "contract_set": CAPABILITY_CONTRACT_SET,
            "adapter": "offline-test-host",
            "model_host": "offline",
            "execution_mode": "host_native_subscription",
            "api_key_used": False,
            "paid_api_calls": 0,
            "capabilities": {
                name: {"level": "native", "contract": contract}
                for name, contract in CAPABILITY_CONTRACTS.items()
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = root / "request.json"
            adapter = root / "adapter.json"
            request.write_text(
                json.dumps({"topic": "A bounded research question"}), encoding="utf-8"
            )
            adapter.write_text(json.dumps(manifest), encoding="utf-8")
            argv = [
                "swos",
                "start",
                str(request),
                "--adapter",
                str(adapter),
                "--run-root",
                str(root / "runs"),
                "--json",
            ]
            output = io.StringIO()
            with (
                patch.object(sys, "argv", argv),
                patch.dict(os.environ, {}, clear=True),
                redirect_stdout(output),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["next_stage"], "research_planning")
        self.assertEqual(payload["work_order"]["contract"], "swos.research-planning.v1")

    def test_prepare_approval_routes_provider_neutral_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = {}
            for role in ("author", "contract-owner", "evaluation-owner"):
                path = root / f"{role}.json"
                payload = {"actor_type": "human", "actor_id": role}
                path.write_text(json.dumps(payload), encoding="utf-8")
                inputs[role] = (path, payload)
            argv = [
                "swos",
                "prepare-approval",
                "--run-dir",
                str(root / "run"),
                "--evaluation",
                str(root / "evaluation.json"),
                "--author",
                str(inputs["author"][0]),
                "--contract-owner",
                str(inputs["contract-owner"][0]),
                "--evaluation-owner",
                str(inputs["evaluation-owner"][0]),
                "--output",
                str(root / "release"),
                "--created-at",
                "2026-08-30T00:00:00+00:00",
                "--json",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch(
                    "swos_runtime.cli.prepare_approval_pack", return_value={"pack_id": "apr-1"}
                ) as prepare,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(main(), 0)

            prepare.assert_called_once_with(
                root / "run",
                root / "evaluation.json",
                root / "release",
                author=inputs["author"][1],
                contract_owner=inputs["contract-owner"][1],
                evaluation_owner=inputs["evaluation-owner"][1],
                created_at="2026-08-30T00:00:00+00:00",
            )

    def test_record_approval_routes_human_supplied_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decision = root / "decision.json"
            payload = {"decision": "reject"}
            decision.write_text(json.dumps(payload), encoding="utf-8")
            argv = [
                "swos",
                "record-approval",
                "--release-dir",
                str(root / "release"),
                "--decision",
                str(decision),
                "--json",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch(
                    "swos_runtime.cli.record_release_decision", return_value={"entries": []}
                ) as record,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(main(), 0)

            record.assert_called_once_with(root / "release", payload)


if __name__ == "__main__":
    unittest.main()
