# Data Model: SWOS v1.1 Evaluation and Human Approval

## Evaluation Subject

- `run_dir`: local subject location, not persisted in portable evidence.
- `run_id`, `work_id`, `runtime_version`: exact runtime identities.
- `manifest_sha256`: digest of the immutable run manifest.
- `integrity_chain_head`: final runtime integrity-chain hash.
- `governed_store_heads`: exact active store record hashes.
- `author`: stable actor identity responsible for the output.
- `review_assurance`: author/reviewer identities, execution modes, independence and limitations.
- `artifact_hashes`: repository-independent relative paths and SHA-256 values.

Validation: manifest, frozen schemas, governed stores and required artifacts must
verify before any plane can claim a bound subject.

## Plane Result

- `plane`: one of the eight frozen plane names.
- `gate_result`: `pass`, `fail`, `warn`, or `not_run`.
- `metrics`: numeric results with thresholds where applicable.
- `fixtures_run`: count of probes used.
- `failures`: fixture IDs and bounded reasons.

Validation: exactly one result per required plane; `fail` and `not_run` block;
duplicates or omissions block; all results share the enclosing subject.

## Evaluation Result

- Frozen `schema_version: 1.0.0`.
- Subject `work_id`, evaluation `run_id`, and harness version.
- `subject_versions` with runtime/schema/agent/model/retriever provenance.
- Eight `planes`.
- Deterministic `release_decision` recommendation and blocking planes.

Relationship: digest-bound to one Evaluation Subject and included in one
Approval Pack.

## Approval Pack

Ordered sections:

1. unsupported claims;
2. counter-evidence and limitations;
3. open reviewer findings;
4. eight-plane evaluation summary;
5. provenance and review-assurance summary;
6. manuscript.

Each section records a media type, relative source, content digest and item
count. The pack records the run manifest and evaluation-result digests.

Validation: order is fixed; every digest verifies; failed/unrun planes, open
blocker/major findings, incomplete provenance, or unknown review separation
prevent pack readiness.

## Human Release Decision

Represented as a frozen-schema SDL document with one decision:

- decision type `release`;
- at least `approve` and `reject` alternatives;
- selected option;
- non-empty rationale;
- run/evaluation/pack evidence references and digest bindings;
- human approver actor;
- author, contract-owner and evaluation-owner actor IDs for separation checks;
- timestamp and `swos.release-gate` policy basis;
- lifecycle `approved` for approval or `evaluated` for rejection.

Validation: only human actor type; exact evidence digests; stable IDs differ at
required separation boundaries; rejection remains valid evidence but cannot
open release.

## Release Gate Result

- exact run, evaluation, pack and decision digests;
- prerequisite results for runtime integrity, eight planes, blockers,
  provenance, reviewer separation, human identity and approval validity;
- final `allow` or `deny` decision with reasons;
- deterministic verification timestamp supplied by the caller or recorded at execution.

## State Transitions

```text
finalized run
  -> subject verified
  -> eight planes evaluated
  -> approval pack ready
  -> human decision recorded
  -> release allowed | release denied
```

No transition mutates the finalized run. Any changed digest returns to
`release denied` and requires a new evaluation/approval chain.
