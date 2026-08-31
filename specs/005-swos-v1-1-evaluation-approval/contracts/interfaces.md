# Interface Contracts: Evaluation and Human Approval

> **Historical scope note:** These evaluation contracts remain a record of the
> completed feature. Do not use the former release approval commands; current
> source releases use `specs/007-simple-release-record/contracts/interfaces.md`.

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

## Current source-release boundary

The former multi-file release approval interface is retained only in the
historical implementation record and is no longer a runtime command. Current
source releases use the single exact-SHA record documented in
`specs/007-simple-release-record/contracts/interfaces.md`. The runtime
evaluation and scholarly decision evidence described above remain in force;
release signing and identity-policy machinery is not required.
