# Interface Contracts: SWOS v1.1 Simple Release Record

## Create the record

```powershell
python tools/create_release_record.py --selected-sha <40-hex-sha> `
  --proof <proof-dir> --reproduction <reproduction-report.json> `
  --approved-by-id <maintainer-id> --approved-by-name <maintainer-name> `
  --approved-at <ISO-8601> --rationale <short-rationale> `
  --out <release-record.json>
```

The command reads completed proof and reproduction evidence and writes one
record. It does not call a provider, create a key, or infer an approval from
runtime state.

## Build a candidate

```powershell
python tools/build_release_candidate.py --repo <clean-checkout> `
  --selected-sha <40-hex-sha> --proof <proof-dir> `
  --reproduction <reproduction-report.json> `
  --release-record <release-record.json> --out <candidate-dir> `
  --built-at <ISO-8601>
```

Assembly requires an exact clean `HEAD`, verified public proof, passing
independent reproduction and a record whose SHA, proof fingerprint, file
hashes and source snapshot hashes match. It writes the record, release-record
gate, checksums, SBOM, build provenance, conformance report and limitations.

## Verify a candidate

```powershell
python tools/verify_release_candidate.py --candidate <candidate-dir>
```

Exit `0` only when the candidate's checksums, proof, reproduction, record,
exact-SHA bindings, SBOM, provenance, conformance and limitations verify. The
command has no `--allowed-signers`, `--principal` or provider credential input.

## Profiles

- **Deterministic PR**: ordinary PR checks using local fixtures and validators.
- **Offline public release**: manual proof/reproduction and candidate assembly
  without provider credentials.
- **Live compatible release**: explicit manual workflow only; it is not claimed
  by the current source candidate unless its own evidence passes.

Detached package signing is not part of this interface. It may be added later
if SWOS distributes packages or gains multiple maintainers.
