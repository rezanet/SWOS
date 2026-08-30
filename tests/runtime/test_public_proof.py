from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.public_proof import (
    PublicProofError,
    load_public_project,
    reproduce_public_proof,
    run_public_proof,
    verify_public_proof,
)

PROJECT = Path("examples/public-proof/project.json")
EXPECTED = Path("examples/public-proof/expected-proof.json")


class PublicProofTests(unittest.TestCase):
    def test_public_project_executes_real_runtime_and_all_eight_planes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "proof"
            result = run_public_proof(PROJECT, output)

            self.assertEqual(result["normalized_proof"]["status"], "APPROVED")
            self.assertEqual(len(result["normalized_proof"]["planes"]), 8)
            self.assertTrue(
                all(
                    plane["gate_result"] == "pass" for plane in result["normalized_proof"]["planes"]
                )
            )
            self.assertEqual(verify_public_proof(output), [])
            self.assertFalse((output / "approval" / "release-decision-ledger.json").exists())
            expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
            self.assertEqual(result["proof_fingerprint"], expected["proof_fingerprint"])
            self.assertEqual(
                result["normalized_proof"]["article_sha256"], expected["article_sha256"]
            )

    def test_independent_reproduction_matches_semantics_not_run_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "primary"
            run_public_proof(PROJECT, primary)
            report = reproduce_public_proof(PROJECT, primary, root / "independent")

            self.assertEqual(report["decision"], "pass", report["reasons"])
            self.assertEqual(report["primary_fingerprint"], report["reproduced_fingerprint"])
            self.assertNotEqual(report["primary_run_id"], report["reproduced_run_id"])

    def test_source_mutation_and_digest_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = json.loads(PROJECT.read_text(encoding="utf-8"))
            project["source_snapshots"][0]["text"] += " tampered"
            path = Path(tmp) / "project.json"
            path.write_text(json.dumps(project), encoding="utf-8")
            with self.assertRaises(PublicProofError):
                load_public_project(path)

    def test_proof_artifact_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "proof"
            run_public_proof(PROJECT, output)
            result_path = output / "proof-result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["normalized_proof"]["status"] = "ALTERED"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            self.assertTrue(verify_public_proof(output))


if __name__ == "__main__":
    unittest.main()
