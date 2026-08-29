# Feature Specification: SWOS v1.1 Programme Foundation

**Feature Branch**: `codex/swos-v1.1-programme-foundation`

**Created**: 2026-08-29

**Status**: Implemented on this isolated branch

**Input**: Approved SWOS v1.1 Programme Plan — Luna Max Implementation

## Objective

Establish the control plane for the SWOS v1.1 reference-runtime programme. The
foundation makes the project philosophy, version tracks, documentation authority,
workflow profiles and delivery gates explicit and machine-checkable without
duplicating the runtime, portability or capability work already merged in PR
#41.

The primary users are SWOS maintainers, reviewers and future implementation
agents. Success means that a maintainer can identify the authoritative document,
understand what a version claim means, run deterministic checks without a
provider, and invoke live compatibility only against a recorded exact SHA.

The version tracks remain deliberately separate: Core/specification `1.0.0`,
reference runtime `v1.1`, and Research Grade `v2.0`.

## Capability map and build order

| Module ID | Responsibility | Depends on |
|---|---|---|
| `programme-governance` | Spec Kit constitution, applicability and version-track rules | Exact PR #41 baseline |
| `canonical-documents` | Vision, roadmap, README pointer and status reconciliation | `programme-governance` |
| `document-authority` | Documentation corpus manifest, schema and semantic validator | `canonical-documents` |
| `release-profiles` | Deterministic PR/offline/live workflow separation | `programme-governance`, `document-authority` |

Build order: `programme-governance` → `canonical-documents` →
`document-authority` → `release-profiles`. Status reconciliation is part of
`canonical-documents` and is verified after all modules are present.

## User scenarios and testing

### User Story 1 — Govern a programme change (Priority: P1)

As a SWOS maintainer, I want roadmap-scale changes to have a constitution,
specification, plan, tasks and requirements checklist so that implementation and
review share one explicit contract.

**Why this priority**: Without a governing specification, later runtime work can
silently broaden scope or duplicate PR #41.

**Independent Test**: Inspect the Spec Kit feature directory, run the official
prerequisite and analysis commands, and confirm that the four required artifacts
contain no unresolved placeholders and cover the same requirements.

**Acceptance Scenarios**:

1. **Given** an applicable roadmap milestone, **when** a maintainer starts work,
   **then** Spec Kit is required and the constitution records its scope,
   principles and gates.
2. **Given** a routine editorial correction, **when** a maintainer classifies
   the change, **then** the change is exempt from Spec Kit and does not require a
   new feature directory.
3. **Given** the v1.1 foundation feature, **when** analysis runs, **then** spec,
   plan, tasks and checklist have consistent requirement IDs, paths and gates.

### User Story 2 — Find the authoritative document (Priority: P1)

As a reviewer, I want every in-scope documentation file to declare authority,
status, version, ownership, canonical responsibility and supersession so that I
can tell which rule or explanation governs a decision.

**Why this priority**: Stale plans and competing narratives are a governance
risk even when the code is correct.

**Independent Test**: Run the manifest validator and its focused negative-path
tests against the repository corpus; remove or corrupt one entry and confirm the
validator fails with a specific error.

**Acceptance Scenarios**:

1. **Given** the declared documentation corpus, **when** validation runs,
   **then** every in-scope document has a unique stable ID and path and valid
   metadata.
2. **Given** a supersession relationship, **when** only one side records the
   link or the newer document remains active, **then** validation fails closed.
3. **Given** two documents claiming the same canonical authority domain,
   **when** validation runs, **then** validation reports multiple canonical
   documents.

### User Story 3 — Choose a safe release profile (Priority: P1)

As a maintainer, I want ordinary PR checks to be deterministic and live
compatibility to be an explicit, exact-SHA workflow so that exhausted credits or
provider failures cannot break ordinary development or create a false claim.

**Why this priority**: The previous live OpenAI checks consumed credits and were
operationally mixed with ordinary CI.

**Independent Test**: Run the workflow-profile inspection. It must prove that
PR/push workflows contain no provider call path, portability release mode is
dispatch-only, and the manual live workflow records an exact SHA and fails
closed on missing credentials, provider failures and missing evidence.

**Acceptance Scenarios**:

1. **Given** a pull request, **when** the ordinary workflows are scheduled,
   **then** they use deterministic checks and portability `--definitions-only`
   without provider credentials.
2. **Given** an explicit live workflow dispatch, **when** a selected SHA is
   checked out, **then** the workflow records the resolved SHA and uploads its
   evidence without making the job a required branch-protection context.
3. **Given** absent credentials, provider failure, exhausted credits or missing
   evidence, **when** live validation runs, **then** the workflow fails rather
   than reporting compatibility.

### User Story 4 — Understand what is complete (Priority: P2)

As a future contributor, I want a philosophical vision, roadmap and reconciled
status vocabulary so that I can distinguish the Core specification, reference
runtime and Research Grade tracks and avoid treating PR #41 as full v1.1
completion.

