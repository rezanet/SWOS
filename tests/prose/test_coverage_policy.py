import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_coverage import main


def _report(total: float, *, include_critical: bool = True) -> dict:
    files = {}
    if include_critical:
        files = {
            path.replace("/", "\\"): {"summary": {"percent_covered": value}}
            for path, value in {
                "swos_prose/repair.py": 80.0,
                "swos_prose/pipeline.py": 85.0,
                "swos_prose/verify/causal_scope.py": 90.0,
                "swos_prose/verify/deterministic.py": 90.0,
                "swos_prose/verify/propositions.py": 85.0,
            }.items()
        }
    return {"totals": {"percent_covered": total}, "files": files}


class CoveragePolicyTests(unittest.TestCase):
    def _run(self, report: dict) -> int:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            with patch("sys.argv", ["check_coverage", "--coverage-json", str(path)]):
                return main()

    def test_policy_accepts_windows_coverage_paths(self) -> None:
        self.assertEqual(self._run(_report(80.0)), 0)

    def test_policy_rejects_missing_critical_module(self) -> None:
        self.assertEqual(self._run(_report(90.0, include_critical=False)), 1)
