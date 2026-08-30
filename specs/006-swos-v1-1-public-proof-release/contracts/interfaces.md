# Interfaces: SWOS v1.1 Public Proof and Release

## Execute public proof

```powershell
python tools/run_public_proof.py --project examples/public-proof/project.json --out <proof-dir>
```

Creates one finalized runtime run, evaluation result, approval pack and
`proof-result.json`. It does not create a human approval.

## Independently reproduce

```powershell
python tools/verify_public_proof.py --project examples/public-proof/project.json `
  --primary <proof-a> --reproduce-at <proof-b> --out <reproduction-report.json>
```

Exit `0` only when snapshots and normalized governed outcomes match.

## Build release candidate

```powershell
python tools/build_release_candidate.py --selected-sha <40-hex-sha> `
  --proof <proof-a> --reproduction <reproduction-report.json> `
  --release-approval <release-approval-dir> --out <candidate-dir> `
  --built-at <ISO-8601>
```

Requires exact clean `HEAD`, a passing public proof/reproduction, and a passing
feature-005 human approval gate. Writes all candidate artifacts and `SHA256SUMS`.

## Sign checksums externally

```powershell
ssh-keygen -Y sign -f <private-key> -n swos-release <candidate-dir>/SHA256SUMS
```

SWOS never accepts or stores the private key. The resulting detached signature is
`SHA256SUMS.sig`.

## Verify candidate

```powershell
python tools/verify_release_candidate.py --candidate <candidate-dir> `
  --allowed-signers <allowed_signers> --principal <release-principal> `
  --out <release-gate.json>
```

Exit `0` only for a complete exact-commit candidate, exact human approval,
complete checksum inventory and trusted `swos-release` OpenSSH signature.

## Manual workflow

`workflow_dispatch` executes and uploads unsigned public-proof evidence at an
explicitly selected SHA. Candidate assembly remains blocked until that exact
proof receives human approval; external signing follows assembly. The workflow
is not triggered by pull requests and is not a branch-protection requirement.
