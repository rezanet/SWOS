# Data Model: SWOS v1.1 Simple Release Record

## Release record

`release-record.json` is a small, human-readable object with exactly these
top-level fields:

```json
{
  "record_version": "swos.release-record.v1",
  "selected_sha": "<40 lowercase hex characters>",
  "decision": "approve",
  "approved_by": {"id": "<maintainer-id>", "name": "<display name>"},
  "approved_at": "<timezone-aware ISO-8601 timestamp>",
  "rationale": "<short review rationale>",
  "tests": {
    "deterministic_pr": "passed",
    "offline_public_release": "passed"
  },
  "proof": {
    "status": "passed",
    "run_id": "<proof run id>",
    "fingerprint": "<proof-result SHA-256 fingerprint>",
    "reproduction": "passed"
  },
  "evidence": {
    "proof_result_sha256": "<file SHA-256>",
    "project_sha256": "<file SHA-256>",
    "reproduction_sha256": "<file SHA-256>",
    "source_sha256": {"<source-id>": "<snapshot SHA-256>"}
  }
}
```

The validator checks all fields, the selected commit, proof and reproduction
values, exact file digests and the source snapshot map in the public project.

## Candidate manifest

The existing `swos.release-candidate.v1` manifest keeps its version and adds
the state `ready_for_public_release`. It names `release-record.json`,
`release-record-gate.json`, `SHA256SUMS`, public proof, SBOM, provenance,
conformance and known limitations as required artifacts. It has no signature,
principal or allowed-signers field.

## Release-record gate

`release-record-gate.json` contains:

```json
{
  "gate_version": "swos.release-record-gate.v1",
  "decision": "allow",
  "selected_sha": "<exact SHA>",
  "release_record": "release-record.json",
  "reasons": []
}
```

The gate is generated only after the record and evidence validate. The gate is
covered by `SHA256SUMS`, and candidate verification also requires the exact
fields and values shown above, including an empty `reasons` list. This prevents
rewriting the checksum inventory from turning a changed gate into an accepted
candidate.

## Evidence retained

The public project continues to carry source snapshot and citation-related
hashes. The candidate retains `proof-result.json`, project metadata,
reproduction output, audit run files, `SHA256SUMS`, CycloneDX SBOM, build
provenance, conformance and known limitations.
