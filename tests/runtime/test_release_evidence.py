from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from swos_runtime.evaluation import canonical_digest
from swos_runtime.public_proof import (
    reproduce_public_proof,
    run_public_proof,
    verify_public_proof,
)
from swos_runtime.release_approval import record_release_decision
from swos_runtime.release_evidence import (
    ReleaseEvidenceError,
    build_release_candidate,
    generate_sbom,
    verify_checksums,
    verify_release_candidate,
    write_checksums,
)

PROJECT = Path("examples/public-proof/project.json")
TIME = "2026-08-30T00:00:00+00:00"
PRINCIPAL = "swos-release-test@example.invalid"


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

    def _proof_and_approval(self, root: Path) -> tuple[Path, Path]:
        proof = root / "proof"
        run_public_proof(PROJECT, proof)
        report = reproduce_public_proof(PROJECT, proof, root / "independent")
        reproduction = root / "reproduction.json"
        reproduction.write_text(json.dumps(report), encoding="utf-8")
        pack = json.loads((proof / "approval" / "approval-pack.json").read_text(encoding="utf-8"))
        decision = {
            "decision": "approve",
            "approver": {"actor_type": "human", "actor_id": "release-approver-test"},
            "rationale": "The exact deterministic evidence passes this test release gate.",
            "alternatives_considered": ["approve", "reject"],
            "reviewed_evidence": {
                **pack["bindings"],
                "approval_pack_sha256": canonical_digest(pack),
            },
            "policy_basis": "swos.release-gate",
            "timestamp": TIME,
        }
        record_release_decision(proof / "approval", decision)
        return proof, reproduction

    def _candidate(self, root: Path) -> tuple[Path, Path, str]:
        repo, sha = self._source_repo(root)
        proof, reproduction = self._proof_and_approval(root)
        candidate = root / "candidate"
        build_release_candidate(
            repo_root=repo,
            selected_sha=sha,
            proof_dir=proof,
            reproduction_path=reproduction,
            release_approval_dir=proof / "approval",
            out_dir=candidate,
            built_at=TIME,
        )
        return candidate, proof, sha

    def _sign(self, root: Path, candidate: Path, namespace: str = "swos-release") -> Path:
        key = root / "release-key"
        _run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key))
        _run(
            "ssh-keygen",
            "-Y",
            "sign",
            "-f",
            str(key),
            "-n",
            namespace,
            str(candidate / "SHA256SUMS"),
        )
        public = (root / "release-key.pub").read_text(encoding="utf-8").strip()
        allowed = root / "allowed_signers"
        allowed.write_text(f"{PRINCIPAL} {public}\n", encoding="utf-8")
        return allowed

    def test_candidate_contains_exact_sbom_provenance_conformance_and_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate, _, sha = self._candidate(root)
            manifest = json.loads(
                (candidate / "candidate-manifest.json").read_text(encoding="utf-8")
            )
            sbom = json.loads((candidate / "sbom.cdx.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["selected_sha"], sha)
            self.assertEqual(sbom["bomFormat"], "CycloneDX")
            self.assertTrue(sbom["components"])
            self.assertEqual(verify_checksums(candidate), [])
            self.assertEqual(verify_public_proof(candidate / "public-proof"), [])
            self.assertIn(
                "live_compatible_release", (candidate / "conformance-report.json").read_text()
            )
            self.assertTrue((candidate / "KNOWN-LIMITATIONS.md").read_text().strip())

    def test_dirty_or_mismatched_selected_head_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, sha = self._source_repo(root)
            proof, reproduction = self._proof_and_approval(root)
            (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
            with self.assertRaises(ReleaseEvidenceError):
                build_release_candidate(
                    repo_root=repo,
                    selected_sha=sha,
                    proof_dir=proof,
                    reproduction_path=reproduction,
                    release_approval_dir=proof / "approval",
                    out_dir=root / "candidate",
                    built_at=TIME,
                )
            with self.assertRaises(ReleaseEvidenceError):
                build_release_candidate(
                    repo_root=repo,
                    selected_sha="0" * 40,
                    proof_dir=proof,
                    reproduction_path=reproduction,
                    release_approval_dir=proof / "approval",
                    out_dir=root / "candidate-2",
                    built_at=TIME,
                )

    def test_tamper_or_incomplete_checksum_inventory_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate, _, _ = self._candidate(Path(tmp))
            (candidate / "KNOWN-LIMITATIONS.md").write_text("tampered", encoding="utf-8")
            self.assertTrue(verify_checksums(candidate))

    def test_trusted_signature_and_exact_human_approval_allow_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate, _, _ = self._candidate(root)
            allowed = self._sign(root, candidate)
            result = verify_release_candidate(
                candidate_dir=candidate,
                allowed_signers=allowed,
                principal=PRINCIPAL,
            )
            self.assertEqual(result["decision"], "allow", result["reasons"])

    def test_resigned_semantically_tampered_proof_still_denies_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate, _, _ = self._candidate(root)
            result_path = candidate / "public-proof" / "proof-result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["normalized_proof"]["status"] = "tampered"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            write_checksums(candidate)
            allowed = self._sign(root, candidate)

            gate = verify_release_candidate(
                candidate_dir=candidate,
                allowed_signers=allowed,
                principal=PRINCIPAL,
            )
            self.assertEqual(gate["decision"], "deny")
            self.assertTrue(any("public proof" in reason for reason in gate["reasons"]))

    def test_missing_wrong_principal_and_wrong_namespace_signatures_deny(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate, _, _ = self._candidate(root)
            allowed = self._sign(root, candidate)
            missing = verify_release_candidate(
                candidate_dir=candidate,
                allowed_signers=allowed,
                principal="wrong@example.invalid",
            )
            self.assertEqual(missing["decision"], "deny")

            (candidate / "SHA256SUMS.sig").unlink()
            key = root / "release-key"
            _run(
                "ssh-keygen",
                "-Y",
                "sign",
                "-f",
                str(key),
                "-n",
                "wrong-namespace",
                str(candidate / "SHA256SUMS"),
            )
            wrong_namespace = verify_release_candidate(
                candidate_dir=candidate,
                allowed_signers=allowed,
                principal=PRINCIPAL,
            )
            self.assertEqual(wrong_namespace["decision"], "deny")

    def test_sbom_rejects_unlocked_dependency_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy2("pyproject.toml", root / "pyproject.toml")
            (root / "requirements-dev.lock").write_text("jsonschema>=4\n", encoding="utf-8")
            with self.assertRaises(ReleaseEvidenceError):
                generate_sbom(root)


if __name__ == "__main__":
    unittest.main()
