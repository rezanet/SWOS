# Implementation Plan: SWOS v1.1 Programme Foundation

## Scope and intent

This plan implements only the foundation slice described by the approved
programme plan. The work is isolated on
`codex/swos-v1.1-programme-foundation` at exact base
`156e2b7faa70f9affce2ed93d7dc3cb6e19b938e`. PR #41 is an input to reconcile,
not a feature to reimplement.

## Technical context

| Area | Decision |
|---|---|
| Runtime language | Python 3.11+ using existing repository conventions |
| Validation | Standard library plus already-declared `jsonschema` |
| Human-readable artifacts | Markdown with repository-relative links |
| Machine-readable artifacts | JSON and Draft 2020-12 JSON Schema |
| CI | Existing GitHub Actions workflows with deterministic and manual profiles |
| Spec tooling | Spec Kit `v1.0.1`, Codex integration with bundled skills |
| New runtime dependencies | None |
| Version tracks | Core/specification `1.0.0`; reference runtime `v1.1`; Research Grade `v2.0` |

## Constitution check

| Principle | Design response | Result |
|---|---|---|
| Evidence before prose | Vision, roadmap and status reference evidence, provenance, audit and approval | Pass |
| Contract authority | Manifest schema and constitution define metadata; PR #41 contracts remain authoritative | Pass |
| Fail-closed assurance | Validator and live workflow reject missing, invalid or incomplete evidence | Pass |
| Host independence | No provider is used by deterministic workflows; live evidence is profile-scoped | Pass |
| Human approval | The plan documents human release approval and does not certify this branch | Pass |
| Separation of duties | Planning, implementation, validation and review remain distinct | Pass |
| Proof before breadth | Foundation precedes retrieval, stores, evaluation and public proof | Pass |
| Exact-head evidence | Baseline and manual live workflow record immutable SHAs | Pass |

## Design and implementation phases

### Phase 0 — baseline and initialization

1. Confirm the isolated worktree, branch and exact `origin/main` base.
2. Inventory PR #41 runtime, capability, portability and validator files so no
   implementation is duplicated.
3. Initialize Spec Kit v1.0.1 using the official brownfield command and retain
   the generated `.specify/` infrastructure and reviewed Codex skills.
4. Replace the constitution template with SWOS principles. Keep
   `.specify/feature.json` machine-local and do not touch the historical root
   `tasks/` records beyond their banners.

### Phase 1 — canonical documentation

1. Add `VISION.md` as the long-form philosophical authority.
2. Add a concise README pointer and reduce the architecture vision file to a
   technical derivative.
3. Expand `docs/roadmap.md` into the authoritative programme and Phase 1 plan,
   including dependencies, outputs, gates, exclusions and definitions of done.
4. Reconcile `PROGRESS.md` with PR #41 and the five-state capability vocabulary.

### Phase 2 — documentation authority contract

1. Define the manifest schema and corpus discovery policy.
2. Add the complete repository document inventory with authority, owner, status,
   version, canonical responsibility and reciprocal supersession metadata.
3. Record the three external research inputs by filename, hash, date, role and
   derived canonical documents without machine-specific paths.
4. Implement semantic validation and focused negative tests. The validator must
   collect actionable errors and fail with a non-zero exit code.

### Phase 3 — release-profile separation

1. Remove the live OpenAI job from `swos-ci.yml` while preserving existing
   deterministic job IDs and display names.
2. Add the manual live-evidence workflow with a required selected SHA input,
   resolved-SHA record, credential/provider/evidence fail-closed behavior and
   non-required artifact upload.
3. Restrict portability `--release` to `workflow_dispatch`, retain
   `--definitions-only` on the PR architecture job, and use the version-neutral
   workflow display name.
4. Add a deterministic workflow inspector and tests proving PR/push events do
   not schedule provider calls.

## File-level design

| File or directory | Responsibility |
|---|---|
| `.specify/memory/constitution.md` | SWOS Spec Kit constitution |
| `.specify/`, `.agents/skills/` | Reviewed Spec Kit v1.0.1 infrastructure |
| `specs/001-swos-v1-1-programme-foundation/` | Feature specification and design artifacts |
| `VISION.md`, `README.md`, `docs/architecture/01-vision-and-principles.md` | Canonical and derivative narrative |
| `docs/roadmap.md`, `PROGRESS.md`, `tasks/*.md` | Programme and historical status surfaces |
| `docs/document-manifest.json` | Documentation authority inventory |
| `schemas/document-manifest/document-manifest.schema.json` | Machine contract for the inventory |
| `tools/validate_document_manifest.py` | Schema, coverage and semantic validation |
| `tools/check_workflow_profiles.py` | Deterministic trigger/provider safety inspection |
| `tests/test_document_manifest.py`, `tests/test_workflow_profiles.py` | Focused positive and negative proof |
| `.github/workflows/swos-ci.yml` | Deterministic ordinary CI only |
| `.github/workflows/swos-live-evidence.yml` | Explicit manual live compatibility evidence |
| `.github/workflows/swos-prose-benchmark.yml` | Deterministic PR benchmark plus fail-closed manual live benchmark |
| `.github/workflows/swos-portability-gate.yml` | PR definitions and manual release portability profiles |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Spec Kit overwrites existing files | Initialization is reviewed; only new infrastructure and the intended constitution are retained |
| Manifest becomes stale | Validator derives expected corpus paths and fails on missing or extra entries |
| Document authority remains ambiguous | Each entry has one or more unique canonical domains and reciprocal supersession links |
| Live provider failure breaks PRs | Provider jobs are manual-only and absent from required deterministic contexts |
| PR #41 work is duplicated | Exact-head inventory and explicit exclusions are recorded in spec and roadmap |
| Historical records are erased | Root `tasks/` files are preserved with banners and historical manifest status |
| Claims overstate completion | Status vocabulary and progress text distinguish implemented/tested from demonstrated/certified |

## Verification checkpoints

1. Spec Kit prerequisite and artifact consistency analysis pass for this feature.
2. Manifest positive and negative tests, schema validation and coverage pass.
3. Workflow inspection passes and identifies no provider path on PR/push.
4. Existing schema, governance, skill, host-independence, vendor-leakage and
   definitions-only portability validators pass.
5. Existing Prose/runtime tests and Ruff format/lint pass, or an explicit local
   environment blocker is reported.
6. Final `git status` shows only intentional foundation changes in this
   worktree; no commit, push, merge, branch deletion or ruleset mutation occurs.

## Requirement traceability

| Requirements | Implementation tasks | Verification |
|---|---|---|
| FR-001, FR-002, FR-003 | T002–T008 | T025, placeholder scan |
| FR-004, FR-005, FR-006 | T018–T020 | T025, narrative inspection |
| FR-007, FR-008, FR-009 | T009–T012 | T023, manifest tests and validator |
| FR-010, FR-011 | T013–T017 | T023, workflow tests and trigger inspection |
| FR-012, FR-013, FR-014 | T021–T022 | T023–T025, exact-head status review |
| NFR-001, NFR-002, NFR-003, NFR-004 | T009–T017, T023–T025 | Ruff, schema, focused and repository-native gates |

## Delivery boundary

This branch stops after local verification. It does not commit, push, merge,
open a PR, delete branches or worktrees, change GitHub rulesets, run paid live
providers, or implement later Phase 1 runtime slices. The main agent or human
reviewer may decide separately how to deliver the uncommitted work.
