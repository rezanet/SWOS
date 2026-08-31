from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from swos_runtime.public_proof import (
    reproduce_public_proof,
    run_public_proof,
    verify_public_proof,
)
from swos_runtime.release_evidence import (
    ReleaseEvidenceError,
    build_release_candidate,
    generate_sbom,
    verify_checksums,
    verify_release_candidate,
    write_checksums,
)
from swos_runtime.release_record import (
    ReleaseRecordError,
    create_release_record,
    verify_release_record,
)

PROJECT = Path("examples/public-proof/project.json")
TIME = "2026-08-30T00:00:00+00:00"


def _run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(args), cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


class ReleaseEvidenceTests(unittest.TestCase):
    def _source_repo(self, root: Path) -> tuple[Path, str]:
        repo = root / "repo"
        repo.mkdir()
        shutil.copy2("pyproject.toml", repo / "pyproject.toml")
        shutil.copy2("requirements-dev.lock", repo / "requirements-dev.lock")
        (repo / "release-input.txt").write_text("exact release input\n", encoding="utf-8")
        _run("git", "init", "-b", "main", cwd=repo)
        _run("git", "config", "user.name", "SWOS Test", cwd=repo)
        _run("git", "config", "user.email", "swos-test@example.invalid", cwd=repo)
        _run("git", "add", ".", cwd=repo)
        _run("git", "commit", "-m", "test release input", cwd=repo)
        return repo, _run("git", "rev-parse", "HEAD", cwd=repo)

    def _proof_and_record(self, root: Path, sha: str) -> tuple[Path, Path, Path]:
        proof = root / "proof"
        run_public_proof(PROJECT, proof)
        report = reproduce_public_proof(PROJECT, proof, root / "independent")
        reproduction = root / "reproduction.json"
        reproduction.write_text(json.dumps(report), encoding="utf-8")
        record = root / "release-record.json"
        create_release_record(
            selected_sha=sha,
            proof_dir=proof,
            reproduction_path=reproduction,
            approved_by_id="release-owner-test",
            approved_by_name="SWOS Test Owner",
            approved_at=TIME,
            rationale="The exact deterministic proof and independent reproduction pass.",
            output_path=record,
        )
        return proof, reproduction, record

    def _candidate(self, root: Path) -> tuple[Path, Path, str]:
        repo, sha = self._source_repo(root)
        proof, reproduction, record = self._proof_and_record(root, sha)
        candidate = root / "candidate"
        build_release_candidate(
            repo_root=repo,
            selected_sha=sha,
            proof_dir=proof,
            reproduction_path=reproduction,
            release_record_path=record,
            out_dir=candidate,
            built_at=TIME,
        )
        return candidate, proof, sha

    def test_candidate_contains_exact_record_sbom_provenance_and_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate, _, sha = self._candidate(root)
            manifest = json.loads(
                (candidate / "candidate-manifest.json").read_text(encoding="utf-8")
            )
            sbom = json.loads((candidate / "sbom.cdx.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["selected_sha"], sha)
            self.assertEqual(manifest["state"], "ready_for_public_release")
            self.assertTrue((candidate / "release-record.json").is_file())
            self.assertIn("release-record-gate.json", (candidate / "SHA256SUMS").read_text())
            self.assertFalse((candidate / "approval").exists())
            self.assertFalse((candidate / "SHA256SUMS.sig").exists())
            self.assertEqual(sbom["bomFormat"], "CycloneDX")
            self.assertTrue(sbom["components"])
            self.assertEqual(verify_checksums(candidate), [])
            self.assertEqual(verify_public_proof(candidate / "public-proof"), [])
            self.assertEqual(verify_release_candidate(candidate_dir=candidate)["decision"], "allow")
            self.assertIn(
                "live_compatible_release", (candidate / "conformance-report.json").read_text()
            )
            self.assertTrue((candidate / "KNOWN-LIMITATIONS.md").read_text().strip())

    def test_dirty_or_mismatched_selected_head_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, sha = self._source_repo(root)
            proof, reproduction, record = self._proof_and_record(root, sha)
            (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
            with self.assertRaises(ReleaseEvidenceError):
                build_release_candidate(
                    repo_root=repo,
                    selected_sha=sha,
                    proof_dir=proof,
                    reproduction_path=reproduction,
                    release_record_path=record,
                    out_dir=root / "candidate",
                    built_at=TIME,
                )
            with self.assertRaises(ReleaseEvidenceError):
                build_release_candidate(
                    repo_root=repo,
                    selected_sha="0" * 40,
                    proof_dir=proof,
                    reproduction_path=reproduction,
                    release_record_path=record,
                    out_dir=root / "candidate-2",
                    built_at=TIME,
                )

    def test_missing_or_mismatched_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, sha = self._source_repo(root)
            proof, reproduction, record = self._proof_and_record(root, sha)
            missing = verify_release_record(
                root / "missing.json",
                selected_sha=sha,
                proof_dir=proof,
                reproduction_path=reproduction,
            )
            self.assertTrue(missing)

            stored = json.loads(record.read_text(encoding="utf-8"))
            stored["selected_sha"] = "0" * 40
            record.write_text(json.dumps(stored), encoding="utf-8")
            with self.assertRaises(ReleaseEvidenceError):
                build_release_candidate(
                    repo_root=repo,
                    selected_sha=sha,
                    proof_dir=proof,
                    reproduction_path=reproduction,
                    release_record_path=record,
                    out_dir=root / "candidate",
                    built_at=TIME,
                )

    def test_tampered_candidate_or_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate, _, _ = self._candidate(Path(tmp))
            (candidate / "KNOWN-LIMITATIONS.md").write_text("tampered", encoding="utf-8")
            self.assertTrue(verify_release_candidate(candidate_dir=candidate)["reasons"])

            write_checksums(candidate)
            stored = json.loads((candidate / "release-record.json").read_text(encoding="utf-8"))
            stored["proof"]["fingerprint"] = "0" * 64
            (candidate / "release-record.json").write_text(json.dumps(stored), encoding="utf-8")
            write_checksums(candidate)
            result = verify_release_candidate(candidate_dir=candidate)
            self.assertEqual(result["decision"], "deny")
            self.assertTrue(any("release record" in reason for reason in result["reasons"]))

    def test_release_record_gate_schema_and_binding_fail_closed(self):
        cases = {
            "gate_version": "wrong.version",
            "release_record": "other-record.json",
            "reasons": ["blocked"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for field, value in cases.items():
                with self.subTest(field=field):
                    case_root = root / field
                    case_root.mkdir()
                    candidate, _, _ = self._candidate(case_root)
                    gate_path = candidate / "release-record-gate.json"
                    gate = json.loads(gate_path.read_text(encoding="utf-8"))
                    gate[field] = value
                    gate_path.write_text(json.dumps(gate), encoding="utf-8")
                    write_checksums(candidate)

                    result = verify_release_candidate(candidate_dir=candidate)
                    self.assertEqual(result["decision"], "deny")
                    self.assertTrue(
                        any("release record gate" in reason for reason in result["reasons"])
                    )

    def test_sbom_rejects_unlocked_dependency_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy2("pyproject.toml", root / "pyproject.toml")
            (root / "requirements-dev.lock").write_text("jsonschema>=4\n", encoding="utf-8")
            with self.assertRaises(ReleaseEvidenceError):
                generate_sbom(root)

    def test_record_rejects_unknown_fields_and_bad_source_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, sha = self._source_repo(root)
            proof, reproduction, record = self._proof_and_record(root, sha)
            stored = json.loads(record.read_text(encoding="utf-8"))
            stored["unexpected"] = True
            stored["evidence"]["source_sha256"]["src-nist-ai-rmf-core"] = "0" * 64
            record.write_text(json.dumps(stored), encoding="utf-8")
            errors = verify_release_record(
                record,
                selected_sha=sha,
                proof_dir=proof,
                reproduction_path=reproduction,
            )
            self.assertTrue(any("unsupported fields" in error for error in errors))
            self.assertTrue(any("source hashes" in error for error in errors))
            with self.assertRaises(ReleaseRecordError):
                create_release_record(
                    selected_sha=sha,
                    proof_dir=proof,
                    reproduction_path=reproduction,
                    approved_by_id="release-owner-test",
                    approved_by_name="SWOS Test Owner",
                    approved_at=TIME,
                    rationale="duplicate output must fail",
                    output_path=record,
                )


if __name__ == "__main__":
    unittest.main()
