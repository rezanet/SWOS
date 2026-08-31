# Tasks: SWOS v1.1 Simple Release Record

## Phase 1: Specification

- [x] T001 [US1] Write the exact-SHA release-record requirements in `specs/007-simple-release-record/spec.md`.
- [x] T002 [US1] Record the simplicity decision and future signing boundary in `specs/007-simple-release-record/research.md`.
- [x] T003 [US1] Define record, candidate and gate fields in `specs/007-simple-release-record/data-model.md`.
- [x] T004 [US1] Document create, build, verify and profile interfaces in `specs/007-simple-release-record/contracts/interfaces.md`.

## Phase 2: Record implementation

- [x] T005 [US1] Implement the single release-record validator and creator in `swos_runtime/release_record.py`.
- [x] T006 [US1] Remove release-specific approval-pack and decision-ledger routing from `swos_runtime/public_proof.py` and `swos_runtime/cli.py`.
- [x] T007 [US1] Add the record creation entry point in `tools/create_release_record.py`.

## Phase 3: Candidate implementation

- [x] T008 [US2] Replace approval and signature inputs with the record in `swos_runtime/release_evidence.py`.
- [x] T009 [US2] Update candidate build and verification interfaces in `tools/build_release_candidate.py` and `tools/verify_release_candidate.py`.
- [x] T010 [US2] Retain source/citation hashes, checksums, SBOM, provenance, conformance and limitations in `swos_runtime/release_evidence.py`.

## Phase 4: Tests and workflow

- [x] T011 [US2] Add record, exact-SHA, tamper, checksum and unsigned-candidate tests in `tests/runtime/test_release_evidence.py`.
- [x] T012 [US2] Assert proof-only output and the current release status in `tests/runtime/test_public_proof.py` and `tests/runtime/test_cli.py`.
- [x] T013 [US3] Keep the public-proof workflow manual-only and describe the one-record handoff in `.github/workflows/swos-release-candidate.yml`.

## Phase 5: Documentation and validation

- [x] T014 [US3] Reconcile current release terminology in `docs/roadmap.md`, `examples/public-proof/README.md` and `specs/002-swos-v1-1-runtime-reconciliation/capability-ledger.md`.
- [x] T015 [US3] Mark superseded release-approval specifications and record feature metadata in `docs/document-manifest.json`.
- [x] T016 [US3] Run Spec Kit, schema, manifest, workflow, runtime and exact-head candidate validation from `specs/007-simple-release-record/quickstart.md`.

## Dependencies

- T001-T004 establish the current release contract.
- T005-T007 implement one record and remove obsolete release-specific routing.
- T008-T010 bind the record to the candidate while retaining useful evidence.
- T011-T013 prove deterministic behavior and manual-only workflow boundaries.
- T014-T016 reconcile documentation and verify the exact implementation head.

## Definition of done

The feature is complete when one exact-SHA record permits unsigned candidate
verification, every listed negative path fails closed, useful proof and supply
chain evidence remains, no current code or workflow requires OpenSSH or
allowed-signers machinery, and all repository validators pass.