**Why this priority**: Accurate sequencing prevents premature breadth and keeps
human accountability visible.

**Independent Test**: Read `VISION.md`, `README.md`, `docs/roadmap.md` and
`PROGRESS.md`; verify the requested philosophical topics, version tracks,
dependencies, gates, exclusions and status states are present and consistent.

**Acceptance Scenarios**:

1. **Given** the repository narrative, **when** a reader follows the README
   vision link, **then** the long-form philosophy and explicit non-goals are in
   `VISION.md` and the README remains concise.
2. **Given** PR #41's merged runtime, **when** progress is read, **then** the
   reference-runtime foundation is recognized while full v1.1 remains open.
3. **Given** the old G-Prose95 task files, **when** a reader opens them,
   **then** a banner and manifest metadata identify them as historical records.

## Functional requirements

- **FR-001**: The repository MUST retain Spec Kit v1.0.1 initialization artifacts
  and a constitution with the eight approved SWOS principles.
- **FR-002**: The constitution MUST require Spec Kit for roadmap milestones,
  architecture, governance controls, frozen contracts/schemas, public
  interfaces and release gates, while exempting routine fixes and editorial
  corrections.
- **FR-003**: The feature MUST contain mutually consistent `spec.md`, `plan.md`,
  `tasks.md` and `checklists/requirements.md` artifacts with no unresolved
  placeholders in the feature artifacts.
- **FR-004**: `VISION.md` MUST record the philosophical rationale, accountability
  model, portability boundary, delivery sequence and explicit non-goals.
- **FR-005**: The README MUST contain only a concise vision summary and link to
  `VISION.md`; the architecture vision file MUST identify itself as a technical
  derivative.
- **FR-006**: `docs/roadmap.md` MUST be the authoritative programme and Phase 1
  plan, including dependencies, outputs, gates, exclusions and definitions of
  done for the three version tracks.
- **FR-007**: The manifest MUST cover the declared documentation corpus and
  record stable ID, path, title, owner, authority, status, version scheme,
  version, canonical responsibility, and reciprocal supersession arrays.
- **FR-008**: The manifest validator MUST reject missing corpus entries,
  nonexistent or duplicate IDs/paths, invalid metadata, broken supersession,
  active-but-superseded documents and duplicate canonical authority domains.
- **FR-009**: The manifest MUST record all three external research inputs by
  filename, SHA-256, date, role and derived canonical documents without absolute
  machine paths.
- **FR-010**: Ordinary PR and protected-push workflows MUST be deterministic,
  credential-free and paid-provider-free; portability on PR MUST use
  `--definitions-only`.
- **FR-011**: Live compatibility MUST be available only through explicit manual
  dispatch, record the exact selected SHA, fail closed on provider/credential/
  evidence failure, upload evidence, and remain non-required.
- **FR-012**: `PROGRESS.md`, README, roadmap, acceptance documentation, workflow
  names and manifest terminology MUST use the distinct states `specified`,
  `implemented`, `tested`, `demonstrated` and `certified` without calling full
  v1.1 complete.
- **FR-013**: Existing PR #41 runtime, portability, capability and validator
  functionality MUST remain unchanged except for profile/documentation wiring
  required by this foundation.
- **FR-014**: The main checkout, unrelated untracked builder reports, historical
  task records and GitHub rulesets MUST remain untouched by this implementation.

## Non-functional requirements

- **NFR-001**: Validation MUST be deterministic, explain failures, and use
  standard-library logic plus already-declared `jsonschema` where practical.
- **NFR-002**: The manifest schema MUST be a valid JSON Schema and the validator
  MUST validate both schema shape and repository-level semantic relationships.
- **NFR-003**: Workflows MUST remain auditable from their trigger and job
  conditions without requiring a network provider during ordinary checks.
- **NFR-004**: Documentation links MUST be repository-relative or stable external
  documentation URLs; source input records MUST not expose local absolute paths.

## Technology stack

- Python 3.11 or newer, with the repository's existing unittest, Ruff,
  `jsonschema` and command-line validators.
- Markdown for human-readable programme artifacts; JSON and JSON Schema for the
  document authority contract.
- GitHub Actions YAML for CI profiles; no new runtime dependency is introduced.
- Spec Kit CLI pinned to `v1.0.1`, initialized for Codex with bundled skills.

## Commands

The following commands are the feature's review and verification interface:

```text
uvx --from git+https://github.com/github/spec-kit.git@v1.0.1 specify --version
pwsh -NoProfile -File .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
python -m unittest tests/test_document_manifest.py tests/test_workflow_profiles.py
python tools/validate_document_manifest.py
python tools/check_workflow_profiles.py
python tools/validate_schemas.py --strict
python tools/check_governance.py
python tools/check_host_independence.py
python tools/check_vendor_leakage.py
python tools/check_portability_acceptance.py --definitions-only
python -m unittest discover -s tests/prose -p 'test_*.py'
python -m unittest discover -s tests/runtime -p 'test_*.py'
python -m ruff format --check swos_prose swos_runtime benchmark tools evals tests
python -m ruff check swos_prose swos_runtime benchmark tools evals tests
```

