# Interface Contracts: Evaluation and Human Approval

## Runtime-bound evaluation

```text
python evals/harness/run_evals.py --all --system autonomous-swos \
  --run-dir <finalized-run> --out <evaluation-result.json> --fail-on-gate
```

Contract:

- `--run-dir` is mandatory when a system adapter is selected.
- the run must pass subject integrity before any plane runs;
- output conforms to the frozen evaluation-result 1.0.0 schema;
- exit `0` only when all selected gates pass, otherwise non-zero with no release claim;
- contract-only mode remains available but is labelled fixture conformance.

## Approval-pack preparation

```text
python -m swos_runtime.cli prepare-approval \
  --run-dir <finalized-run> \
  --evaluation <evaluation-result.json> \
  --author <actor.json> \
  --contract-owner <actor.json> \
  --evaluation-owner <actor.json> \
  --output <release-evidence-dir>
```

Contract:

- fails unless the subject and all eight planes pass prerequisites;
- writes a digest-protected pack with risk/evidence sections before manuscript;
- does not create or imply human approval.

## Human decision recording

```text
python -m swos_runtime.cli record-approval \
  --release-dir <release-evidence-dir> \
  --decision <human-decision-input.json>
```

Required decision input:

- `decision`: `approve` or `reject`;
- `approver`: actor object with `actor_type: human` and stable `actor_id`;
- `rationale`: non-empty text;
- `alternatives_considered`: at least approval and rejection;
- `reviewed_evidence`: exact run-manifest, evaluation and approval-pack digests;
- `policy_basis`: `swos.release-gate`;
- `timestamp`: ISO 8601 date-time.

Contract: writes a frozen-schema-compatible SDL decision document. Automation
may invoke the command with a human-supplied file but may not synthesize the
human identity or decision.

## Standalone release verification

```text
python tools/validate_release.py \
  --run-dir <finalized-run> --release-dir <release-evidence-dir>
```

Contract:

- exit `0` only for an exact, passing evaluation, intact pack, eligible human
  approval and all separation-of-duties checks;
- exit non-zero for rejection, missing evidence, mismatch, alteration or unknown;
- emits a machine-readable gate result without modifying the subject.
