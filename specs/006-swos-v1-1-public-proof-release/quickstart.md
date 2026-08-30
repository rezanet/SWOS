# Quickstart: Public Proof and Release

## Deterministic tests

```powershell
python -m unittest tests.runtime.test_public_proof
python -m unittest tests.runtime.test_release_evidence
```

## Execute and independently reproduce

```powershell
python tools/run_public_proof.py --project examples/public-proof/project.json --out .tmp/proof-a
python tools/verify_public_proof.py --project examples/public-proof/project.json `
  --primary .tmp/proof-a --reproduce-at .tmp/proof-b `
  --out .tmp/reproduction-report.json
```

Expected: both runs are approved, all eight planes pass, and fingerprints match.

## Release boundary

Candidate assembly requires a real feature-005 human approval directory. Signing
requires a private key supplied directly to `ssh-keygen`; the key is never passed
to SWOS. Verification requires the corresponding explicit allowed-signers file.
Without both human approval and signature, the release gate must say `deny`.

## Repository gates

Run all commands from feature `005` plus public-proof tests, manifest validation,
coverage, locked dependency audit, Bandit and workflow-profile inspection.