## Project structure

- `.specify/` — pinned Spec Kit project infrastructure and constitution.
- `.agents/skills/` — reviewed Codex/Spec Kit skills installed by the official
  brownfield initialization.
- `specs/001-swos-v1-1-programme-foundation/` — this feature's specification,
  design, task and requirements artifacts.
- `VISION.md`, `README.md`, `docs/roadmap.md`, `PROGRESS.md` — canonical
  programme narrative and status surface.
- `docs/document-manifest.json` — documentation authority manifest.
- `schemas/document-manifest/` — manifest JSON Schema.
- `tools/validate_document_manifest.py` and
  `tools/check_workflow_profiles.py` — deterministic foundation validators.
- `tests/` — focused manifest/workflow tests plus existing Prose/runtime suites.
- `swos_runtime/` and existing validators — PR #41 implementation substrate;
  they are not reimplemented by this feature.

## Code and document style

Python follows the existing Ruff configuration: four-space indentation, type
annotations for public functions, small pure validation helpers and actionable
stderr errors. JSON is two-space indented with stable key ordering. Markdown
uses direct language, repository-relative links, explicit authority and version
labels, and avoids turning research input into an unmarked normative rule.

```python
def validate_manifest_data(manifest: dict, repo_root: Path) -> list[str]:
    """Return deterministic, human-readable manifest validation failures."""

    errors: list[str] = []
    # Collect all errors so a reviewer can repair one manifest in one pass.
    return errors
```

## Testing strategy

The validator uses small unit tests for metadata and relationship rules. The
workflow inspector uses deterministic text inspection for trigger/job safety.
Existing schema, governance, skills, host-independence, vendor-leakage and
portability validators remain the integration boundary. The existing Prose and
runtime unittest suites and Ruff checks are the regression gate. Live provider
workflows are manual evidence only and are not part of ordinary merge testing.

## Boundaries

- **Always**: preserve exact-head evidence, use the manifest for documentation
  authority, test new validator behavior, keep live checks manual, and preserve
  unrelated work and historical records.
- **Ask first**: change a frozen contract/schema, add a runtime dependency,
  modify branch-protection rules, change version-track meaning, or expand into
  a later Phase 1 slice.
- **Never**: commit secrets, call paid providers from ordinary PR/push jobs,
  claim live compatibility without exact evidence, duplicate PR #41 runtime
  functionality, overwrite historical task files, rewrite history, or turn
  SWOS into a chatbot, SaaS product or autonomous publisher.

## Key entities

- **Document record**: one in-scope repository document with stable identity,
  authority, lifecycle status, version and supersession links.
- **Source input**: one external research file recorded by filename, hash, date,
  role and derived canonical documents.
- **Authority domain**: a named responsibility for which at most one document is
  canonical in the manifest.
- **Release profile**: deterministic PR, offline release or live-compatible
  release, each with explicit triggers and evidence obligations.
- **Capability state**: `specified`, `implemented`, `tested`, `demonstrated` or
  `certified`; states are not interchangeable.

## Success criteria

- **SC-001**: Official Spec Kit v1.0.1 is used for initialization and the
  feature artifacts contain zero unresolved template placeholders.
- **SC-002**: Manifest validation reports zero errors across every declared
  in-scope document and its schema passes Draft 2020-12 validation.
- **SC-003**: Focused negative tests cover all seven required failure classes
  and fail when each invalid condition is introduced.
- **SC-004**: Workflow inspection proves that every PR-triggered provider path
  is absent or dispatch-gated, portability `--release` is dispatch-only, and
  the manual live workflow records a resolved 40-character SHA.
- **SC-005**: Existing schema, governance, host-independence, vendor-leakage,
  definitions-only portability, Prose, runtime and Ruff checks pass or are
  reported with an explicit environmental blocker.
- **SC-006**: The repository narrative contains one canonical vision and one
  authoritative roadmap, while the full v1.1 programme remains explicitly open.

## Assumptions

- The exact PR #41 main head `156e2b7faa70f9affce2ed93d7dc3cb6e19b938e` is the
  authoritative implementation baseline for this slice.
- The repository's existing Python dependency lock and `jsonschema` dependency
  are sufficient; no new runtime package is needed.
- The three supplied external files remain available to the maintainer but are
  represented in-repository only by filename, hash and research role.
- GitHub rulesets and remote branch/PR state are outside this no-push foundation
  task and are not changed here.

## Open questions

There are no unresolved questions for the foundation slice. Later runtime
features must create their own Spec Kit feature and resolve their own design
questions before implementation.
