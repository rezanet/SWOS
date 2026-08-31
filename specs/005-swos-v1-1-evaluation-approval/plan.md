# Implementation Plan: SWOS v1.1 Evaluation and Human Approval

> **Historical scope note:** Runtime evaluation remains relevant. The former
> release approval-pack/decision implementation is superseded by feature `007`.

**Branch**: `codex/swos-v1.1-evaluation-approval` | **Date**: 2026-08-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-swos-v1-1-evaluation-approval/spec.md`

## Summary

Replace fixture-only claims about the Autonomous SWOS system with an evaluation
subject that loads and verifies one actual finalized runtime run. Bind all eight
planes to that subject and production controls, emit a frozen-schema-compatible
evaluation result, prepare an anti-anchoring approval pack, and provide a
standalone release gate that accepts only a complete human SDL decision with
exact evidence bindings and separation of duties.

## Technical Context

**Language/Version**: Python 3.11 or later

**Primary Dependencies**: Python standard library, jsonschema, existing SWOS runtime and frozen schema validators

**Storage**: Local immutable JSON/JSONL/Markdown run artifacts and release-evidence sidecars

**Testing**: unittest, repository evaluation harness, schema/governance/manifest validators, Ruff, coverage, Bandit and pip-audit

**Target Platform**: Provider-neutral CLI/CI on Windows and Linux

**Project Type**: Python library and CLI evaluation/release subsystem

**Performance Goals**: Evaluate all eight deterministic planes and verify one local release bundle in under 30 seconds on CI hardware

**Constraints**: Credential-free ordinary PR execution; frozen 1.0.0 schemas/contracts; no automated release approval; exact-head and exact-artifact evidence

**Scale/Scope**: One finalized run, eight planes, one approval pack and one human decision per release candidate

**Version Tracks**: Core/specification `1.0.0`; reference runtime `v1.1`; Research Grade `v2.0`

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **Evidence before prose**: approval-pack risk and evidence sections precede the manuscript.
- **Contract authority**: evaluation output and release decision reuse frozen evaluation and SDL schemas without schema edits.
- **Fail closed**: absent run evidence, plane coverage, provenance, review separation, rationale, human identity or exact digest blocks release.
- **Host independence**: the subject and approval contracts identify providers only as provenance.
- **Human approval**: automation prepares evidence; only an explicit human decision may open the release gate.
- **Separation of duties**: author/approver and contract-owner/evaluation-owner identity conflicts are rejected.
- **Proof before breadth**: scope is limited to the existing reference runtime and eight existing planes.
- **Exact-head evidence**: evaluation and approval bind the run manifest plus content digests.
- **Development controls**: TDD, deterministic PR checks, manifest coverage and exact-head validation are required.

No constitution exception is required.

## Phase 0 Research Decisions

Research is consolidated in [research.md](research.md). The key decisions are:

1. Treat a verified finalized run as the evaluation subject; fixture dictionaries alone cannot identify a runtime under test.
2. Preserve the finalized run and store evaluation/approval evidence as hash-bound sidecars.
3. Reuse the frozen evaluation-result and SDL decision-ledger schemas.
4. Separate automated plane recommendation from the human release gate.
5. Require explicit identity separation and truthful reviewer-assurance evidence.

## Phase 1 Design

The entity and transition model is in [data-model.md](data-model.md). Public CLI
and file contracts are in [contracts/interfaces.md](contracts/interfaces.md),
and [quickstart.md](quickstart.md) defines end-to-end acceptance.

Post-design constitution re-check: passed. The design adds no schema, authority,
provider, or automated-approval exception.

## Project Structure

### Documentation (this feature)

```text
specs/005-swos-v1-1-evaluation-approval/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── interfaces.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
swos_runtime/
├── evaluation.py          # verified runtime subject and production-bound planes
├── release_approval.py    # approval pack, human decision and release verification
└── cli.py                 # release-evidence commands

evals/harness/
├── autonomous_sut.py      # thin adapter over swos_runtime.evaluation
└── run_evals.py           # exact run-dir binding and schema-valid result

tools/
└── validate_release.py    # standalone fail-closed release verifier

tests/runtime/
├── deterministic_subject.py # shared deterministic real-run builder
├── test_evaluation.py
└── test_release_approval.py

.github/workflows/
└── swos-ci.yml            # deterministic exact-subject evaluation invocation
```

**Structure Decision**: Extend the existing runtime, harness, tools, and runtime
test layout. Keep the harness adapter thin so production assurance logic has one
owner and cannot drift into a parallel synthetic implementation.

## Testing Strategy

1. Write failing tests proving that runtime-bound evaluation rejects a missing or altered subject and that all eight planes use one verified run.
2. Write failing tests for missing planes, incomplete provenance, unresolved findings and review-identity conflicts.
3. Write approval-pack ordering and digest-tamper tests.
4. Write human actor, rationale, policy, identity separation, rejection and cross-run replay tests.
5. Run all eight planes against a deterministic run produced through the real runtime/finalizer path.
6. Re-run runtime, Prose, frozen schema, governance, manifest, portability, workflow, coverage and security gates at the committed exact head.

## Requirement Traceability

| Requirements | Design owner | Verification |
|---|---|---|
| FR-001, FR-002, FR-003 | Verified Evaluation Subject and production-bound planes | Real finalized-run test and fixture-only rejection |
| FR-004, FR-005 | Evaluation Result | Plane omission/duplication/mutation tests and frozen-schema validation |
| FR-006, FR-007 | Subject prerequisites and review assurance | Provenance, blocker and actor-separation negative tests |
| FR-008, FR-009 | Approval Pack | Fixed-order and digest-tamper tests |
| FR-010, FR-011 | Human Release Decision | SDL validation, human actor and rationale tests |
| FR-012, FR-013 | Separation and exact bindings | Identity-conflict and cross-run replay tests |
| FR-014, FR-015 | Release Gate Result | Rejection retention and standalone fail-closed verification |

## Delivery Boundaries

- Do not change frozen schemas or contracts.
- Do not treat the deterministic sample approval used by tests as a real release approval.
- Do not execute paid or credentialed provider calls in ordinary PR checks.
- Do not generate SBOMs, signatures, conformance certification or public-source proof in this slice.
- Do not merge or delete branches until exact-head CI and review state are clean.

## Complexity Tracking

No constitution violations require justification.
