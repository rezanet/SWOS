# Requirements Checklist: SWOS v1.1 Programme Foundation

## Spec Kit and governance

- [x] FR-001: The repository uses the official Spec Kit v1.0.1 brownfield structure.
- [x] FR-001: The constitution records evidence before prose, contract authority,
  fail-closed assurance, host independence, human approval, separation of
  duties, proof before breadth and exact-head evidence.
- [x] FR-002: Spec Kit applicability and exemptions are explicit.
- [x] FR-003: `.specify/feature.json` is ignored and machine-local.
- [x] FR-003: Existing project instructions remain intact.
- [x] FR-003: The feature artifacts contain no unresolved template placeholders.

## Canonical narrative

- [x] FR-004: `VISION.md` contains the requested philosophical reasoning and non-goals.
- [x] FR-005: README contains a concise vision summary and link.
- [x] FR-005: The architecture vision is explicitly a technical derivative.
- [x] FR-006: `docs/roadmap.md` is the single authoritative programme and Phase 1 plan.
- [x] FR-006: Core/specification `1.0.0`, reference runtime `v1.1` and Research Grade
  `v2.0` are kept distinct.
- [x] FR-006: The roadmap has dependencies, outputs, gates, exclusions and definitions
  of done.

## Manifest contract

- [x] FR-007: The manifest has stable document IDs and repository-relative paths.
- [x] FR-007: Every document records title, owner, authority, status, version scheme,
  version, canonical responsibility, `supersedes` and `superseded_by`.
- [x] FR-007: The declared corpus includes the intended documentation roots and excludes
  tests, generated evidence, dogfood outputs and GitHub templates.
- [x] FR-009: All three research inputs are recorded by filename, SHA-256, date, role and
  derived canonical documents without absolute paths.
- [x] FR-008: JSON Schema validation is implemented.
- [x] FR-008: Semantic validation rejects missing, nonexistent, duplicate, invalid,
  non-reciprocal, active-superseded and multiple-canonical cases.
- [x] FR-008: Focused negative-path tests exist.

## CI and release profiles

- [x] FR-010: Ordinary PR/push workflows do not read provider credentials or make paid
  provider calls.
- [x] FR-010: Portability PR execution uses `--definitions-only`.
- [x] FR-011: Portability `--release` is dispatch-only.
- [x] FR-011: Live OpenAI evidence is in a manual-only workflow.
- [x] FR-011: Live workflow records and verifies the selected exact SHA.
- [x] FR-011: Live workflow fails closed on missing credentials, provider failure or
  missing evidence and uploads evidence as a non-required artifact.
- [x] FR-011: Autonomous and pigment acceptance remain manual-only.
- [x] FR-011: Existing deterministic context/job names are preserved.
- [x] FR-011: Workflow inspection tests prove the trigger separation.

## Non-functional requirements

- [x] NFR-001: Validation is deterministic and uses existing dependencies.
- [x] NFR-002: The manifest schema is valid Draft 2020-12 JSON Schema.
- [x] NFR-003: Workflow trigger and job conditions are auditable without a provider.
- [x] NFR-004: Documentation links and source-input records avoid machine-specific paths.

## Status and preservation

- [x] FR-012: `PROGRESS.md` recognizes PR #41's merged reference-runtime foundation.
- [x] FR-012: Status distinguishes specified, implemented, tested, demonstrated and
  certified.
- [x] FR-012: Full v1.1 is not claimed complete.
- [x] FR-012: Historical G-Prose95 task files remain present with concise banners.
- [x] FR-013/FR-014: Main checkout and its unrelated untracked builder reports are untouched.
- [x] FR-014: No commit, push, merge, branch deletion, worktree deletion or ruleset
  change is performed by this implementation.
