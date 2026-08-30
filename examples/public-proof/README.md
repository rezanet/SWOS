# SWOS v1.1 Public Proof

This project is the canonical provider-free public-source demonstration for the
SWOS v1.1 reference runtime. It uses bounded, hash-pinned snapshots from official
NIST AI RMF resources. The snapshots make ordinary execution deterministic; they
do not imply that upstream pages are immutable or that NIST endorses SWOS.

Install the locked environment and SWOS package, then run and reproduce:

```powershell
python -m pip install --requirement requirements-dev.lock
python -m pip install --no-deps --no-build-isolation --editable .
python tools/run_public_proof.py --project examples/public-proof/project.json --out .tmp/proof-a
python tools/verify_public_proof.py --project examples/public-proof/project.json `
  --primary .tmp/proof-a --reproduce-at .tmp/proof-b `
  --out .tmp/reproduction-report.json
```

The second command executes an independent run and compares normalized governed
content. Runtime identifiers remain unique and are never normalized away in the
underlying audit packs.

Release candidate assembly additionally requires a clean exact Git head and a
real feature-005 human approval directory. SWOS writes `SHA256SUMS` but never
receives a private key. The release authority signs externally:

```powershell
ssh-keygen -Y sign -f <private-key> -n swos-release <candidate>/SHA256SUMS
```

Independent verification requires an explicit allowed-signers file and principal.
Without exact approval and a trusted signature, the release gate remains denied.
