# Feature Specification: SWOS v1.1 Evaluation and Human Approval

> **Historical scope note:** This feature's runtime evaluation and scholarly
> human-judgement controls remain part of SWOS. Its release-specific approval
> pack and multi-step release authority are superseded by
> `specs/007-simple-release-record/`.

**Feature Branch**: `codex/swos-v1.1-evaluation-approval`

**Created**: 2026-08-30

**Status**: Draft

**Input**: Bind all eight evaluation planes to a finalized SWOS runtime run, require complete provenance and zero unresolved blockers, preserve reviewer independence evidence, and add an explicit human release-approval record with separation of duties.

## Objective

Complete the Phase 1 evaluation and human-approval slice without changing Core
`1.0.0`, the v1.1 reference-runtime boundary, or the Research Grade `v2.0`
horizon. Replace fixture-only runtime claims with exact finalized-run evidence
and make human release authority independently verifiable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evaluate the real run (Priority: P1)

As an evaluation owner, I can run every required evaluation plane against one
actual finalized SWOS run and see which immutable run evidence each plane used.

**Why this priority**: A fixture-only result cannot justify a claim about the
runtime that will be released.

**Independent Test**: Finalize a deterministic run, execute all eight planes
against that run, and verify that each plane records the exact subject identity,
uses runtime artifacts, and fails when its required artifact is absent or altered.

**Acceptance Scenarios**:

1. **Given** a complete finalized run, **When** all eight planes execute, **Then** every plane is evaluated against that same run and records a pass or fail.
2. **Given** a fixture contract without a finalized run, **When** a runtime-bound result is requested, **Then** the request fails and cannot claim runtime coverage.
3. **Given** a missing, altered, or incompletely proven runtime artifact, **When** a dependent plane executes, **Then** that plane fails closed.

---

### User Story 2 - Review an ordered approval pack (Priority: P2)

As the responsible human approver, I receive unresolved claims, counter-evidence,
review findings, evaluation results, provenance, and only then the manuscript, so
I can make an accountable release decision without being anchored by fluent prose.

**Why this priority**: Human approval is meaningful only when the evidence and
risks being approved are presented explicitly and first.

**Independent Test**: Build an approval pack from a fully evaluated run and
verify ordering, exact evidence bindings, completeness, and rejection of any
pack with failed planes, unresolved blockers, incomplete provenance, or missing
review-independence evidence.

**Acceptance Scenarios**:

1. **Given** a run with eight passing planes and no unresolved blockers, **When** an approval pack is prepared, **Then** risk and evidence sections precede the manuscript and every section is bound to the exact run.
2. **Given** any failed or unrun plane, open blocker, incomplete provenance, or missing independent-review evidence, **When** an approval pack is requested, **Then** preparation fails closed.

---

### User Story 3 - Record and verify human release approval (Priority: P3)

As a release auditor, I can verify a human approval decision that names the
approver, rationale, alternatives, evidence, policy basis, timestamp, subject
run, and separation-of-duties facts without permitting automation to approve.

**Why this priority**: Passing technical gates is necessary but is not human
accountability for release.

**Independent Test**: Submit valid and invalid approval decisions for the same
approval pack and verify that only a complete human decision by an eligible,
separate approver produces a passing release gate.

**Acceptance Scenarios**:

1. **Given** a valid approval pack, **When** an eligible human records an approval with rationale and exact evidence references, **Then** the release gate passes and the immutable decision is auditable.
2. **Given** an automated actor, the author as approver, an evaluation owner who conflicts with the contract owner, or incomplete approval evidence, **When** approval is recorded, **Then** the release gate fails.
3. **Given** an approval bound to another run or an altered pack, **When** release is verified, **Then** the approval is rejected.

### Edge Cases

- A plane is duplicated, omitted, marked `not_run`, or names a different subject run.
- A finalized run is internally valid but its manifest or governed-store chain is later altered.
- Reviewer independence is unknown, self-asserted, or shares the author identity.
- The approval is a rejection rather than an approval; the decision remains evidence but release stays blocked.
- A valid approval is replayed against a different run, evaluation result, or approval pack.
- The approval rationale is blank, the evidence list is empty, or the policy basis is not the release policy.
- Two authority roles use different labels but resolve to the same actor identity.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Runtime-bound evaluation MUST require one complete finalized SWOS run as its subject.
- **FR-002**: All eight required planes MUST evaluate the same exact subject run and immutable manifest.
- **FR-003**: Every plane MUST use relevant runtime artifacts and production assurance controls, not fixture conformance alone.
- **FR-004**: Missing, altered, duplicated, unrun, or failed plane evidence MUST block a release recommendation.
- **FR-005**: The evaluation result MUST record subject versions, exact run identity, plane metrics, blocking planes, and a deterministic decision.
- **FR-006**: Complete provenance, valid governed stores, and zero unresolved blocker or major findings MUST be release prerequisites.
- **FR-007**: Review evidence MUST identify authoring and reviewing actors and state independence limitations truthfully.
- **FR-008**: The approval pack MUST present unsupported claims, counter-evidence, open findings, evaluation evidence, provenance, and the manuscript in that order.
- **FR-009**: Every approval-pack section MUST be bound to the exact run and protected by a verifiable content digest.
- **FR-010**: Release approval MUST be an explicit decision record containing alternatives, rationale, evidence references, human approver identity, timestamp, and policy basis.
- **FR-011**: Only an actor identified as human MAY approve a release; automated actors MAY only prepare or recommend.
- **FR-012**: The approver MUST be distinct from the author, and the evaluation owner MUST be distinct from the contract owner.
- **FR-013**: Approval MUST be rejected when its subject run, evaluation result, approval pack, or evidence bindings do not match exactly.
- **FR-014**: A rejection decision MUST remain auditable and MUST keep release blocked.
- **FR-015**: A standalone verifier MUST fail closed unless the runtime, evaluation, approval pack, and human decision all pass together.

