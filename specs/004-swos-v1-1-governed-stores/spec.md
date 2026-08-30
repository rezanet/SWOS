# Feature Specification: SWOS v1.1 Governed Stores and Audit Verification

## Objective

Implement capability-ledger gaps V11-STORE-001 through V11-STORE-006 and extend
V11-AUDIT-001. Preserve the frozen 1.0.0 EPG, SDL, RPM, Evidence Matrix and
Argument Graph documents while adding a runtime-owned append-only persistence
envelope around them. Core remains `1.0.0`, this reference-runtime slice
remains `v1.1`, and Research Grade remains `v2.0`.

## User stories

### US1 — Tamper-evident scholarly stores

As an auditor, I can reopen every governed store, verify every record and hash
link, and detect missing, reordered, malformed or altered history.

### US2 — Correction without erasure

As a responsible editor, I can correct or supersede a record while preserving
the prior record, actor, rationale and exact provenance.

### US3 — Governed programme memory

As a programme owner, I can write durable RPM items only when source grounding,
EPG references, an SDL decision, expiry and explicit human approval are present.

## Functional requirements

- **FR-001:** Persist EPG, SDL, RPM, Evidence Matrix and Argument Graph in
  separate file-backed append-only stores.
- **FR-002:** Every store record includes store/artifact identity, unique record
  ID, sequence, operation, timestamp, actor, payload hash, previous hash and
  record hash.
- **FR-003:** Reopening a store verifies JSON shape, sequence, identity, payload
  hash, previous hash and record hash before returning records.
- **FR-004:** Missing, malformed, reordered, duplicated or tampered records fail
  closed.
- **FR-005:** Correction and supersession target an active prior record and
  preserve that record unchanged.
- **FR-006:** Active-record views derive reciprocal superseded_by relationships
  without rewriting prior history.
- **FR-007:** RPM durable writes require source grounding, EPG references, an SDL
  decision, owner, expiry and timestamped human approval with rationale.
- **FR-008:** Finalization binds each frozen audit artifact to the active record
  in its corresponding governed store.
- **FR-009:** The autonomous-run validator requires and independently verifies
  all five store chains and artifact bindings.

## Non-functional requirements

- **NFR-001:** Writes are local, provider-neutral and deterministic apart from
  explicit IDs/timestamps recorded as evidence.
- **NFR-002:** Store append uses one canonical JSON representation and flushes
  durable bytes before reporting success.
- **NFR-003:** No frozen schema or capability contract changes.
- **NFR-004:** Ordinary PR checks remain credential-free and deterministic.
- **NFR-005:** Evaluation binding, human release approval and public proof remain
  outside this slice.

## Commands

```powershell
python -m unittest tests.runtime.test_stores tests.runtime.test_finalizer
python -m unittest discover -s tests/runtime -p 'test_*.py'
python tools/check_spec_kit_artifacts.py
python tools/validate_document_manifest.py
python tools/validate_schemas.py --strict
python tools/check_governance.py
python tools/check_host_independence.py
python tools/check_vendor_leakage.py
python tools/check_portability_acceptance.py --definitions-only
python -m ruff check swos_runtime tests/runtime tools
```

## Project structure

- `swos_runtime/stores.py` — generic chain, lifecycle and run-store bindings.
- `swos_runtime/finalizer.py` — persistence integration.
- `tools/validate_autonomous_run.py` — independent audit verification.
- `tests/runtime/test_stores.py` — store and destructive-path fixtures.
- `tests/runtime/test_finalizer.py` — complete-run persistence assertions.

## Code and document style

Use provider-neutral Python with typed boundaries and canonical JSON. Store
records are explicit evidence, not hidden implementation state. Frozen artifact
names and schema versions remain unchanged.

## Testing strategy

Use TDD at the append/reopen and finalizer seams. Mutate real store bytes for
negative tests: malformed JSON, deletion, reordering, duplication, payload
tampering, chain tampering, inactive supersession and incomplete RPM approval.
Then validate a complete finalizer output and the independent run verifier.

## Boundaries

- Always preserve prior bytes and verify before reading or appending.
- Always require explicit human approval for durable RPM writes.
- Ask first before changing any frozen contract or schema.
- Never silently truncate, repair or overwrite a governed store.
- Never implement release approval or public proof in this slice.

## Success criteria

- Store unit tests cover reopen, correction, supersession, RPM governance,
  malformed JSON, deletion, reordering and payload/hash tampering.
- A complete deterministic runtime finalization emits five verified store files.
- The autonomous-run validator rejects any store or artifact-binding mutation.
- Runtime, Prose, schema, governance, manifest, portability, Ruff, coverage and
  security gates pass.
