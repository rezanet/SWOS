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


if __name__ == "__main__":
    unittest.main()
