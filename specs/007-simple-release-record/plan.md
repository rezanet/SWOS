# Implementation Plan: SWOS v1.1 Simple Release Record

**Branch**: `codex/swos-simplify-release-gate` | **Date**: 2026-08-31
**Spec**: [spec.md](spec.md)

## Summary

Replace release-specific approval packs, decision ledgers and mandatory
detached-signature verification with one small exact-SHA release record. Keep
the existing proof, reproduction, source/citation hashes, SBOM, provenance,
conformance profiles, checksums and limitations. Remove only the release
approval machinery; scholarly decision-ledger and governed-store behavior is
unchanged.

## Technical Context

**Language**: Python 3.11+
**Dependencies**: existing runtime and standard library; no signing dependency
**Storage**: readable JSON evidence and SHA-256 inventory
**Testing**: `unittest`, Ruff, schema/manifest/workflow validators
**Target**: offline Windows/Linux/macOS with manual public-proof evidence
**Constraints**: exact clean Git head, no PR credentials, frozen Core schemas,
small release contract

Version authority remains explicit: Core/specification `1.0.0`, reference
runtime `v1.1`, Research Grade `v2.0`.

## Constitution Check

- **Evidence before prose**: the release record points to proof, reproduction
  and source hashes; it cannot replace them.
- **Contract authority**: the record is a release-evidence format and does not
  revise frozen Core contracts or scholarly stores.
- **Fail-closed assurance**: missing, malformed, changed or mismatched record
  and evidence fields deny assembly or verification.
- **Host independence**: validation uses local files, Git and standard Python;
  no host, model, provider or signature service is required.
- **Human approval**: one explicit maintainer record remains the release
  decision; automation only validates the statement and evidence.
- **Separation of duties**: scholarly acquisition, synthesis, verification and
  governance roles remain in the runtime; the release record deliberately does
  not invent a second identity system.
- **Proof before breadth**: the single public proof remains the demonstrated
  release path.
- **Exact-head evidence**: selected SHA is checked at assembly and propagated
  to the record, candidate manifest, gate, provenance and conformance report.

No constitutional conflict remains after the release-specific approval path is
replaced by one explicit human-owned record.

## Architecture

```text
public proof + independent reproduction
                │
                ▼
       release-record.json
                │ exact SHA + evidence hashes + approval
                ▼
  release_evidence.py ── SBOM + provenance + conformance + checksums
                │
                ▼
       release-record-gate.json
                │
                ▼
  verify_release_candidate.py  (no provider, key or trust-policy input)
```

## Project Structure

```text
swos_runtime/
├── public_proof.py
├── release_record.py
└── release_evidence.py
tools/
├── create_release_record.py
├── build_release_candidate.py
└── verify_release_candidate.py
tests/runtime/
├── test_public_proof.py
├── test_release_evidence.py
└── test_cli.py
specs/007-simple-release-record/
```

## Delivery Phases

1. Write the feature specification, record contract, research note, task list
   and acceptance checklist.
2. Implement record creation/validation and remove the release-specific
   approval module, CLI commands and signature verifier.
3. Update candidate assembly, verification, public proof, tests and manual
   workflow to use the record and retain deterministic evidence.
4. Reconcile roadmap, capability ledger, README/example/operator docs and
   historical Spec Kit records.
5. Run manifest, Spec Kit, schema, workflow, runtime, Ruff and exact-head
   candidate verification at the implementation commit.

## Requirement Traceability

| Requirement | Planned evidence |
|---|---|
| FR-001 | Exact clean-head check in `swos_runtime/release_evidence.py` and negative tests in `tests/runtime/test_release_evidence.py` |
| FR-002, FR-003 | Small record validator in `swos_runtime/release_record.py` and record tests |
| FR-004, FR-005 | Record proof/reproduction/source hash binding and public-proof tests |
| FR-006 | `swos_runtime/public_proof.py` output and absence assertions in `tests/runtime/test_public_proof.py` |
| FR-007 | Candidate builder, manifest, SBOM, provenance, conformance, limitation and checksum tests |
| FR-008, FR-009 | Candidate verifier and unsigned/tamper/mismatch tests |
| FR-010 | Conformance report profiles and workflow/documentation inspection |
| FR-011 | `.github/workflows/swos-ci.yml`, `swos-portability-gate.yml`, workflow validator and tests |
| FR-012 | `VISION.md`, `docs/roadmap.md`, example/operator docs and feature contracts |

## Simplicity and Risk Controls

- Keep the release record as one JSON file with one validator module.
- Reuse existing SHA-256, public-proof and SBOM code rather than adding a
  cryptographic package or service.
- Do not modify SDL/EPG/RPM store contracts; they serve scholarly output
  quality rather than package-release identity.
- Keep the manual workflow proof-only; the maintainer creates the record after
  reviewing exact evidence.
- Preserve old feature documentation as superseded history rather than
  rewriting its implementation record.

## Release Boundary

The current source-release gate is complete when exact-SHA evidence and one
valid release record verify. It does not claim live compatibility, package
distribution or cryptographic maintainer identity. Signing can be considered
later if the distribution or maintainer threat model changes.
