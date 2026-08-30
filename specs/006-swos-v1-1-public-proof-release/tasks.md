# Tasks: SWOS v1.1 Public Proof and Release

## Phase 1: Setup

- [x] T001 Register feature documents and public-proof authorities in `docs/document-manifest.json`.
- [x] T002 Update dependency state in `docs/roadmap.md`.
- [x] T003 Add hash-pinned NIST project inputs in `examples/public-proof/project.json` and `examples/public-proof/README.md`.

## Phase 2: Foundational tests

- [x] T004 Write source-integrity and independent-reproduction tests in `tests/runtime/test_public_proof.py`.
- [x] T005 [P] Write candidate, SBOM, checksum, signature and approval negative tests in `tests/runtime/test_release_evidence.py`.

## Phase 3: User Story 1 - Public proof

- [x] T006 [US1] Implement project loading and source verification in `swos_runtime/public_proof.py`.
- [x] T007 [US1] Implement the real-runtime NIST proof provider and proof fingerprint in `swos_runtime/public_proof.py`.
- [x] T008 [US1] Add proof execution CLI in `tools/run_public_proof.py`.
- [x] T009 [US1] Add independent replay verifier in `tools/verify_public_proof.py`.
- [x] T010 [US1] Execute and record the expected semantic proof in `examples/public-proof/expected-proof.json`.

## Phase 4: User Story 2 - Release evidence

- [x] T011 [US2] Implement exact-clean-head checks and CycloneDX SBOM generation in `swos_runtime/release_evidence.py`.
- [x] T012 [US2] Implement build provenance, conformance, limitations and checksum inventory in `swos_runtime/release_evidence.py`.
- [x] T013 [US2] Add candidate assembly CLI in `tools/build_release_candidate.py`.

## Phase 5: User Story 3 - Signing and verification

- [x] T014 [US3] Implement external OpenSSH signature and checksum verification in `swos_runtime/release_evidence.py`.
- [x] T015 [US3] Add standalone candidate verifier in `tools/verify_release_candidate.py`.
- [x] T016 [US3] Add manual-only candidate workflow in `.github/workflows/swos-release-candidate.yml`.

## Phase 6: Reconciliation and delivery

- [x] T017 Update V11-PROOF-001 and V11-REL-001 through V11-REL-006 in `specs/002-swos-v1-1-runtime-reconciliation/capability-ledger.md`.
- [x] T018 Document exact release commands and authority boundary in `examples/public-proof/README.md`.
- [x] T019 Run all deterministic, quality, security, Spec Kit and manifest gates documented in `specs/006-swos-v1-1-public-proof-release/quickstart.md`.
- [x] T020 Close `specs/006-swos-v1-1-public-proof-release/checklists/requirements.md` and perform exact-head review.

## Dependencies

- T001-T003 establish authority and source inputs.
- T004-T005 are test-first prerequisites.
- T006-T010 complete the independently reproducible proof.
- T011-T013 require a passing proof and feature-005 approval evidence.
- T014-T016 require a complete candidate but never a repository-held private key.
- T017-T020 reconcile evidence and deliver the slice.

## MVP

User Story 1 is independently demonstrable. The programme is not release-complete
until User Stories 2 and 3 also pass with a real human approval and signature.
