# Implementation Plan: SWOS v1.1 Runtime Reconciliation

## Scope and intent

This plan produces the exact capability inventory required by Phase 1 slice 1.
It changes documentation and programme evidence only. Runtime behavior remains
unchanged. Version tracks remain Core/specification `1.0.0`, reference runtime
`v1.1` and Research Grade `v2.0`.

## Dependency graph

```text
authoritative requirements
        |
PR #41 code and tests
        |
evidence classification
        |
capability ledger
        |
verified gap backlog
        |
later Spec Kit slices
```

## Implementation sequence

1. Freeze exact requirement and implementation sources.
2. Inventory PR #41 code, deterministic tests and available demonstrations.
3. Classify every requirement using the five-state vocabulary.
4. Record precise gaps and dependency-ordered dispositions.
5. Validate Spec Kit consistency and documentation-manifest coverage.
6. Rerun deterministic runtime and portability-definition evidence.

## Requirement traceability

| Requirement | Plan response |
|---|---|
| FR-001 | Ledger scope covers historical roadmap, current Phase 1 plan and PR #41 contract. |
| FR-002 | Stable IDs and accountable slices are mandatory ledger columns. |
| FR-003 | Four evidence classes are recorded separately. |
| FR-004 | State rules in `data-model.md` prohibit inference. |
| FR-005 | Every row includes verified gap and disposition. |
| FR-006 | Research notes identify snapshots, synthetic SUT and contract-marker limits. |
| FR-007 | Gap backlog follows retrieval, stores, evaluation and release dependencies. |
| FR-008 | Manifest entries cover every new Markdown artifact. |
| NFR-001 | Base and PR merge SHAs are recorded in spec, research and ledger. |
| NFR-002 | Validation commands are deterministic and offline. |
| NFR-003 | All artifacts use `1.0.0`, `v1.1` and `v2.0` consistently. |
| NFR-004 | No runtime, contract, schema or governance file is changed. |

## Verification checkpoints

### Checkpoint A — inventory completeness

- Every source requirement has a stable ledger row.
- Every PR #41 claim is either linked to code/tests or identified as partial.
- No row uses a test as certification evidence.

### Checkpoint B — gap integrity

- Cross-encoder, rights/retraction, durable stores, real-SUT evaluation, human
  approval and public release gaps are explicit.
- Existing OpenAlex/Crossref, work-order, CLI and audit artifact code is retained.
- Later tasks name only verified gaps.

### Checkpoint C — exact-head validation

- Spec Kit validates both `001` and `002` feature directories.
- Document manifest coverage is complete.
- Runtime tests, definitions-only portability and Ruff lint pass.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| PR prose overstates completion | Require source and deterministic-test evidence. |
| Partial artifact mistaken for store | Apply the capability-level state rule. |
| Synthetic evaluator mistaken for runtime binding | Trace whether `AutonomousSWOS.run` is invoked. |
| Live workflow mistaken for evidence | Require a checked-in exact-head result and reviewer identity. |
| Duplicate later implementation | Link every gap to existing nearby code and tests. |

## Boundaries

No runtime implementation occurs in this slice. The first follow-on is retrieval
and citation assurance; governed stores, evaluation/approval and public release
remain separate reviewed PRs.
