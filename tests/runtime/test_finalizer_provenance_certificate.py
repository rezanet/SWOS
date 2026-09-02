"""Finalizer contract for the schema-valid pending PROV certificate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from swos_runtime.finalizer import finalize_work_order_run
from tests.runtime.test_finalizer import HostNativeFinalizerTests

ROOT = Path(__file__).resolve().parents[2]


class FinalizerProvenanceCertificateTests(unittest.TestCase):
    def test_pending_prov_certificate_is_schema_valid(self) -> None:
        fixture = HostNativeFinalizerTests()
        with tempfile.TemporaryDirectory() as tmp:
            run = fixture._ready_run(tmp)
            output = Path(tmp) / "output"
            outcome = finalize_work_order_run(run, output)
            self.assertEqual("APPROVED", outcome.status, outcome.blocking_reasons)
            certificate = json.loads(
                (output / "provenance-v2-certificate.json").read_text(encoding="utf-8")
            )
        schema = json.loads(
            (ROOT / "schemas/research-grade/prov-roundtrip-report.schema.json").read_text(
                encoding="utf-8"
            )
        )
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(certificate))
        self.assertEqual([], errors)
        self.assertEqual("not_run", certificate["status"])


if __name__ == "__main__":
    unittest.main()