### Key Entities

- **Evaluation Subject**: The exact finalized run, its immutable manifest, artifact identities, runtime version, and assurance provenance.
- **Plane Result**: One required evaluation plane, its metrics, evidence dependencies, outcome, and failure reasons.
- **Evaluation Result**: The complete eight-plane decision bound to one evaluation subject.
- **Approval Pack**: An ordered, digest-protected presentation of risks, evidence, review state, evaluation, provenance, and manuscript.
- **Release Decision**: The human decision, alternatives, rationale, evidence bindings, policy basis, identities, and timestamp.
- **Release Gate Result**: The independently verifiable allow or deny outcome over all prerequisite evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 8 required planes identify and evaluate the same exact finalized run in every runtime-bound evaluation.
- **SC-002**: 100% of missing, altered, duplicated, failed, or unrun plane cases block release in deterministic negative tests.
- **SC-003**: 100% of passing plane results include traceable subject identity, relevant artifact evidence, and production-control provenance.
- **SC-004**: Every approval pack places all risk and evidence sections before the manuscript and verifies every section digest.
- **SC-005**: 100% of automated, self-approval, conflicting-owner, blank-rationale, and cross-run replay attempts are rejected.
- **SC-006**: One complete deterministic run can be evaluated, packed, human-approved through an explicit test record, and independently verified without provider credentials.
- **SC-007**: No ordinary pull-request check reads provider credentials or makes a paid provider call.

## Assumptions

- Core contracts and schemas remain frozen at `1.0.0`; this feature adds runtime behavior around them without changing their meaning.
- A finalized runtime run may pass automated assurance while still awaiting a separate human release decision.
- Deterministic tests may use an explicitly labelled sample human record to prove validation behavior; they do not constitute a real publication approval.
- The public-source proof, release artefact signing, compatibility certification, and actual v1.1 release approval remain in the next programme slice.
- Existing reviewer assurance and governed-store evidence are reused and strengthened rather than replaced.

## Commands

```powershell
python -m unittest tests.runtime.test_evaluation tests.runtime.test_release_approval
python -m unittest discover -s tests/runtime -p 'test_*.py'
python -m unittest discover -s tests/prose -p 'test_*.py'
python tools/check_spec_kit_artifacts.py
python tools/validate_document_manifest.py
python tools/validate_schemas.py --strict
python tools/check_governance.py
python tools/lint_skills.py
python tools/check_host_independence.py
python tools/check_vendor_leakage.py
python tools/check_portability_acceptance.py --definitions-only
python tools/check_workflow_profiles.py
python -m ruff check swos_runtime evals tools tests/runtime
```

## Project Structure

- `swos_runtime/evaluation.py` owns verified subject and plane behavior.
- `swos_runtime/release_approval.py` owns packs, decisions and release verification.
- `evals/harness/` remains the thin command adapter.
- `tools/validate_release.py` provides independent verification.
- `tests/runtime/` proves the real finalized-run and human-authority paths.

## Code and Document Style

Use provider-neutral typed Python, canonical JSON digests, repository-relative
portable evidence paths and concise authority-aware documentation. Runtime
controls have one owner; the harness must not copy policy logic.

## Testing Strategy

Use TDD at subject, plane, pack and human-decision boundaries. Generate a real
deterministic finalized run, mutate its artifacts and sidecars, and prove every
unknown or mismatch fails closed. Re-run all repository-native gates at the
committed exact head.

## Boundaries

- Always preserve finalized-run bytes and bind sidecars by digest.
- Always require a human actor and separation of duties for approval.
- Ask before changing any frozen schema or contract.
- Never let the harness certify fixture conformance as runtime evidence.
- Never describe deterministic sample approvals as real release authority.
- Never implement public proof, signing or v1.1 certification in this slice.
