# Implementation Plan: SWOS v1.1 Governed Stores

## Scope

Build a small provider-neutral persistence layer around the existing frozen
audit artifacts. This slice does not redesign the schemas or introduce a
database, service, identity platform or release approval mechanism.
Core/specification remains `1.0.0`, the reference runtime remains `v1.1`,
and Research Grade remains `v2.0`.

## Dependency order

1. Define negative-path tests and the canonical store-record contract.
2. Implement append/reopen/verify and active-record derivation.
3. Implement correction and supersession against active records.
4. Add the human-approved RPM write wrapper.
5. Persist all five final audit artifacts and verify exact bindings.
6. Extend the autonomous-run validator and capability ledger.
7. Run exact-head deterministic and security gates.

## Architecture

swos_runtime/stores.py owns the generic JSONL chain and the five-artifact store
set. Frozen artifacts remain canonical interchange documents; store records
provide lifecycle, chain-of-custody and immutable history.

Each record hashes its canonical payload and then hashes the complete record
material including the prior record hash. Corrections and supersessions append a
new record with one supersedes target. The prior bytes never change.

## Requirement traceability

| Requirement | Implementation |
|---|---|
| FR-001 | GovernedJsonStore instances for all five artifacts |
| FR-002 | Canonical record material and actor/chain fields |
| FR-003 | Reopen verification before record access |
| FR-004 | Destructive-path byte mutation tests |
| FR-005 | Correction and supersession append APIs |
| FR-006 | Derived lifecycle and active-record views |
| FR-007 | ResearchProgrammeMemoryStore approval gate |
| FR-008 | persist_run_stores and verify_run_stores |
| FR-009 | tools/validate_autonomous_run.py store verification |
| NFR-001 | Local provider-neutral Python implementation |
| NFR-002 | Canonical JSON append, flush and fsync |
| NFR-003 | Frozen schemas and contracts unchanged |
| NFR-004 | Existing deterministic workflow profile retained |
| NFR-005 | Evaluation, human release approval and proof excluded |

## Boundaries

- Always preserve prior records and fail closed on uncertainty.
- Always bind store heads to exact frozen artifact bytes.
- Never overwrite, silently repair or truncate a store.
- Never treat a runtime-generated approval as human approval.
- Defer evaluation planes, approval ingestion for release and public proof.
