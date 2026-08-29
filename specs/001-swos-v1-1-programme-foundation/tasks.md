# Tasks: SWOS v1.1 Programme Foundation

All tasks are complete on this implementation branch unless explicitly marked
otherwise. The historical root `tasks/plan.md` and `tasks/todo.md` are not this
feature's task list.

## Phase 1 — Setup

- [x] T001 Confirm exact base `156e2b7faa70f9affce2ed93d7dc3cb6e19b938e` and isolated worktree in `specs/001-swos-v1-1-programme-foundation/plan.md`
- [x] T002 [P] Retain reviewed Spec Kit v1.0.1 brownfield infrastructure under `.specify/` and `.agents/skills/`
- [x] T003 Replace the constitution template with the eight SWOS principles in `.specify/memory/constitution.md`

## Phase 2 — Foundational controls

- [x] T004 [P] Define the feature requirements and acceptance criteria in `specs/001-swos-v1-1-programme-foundation/spec.md`
- [x] T005 [P] Define the document and release-profile data model in `specs/001-swos-v1-1-programme-foundation/data-model.md`
- [x] T006 [P] Record research-input decisions in `specs/001-swos-v1-1-programme-foundation/research.md`

## Phase 3 — User Story 1: programme governance

- [x] T007 [US1] Create mutually consistent Spec Kit plan, tasks and requirements checklist in `specs/001-swos-v1-1-programme-foundation/`
- [x] T008 [US1] Add the runnable foundation validation guide in `specs/001-swos-v1-1-programme-foundation/quickstart.md`

## Phase 4 — User Story 2: document authority

- [x] T009 [US2] Add the Draft 2020-12 manifest schema in `schemas/document-manifest/document-manifest.schema.json`
- [x] T010 [US2] Add complete document corpus metadata and source-input records in `docs/document-manifest.json`
- [x] T011 [US2] Implement schema, coverage, metadata, supersession and canonical-domain validation in `tools/validate_document_manifest.py`
- [x] T012 [US2] Add positive and negative manifest tests in `tests/test_document_manifest.py`

## Phase 5 — User Story 3: release profiles

- [x] T013 [US3] Remove live provider execution from ordinary CI in `.github/workflows/swos-ci.yml`
- [x] T014 [US3] Add exact-SHA manual live compatibility evidence in `.github/workflows/swos-live-evidence.yml` and make the historical manual benchmark fail closed in `.github/workflows/swos-prose-benchmark.yml`
- [x] T015 [US3] Separate portability definitions from manual release execution in `.github/workflows/swos-portability-gate.yml`
- [x] T016 [US3] Implement deterministic workflow trigger/provider inspection in `tools/check_workflow_profiles.py`
- [x] T017 [US3] Add workflow-profile tests in `tests/test_workflow_profiles.py`

## Phase 6 — User Story 4: status and narrative

- [x] T018 [US4] Add the canonical philosophical vision in `VISION.md` and concise README link in `README.md`
- [x] T019 [US4] Convert the architecture vision into a technical derivative in `docs/architecture/01-vision-and-principles.md`
- [x] T020 [US4] Expand the authoritative programme and Phase 1 roadmap in `docs/roadmap.md`
- [x] T021 [US4] Reconcile merged PR #41 status and five-state vocabulary in `PROGRESS.md`
- [x] T022 [US4] Mark historical G-Prose95 planning records in `tasks/plan.md` and `tasks/todo.md`

## Phase 7 — Verification

- [x] T023 Run manifest, workflow, schema, governance, skills, host-independence, vendor-leakage and definitions-only portability checks in `tools/validate_document_manifest.py` and `tools/check_workflow_profiles.py`
- [x] T024 Run Prose/runtime unit suites and Ruff format/lint checks
- [x] T025 Run Spec Kit prerequisites and official read-only cross-artifact analysis for this feature with `tools/check_spec_kit_artifacts.py`

## Dependencies and parallel opportunities

Dependency order is `T001` → `T002-T003` → `T004-T008` → `T009-T012` →
`T013-T017` → `T018-T022` → `T023-T025`. Within a phase, tasks marked `[P]`
can be prepared in parallel after their listed prerequisites; validation waits
for all artifact changes.

## Independent story tests

| Story | Independent proof |
|---|---|
| US1 | Spec Kit prerequisites plus read-only analysis report no placeholders or cross-artifact conflicts. |
| US2 | Manifest validator and negative tests cover missing, duplicate, invalid, broken, active-superseded and multiple-canonical cases. |
| US3 | Workflow inspector proves PR/push determinism, dispatch-only release and exact-SHA live evidence. |
| US4 | Narrative inspection finds the philosophical topics, version tracks, Phase 1 gates and reconciled PR #41 status. |

## Implementation strategy

The smallest useful delivery is the programme control plane: constitution,
canonical vision/roadmap, manifest contract and safe release profiles. Runtime
retrieval, governed stores, evaluation binding and public proof are deliberately
separate later Spec Kit features.
