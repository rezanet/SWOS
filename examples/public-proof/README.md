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

Release candidate assembly additionally requires a clean exact Git head and
one short maintainer-owned release record. Create it from the passing proof and
reproduction:

```powershell
python tools/create_release_record.py --selected-sha <40-hex-sha> `
  --proof <proof-a> --reproduction <reproduction-report.json> `
  --approved-by-id <maintainer-id> --approved-by-name <maintainer-name> `
  --approved-at <ISO-8601> --rationale <short-rationale> `
  --out <release-record.json>
python tools/build_release_candidate.py --selected-sha <40-hex-sha> `
  --proof <proof-a> --reproduction <reproduction-report.json> `
  --release-record <release-record.json> --out <candidate> `
  --built-at <ISO-8601>
```

Independent verification is local and credential-free:

```powershell
python tools/verify_release_candidate.py --candidate <candidate>
```

The candidate verifies exact-commit binding, deterministic test and proof
results, independent reproduction, source/citation hashes, SHA-256 checksums,
SBOM, provenance, conformance and known limitations. A detached signature is
not required; it is a future optional enhancement if SWOS distributes packages
or gains multiple maintainers.
