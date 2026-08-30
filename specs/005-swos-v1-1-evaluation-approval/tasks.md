# Tasks: SWOS v1.1 Evaluation and Human Approval

**Input**: Design documents from `specs/005-swos-v1-1-evaluation-approval/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/interfaces.md`

## Phase 1: Setup

- [x] T001 Register all feature documents in `docs/document-manifest.json`.
- [x] T002 Reconcile the implemented scope and dependency status in `docs/roadmap.md`.

## Phase 2: Foundational

- [x] T003 Write shared deterministic finalized-run construction in `evals/harness/deterministic_subject.py`.
- [x] T004 Write subject-integrity and production-control binding tests in `tests/runtime/test_evaluation.py`.
- [x] T005 [P] Write approval-pack and release-gate negative tests in `tests/runtime/test_release_approval.py`.

## Phase 3: User Story 1 - Evaluate the real run (Priority: P1)

**Goal**: Bind all eight planes to one verified finalized runtime run.

**Independent Test**: `tests.runtime.test_evaluation` proves one exact subject,
eight unique planes, production-control use, schema validity and fail-closed
artifact mutation behavior.

- [x] T006 [US1] Implement verified evaluation-subject loading in `swos_runtime/evaluation.py`.
- [x] T007 [US1] Implement eight production-bound plane evaluations in `swos_runtime/evaluation.py`.
- [x] T008 [US1] Reduce the system adapter to subject delegation in `evals/harness/autonomous_sut.py`.
- [x] T009 [US1] Require exact subject binding and emit frozen-schema-compatible output in `evals/harness/run_evals.py`.
- [x] T010 [US1] Update deterministic CI invocation in `.github/workflows/swos-ci.yml`.

## Phase 4: User Story 2 - Review an ordered approval pack (Priority: P2)

**Goal**: Prepare immutable risk-first evidence for accountable human review.

**Independent Test**: approval tests prove fixed section order, exact digests,
complete plane/provenance/review prerequisites and manuscript-last behavior.

- [x] T011 [US2] Implement approval-pack construction and digest verification in `swos_runtime/release_approval.py`.
- [x] T012 [US2] Add provider-neutral approval-pack CLI routing in `swos_runtime/cli.py`.
- [x] T013 [US2] Document runtime-bound evaluation and risk-first approval behavior in `evals/README.md`.

## Phase 5: User Story 3 - Record and verify human approval (Priority: P3)

**Goal**: Accept only a complete, separate, exact human release decision.

**Independent Test**: approval tests prove human-only authority, rationale and
policy evidence, author/approver and owner separation, rejection retention,
cross-run replay denial and standalone verification.

- [x] T014 [US3] Implement SDL-compatible human decision recording in `swos_runtime/release_approval.py`.
- [x] T015 [US3] Implement the fail-closed release verifier in `swos_runtime/release_approval.py`.
- [x] T016 [US3] Add human-decision CLI routing in `swos_runtime/cli.py`.
- [x] T017 [US3] Add standalone verification in `tools/validate_release.py`.

## Phase 6: Reconciliation and exact-head validation

- [x] T018 Update V11-EVAL-001/002, V11-REVIEW-001/002 and V11-APPROVAL-001 evidence in `specs/002-swos-v1-1-runtime-reconciliation/capability-ledger.md`.
- [x] T019 Run the deterministic commands in `specs/005-swos-v1-1-evaluation-approval/quickstart.md` and all repository quality/security gates.
- [x] T020 Re-run Spec Kit analysis and close the exact-head checklist in `specs/005-swos-v1-1-evaluation-approval/checklists/requirements.md`.

## Dependencies & Execution Order

- T001-T002 establish authority records and programme status.
- T003-T005 are test-first prerequisites.
- T006-T010 complete US1 and unblock approval-pack construction.
- T011-T013 depend on a passing runtime-bound evaluation.
- T014-T017 depend on an intact approval pack.
- T018-T020 follow implementation and exact-head validation.

## Parallel Opportunities

- T005 can proceed in parallel with T003-T004 because it writes a separate test file.
- Documentation in T013 can proceed after the US2 interface stabilises.
- T017 can proceed after the verifier signature in T015 stabilises.

## Implementation Strategy

1. Prove US1 first: no runtime-bound claim without a real subject.
2. Add the immutable approval pack without granting release authority.
3. Add human decision recording and standalone verification.
4. Reconcile authority documents and run exact-head gates.
