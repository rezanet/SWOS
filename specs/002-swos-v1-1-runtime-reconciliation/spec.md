# Feature Specification: SWOS v1.1 Runtime Reconciliation

## Objective

Reconcile every reference-runtime `v1.1` requirement against the exact merged
implementation before any further runtime code is written. The output is a
reviewable capability ledger that separates specification, implementation,
deterministic testing, reproducible demonstration and independent certification.

The reconciliation starts from `origin/main` at
`5eec89e88e11e9659299d51c1bbf8289b81e464f`. PR #41 merge
`156e2b7faa70f9affce2ed93d7dc3cb6e19b938e` is implementation evidence, not
proof that every `v1.1` requirement is complete.

### User Story 1 — Inspect existing capability

As a maintainer, I can trace every `v1.1` requirement to exact code, tests,
demonstrations, certification evidence or a verified gap, so existing PR #41
work is not duplicated.

### User Story 2 — Select only verified gaps

As an implementer, I receive an ordered gap backlog whose entries name the
missing behavior and acceptance evidence, so later slices implement only what
the repository does not already prove.

### User Story 3 — Audit the reconciliation

As a reviewer, I can reproduce the ledger from repository authority documents,
the PR #41 merge and deterministic local checks without provider credentials.

## Functional Requirements

- **FR-001:** Inventory every explicit `v1.1` requirement in the historical
  roadmap, current Phase 1 roadmap and PR #41 governed outcome contract.
- **FR-002:** Assign every requirement a stable capability ID and one accountable
  Phase 1 slice.
- **FR-003:** Record exact implementation, test, demonstration and certification
  evidence separately; an absent evidence class must be explicit.
- **FR-004:** Assign only the highest state proved by evidence: `specified`,
  `implemented`, `tested`, `demonstrated` or `certified`.
- **FR-005:** Record a concrete verified gap and disposition for every requirement
  that is not fully proved.
- **FR-006:** Distinguish partial artifacts from completed capabilities; contracts,
  schemas, snapshots and synthetic fixtures must not be mistaken for complete
  stores, cross-encoders, live proof or certification.
- **FR-007:** Produce a dependency-ordered implementation backlog from verified
  gaps only.
- **FR-008:** Add every new reconciliation document to the documentation authority
  manifest and preserve historical planning records.

## Non-Functional Requirements

- **NFR-001:** Evidence is repository-relative and tied to exact Git SHAs.
- **NFR-002:** Reconciliation and validation are deterministic and make no paid
  provider calls.
- **NFR-003:** Version terminology remains Core/specification `1.0.0`, reference
  runtime `v1.1` and Research Grade `v2.0`.
- **NFR-004:** The slice does not revise frozen contracts, schemas, governance
  policy or public runtime behavior.

## Commands

```powershell
python tools/check_spec_kit_artifacts.py
python tools/validate_document_manifest.py
python -m unittest tests/test_document_manifest.py tests/test_spec_kit_artifacts.py
python -m unittest discover -s tests/runtime -p 'test_*.py'
python tools/check_portability_acceptance.py --definitions-only
python -m ruff check swos_runtime evals tools tests
```

## Project Structure

- `specs/002-swos-v1-1-runtime-reconciliation/` — specification, evidence model,
  plan, tasks, checklist, research notes and capability ledger.
- `swos_runtime/` — PR #41 runtime implementation inspected as evidence.
- `tests/runtime/` — deterministic runtime tests inspected as evidence.
- `evals/harness/` — evaluation binding inspected for real-SUT coverage.
- `docs/document-manifest.json` — authority metadata for reconciliation documents.
- `docs/roadmap.md` — canonical programme sequence and Phase 1 gates.

## Code and Document Style

Ledger evidence uses repository-relative paths and symbol or test names:

```text
swos_runtime/orchestrator.py::AutonomousSWOS.run
tests/runtime/test_runtime.py::RuntimeTests.test_complete_injected_run_is_approved_and_inspectable
```

Use stable IDs, conservative state labels and explicit em dashes for missing
evidence. Do not use prose such as “appears complete” as a status.

## Testing Strategy

Run the Spec Kit consistency checker across all feature directories, validate
manifest coverage, rerun all 51 deterministic runtime tests, and run
definitions-only portability. The ledger is reviewed requirement by requirement
against exact paths and test names. No live provider result is required or
permitted as an ordinary reconciliation gate.

## Boundaries

- Always: inspect exact merged code and tests before assigning a state.
- Always: preserve the distinction among implementation, test, demonstration and
  certification.
- Ask first: any change to a frozen Core `1.0.0` contract, schema or governance
  policy.
- Never: infer cross-encoder execution from a semantic-rerank contract marker.
- Never: infer a durable store from a generated snapshot file.
- Never: infer human approval or certification from an automated `APPROVED` state.
- Never: implement retrieval, stores, evaluation or release gaps in this
  reconciliation-only PR.

## Success Criteria

- Every identified `v1.1` requirement has one ledger row and evidence verdict.
- PR #41 functionality is retained and no runtime source is modified.
- Every unproved requirement has a bounded next-slice disposition.
- Spec, plan, tasks, checklist, research notes and ledger agree.
- Spec Kit, manifest, runtime, portability-definition and lint checks pass.
