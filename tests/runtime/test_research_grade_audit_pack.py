"""Test-first strict audit-pack verification contracts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.assemble_research_grade_audit_pack import (
    AuditPackError,
    assemble_audit_pack,
    verify_audit_pack,
)


class ResearchGradeAuditPackTests(unittest.TestCase):
    def _make_pack(self) -> tuple[Path, Path, tempfile.TemporaryDirectory[str]]:
        holder = tempfile.TemporaryDirectory()
        root = Path(holder.name)
        source = root / "source"
        pack = root / "pack"
        source.mkdir()
        (source / "metrics.json").write_text('{"coverage": 0.8}\n', encoding="utf-8")
        (source / "reviews.json").write_text('[]\n', encoding="utf-8")
        assemble_audit_pack(source, pack, code_sha="a" * 40)
        return source, pack, holder

    def test_complete_pack_verifies_at_its_recorded_head(self) -> None:
        _, pack, holder = self._make_pack()
        self.addCleanup(holder.cleanup)
        result = verify_audit_pack(pack, expected_code_sha="a" * 40)
        self.assertEqual("pass", result["status"])
        self.assertEqual(2, result["artifact_count"])

    def test_missing_artifact_is_rejected(self) -> None:
        _, pack, holder = self._make_pack()
        self.addCleanup(holder.cleanup)
        (pack / "metrics.json").unlink()
        with self.assertRaises(AuditPackError) as raised:
            verify_audit_pack(pack, expected_code_sha="a" * 40)
        self.assertIn("missing", str(raised.exception).lower())

    def test_extra_artifact_is_rejected(self) -> None:
        _, pack, holder = self._make_pack()
        self.addCleanup(holder.cleanup)
        (pack / "unexpected.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(AuditPackError) as raised:
            verify_audit_pack(pack, expected_code_sha="a" * 40)
        self.assertIn("extra", str(raised.exception).lower())

    def test_tampered_artifact_is_rejected(self) -> None:
        _, pack, holder = self._make_pack()
        self.addCleanup(holder.cleanup)
        (pack / "metrics.json").write_text('{"coverage": 0.1}\n', encoding="utf-8")
        with self.assertRaises(AuditPackError) as raised:
            verify_audit_pack(pack, expected_code_sha="a" * 40)
        self.assertIn("digest", str(raised.exception).lower())

    def test_head_mismatch_is_rejected(self) -> None:
        _, pack, holder = self._make_pack()
        self.addCleanup(holder.cleanup)
        with self.assertRaises(AuditPackError) as raised:
            verify_audit_pack(pack, expected_code_sha="b" * 40)
        self.assertIn("head", str(raised.exception).lower())


if __name__ == "__main__":
    unittest.main()
