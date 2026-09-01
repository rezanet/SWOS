"""CLI contract tests for dry-run-first RPM operator commands."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "tools/rpm.py"


class RPMCLITests(unittest.TestCase):
    def test_init_verify_and_rebuild_are_machine_readable_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as holder:
            root = Path(holder)
            database = root / "rpm.sqlite"
            scope_file = root / "scope.json"
            scope_file.write_text(
                json.dumps(
                    {
                        "repository_namespace_id": "n",
                        "programme_id": "p",
                        "project_id": "x",
                    }
                ),
                encoding="utf-8",
            )
            init = self._run("init", "--repository", str(database), "--namespace", "n")
            self.assertEqual("initialized", init["status"])
            verify = self._run(
                "verify", "--repository", str(database), "--scope-file", str(scope_file)
            )
            self.assertEqual("pass", verify["status"])
            rebuilt = self._run(
                "rebuild-projection",
                "--repository",
                str(database),
                "--scope-file",
                str(scope_file),
                "--verify-only",
            )
            self.assertEqual("pass", rebuilt["status"])

    def _run(self, *args: str) -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
