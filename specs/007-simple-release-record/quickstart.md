# Quickstart: SWOS v1.1 Simple Release Record

## Deterministic tests

```powershell
python -m unittest tests.runtime.test_public_proof
python -m unittest tests.runtime.test_release_evidence
python -m unittest tests.runtime.test_cli
```

## Execute and reproduce public proof

```powershell
python -m pip install --requirement requirements-dev.lock
python -m pip install --no-deps --no-build-isolation --editable .
python tools/run_public_proof.py --project examples/public-proof/project.json --out .tmp/proof-a
python tools/verify_public_proof.py --project examples/public-proof/project.json `
  --primary .tmp/proof-a --reproduce-at .tmp/proof-b `
  --out .tmp/reproduction-report.json
```

Expected: both provider-free runs pass all eight evaluation planes and the
normalized proof fingerprints match. The proof output contains no approval
pack or release decision ledger.

## Create and verify the release record

Run this from a clean checkout at the exact selected SHA:

```powershell
python tools/create_release_record.py --selected-sha <HEAD> `
  --proof .tmp/proof-a --reproduction .tmp/reproduction-report.json `
  --approved-by-id <maintainer-id> --approved-by-name <maintainer-name> `
  --approved-at 2026-08-31T00:00:00+00:00 `
  --rationale "Exact deterministic tests and public-proof reproduction pass." `
  --out .tmp/release-record.json
python tools/build_release_candidate.py --selected-sha <HEAD> `
  --proof .tmp/proof-a --reproduction .tmp/reproduction-report.json `
  --release-record .tmp/release-record.json --out .tmp/candidate `
  --built-at 2026-08-31T00:00:00+00:00
python tools/verify_release_candidate.py --candidate .tmp/candidate
```

Expected: `decision` is `allow`. No signature, allowed-signers file or
provider credential is required. The candidate retains source/citation hashes,
checksums, a concise CycloneDX SBOM, build provenance, conformance and known
limitations.

## Manual evidence workflow

`.github/workflows/swos-release-candidate.yml` runs only through
`workflow_dispatch`, checks out the supplied exact SHA, executes public proof
and independent reproduction, records the resolved SHA and uploads evidence.
The maintainer reviews that evidence and creates the one release record. The
workflow is not a pull-request check or branch-protection requirement.

## Verification gates

```powershell
python tools/validate_schemas.py --strict
python tools/validate_document_manifest.py
python tools/check_workflow_profiles.py
python tools/check_spec_kit_artifacts.py
python -m unittest discover -s tests/runtime -p 'test_*.py'
```

Signing remains a future optional enhancement if SWOS later distributes
packages or has multiple maintainers.
