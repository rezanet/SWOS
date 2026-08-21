# SWOS Prose v0.2 Benchmark

This directory is the empirical release gate for SWOS Prose. It is intentionally
separate from `skills/swos-prose`: packaging must describe measured behaviour, not
pre-commit assumptions.

## Corpus

`corpus/` contains exactly 50 synthetic, governed fixtures. Every fixture carries:

- a source passage for `polish`;
- a fixed semantic probe candidate and a human-labelled relation
  (`equivalent` or `material_change`);
- an explicit deterministic diagnostics expectation;
- a `must_not_abstain` safety label;
- category and benchmark-group metadata;
- an opt-in `stability_probe` flag.

The 11 stability probes reproduce the current trusted live verifier suite so issue
#32 can be measured as a distribution rather than a lucky single draw.

## What the benchmark measures

### Diagnostics

Diagnostics are **not** graded as a grammar or style classifier. Their contract is
asymmetric and fail-closed. The benchmark therefore reports:

- unsafe abstentions: `must_not_abstain=true` but diagnostics returned
  `NO_CHANGE_RECOMMENDED`;
- governed abstention coverage;
- exact expectation/signal regressions for the current reviewed corpus.

An unreviewed good sentence that proceeds to rewrite is conservative inefficiency,
not a diagnostic correctness failure.

### Semantic safety

`--mode safety` compares each source with its fixed semantic probe candidate.
For human-labelled `material_change` pairs, any verifier `PASS` is an unsafe
automatic-acceptance failure. `REVIEW` and `REJECT` are fail-closed.

For human-labelled `equivalent` pairs, `PASS` is preferred, while `REVIEW` or
`REJECT` is recorded as quality/stability cost rather than a safety failure.

### Token efficiency

`--mode efficiency` performs one observed diagnostics-disabled polish run for all
50 sources. It then applies the deterministic diagnostics decision to calculate the
exact current fast-path counterfactual: provider tokens attributable to cases that
would have abstained are tokens avoided by Diagnostics. Non-abstaining cases use
the same generation path, so a second stochastic 50-case run is unnecessary.

### Stability

`--mode stability --stability-runs 5` runs the 11 inherited live probes five times
and records the PASS/REVIEW/REJECT distribution per fixture.

## Commands

Deterministic corpus and diagnostics contract:

```bash
python3 benchmark/runner.py \
  --mode validate \
  --expect-count 50 \
  --output /tmp/swos-prose-benchmark-validate.json
```

Full live baseline:

```bash
export OPENAI_API_KEY=...
export SWOS_PROSE_RUN_LIVE_OPENAI=1
python3 benchmark/runner.py \
  --mode all \
  --stability-runs 5 \
  --rewriter-model gpt-5.6-luna \
  --verifier-model gpt-5.6-luna \
  --fail-on-unsafe \
  --output /tmp/swos-prose-benchmark/baseline.json
```

## Baseline policy

`baseline.json` is a release evidence artefact, not a hand-written performance
claim. Until the first full live CI run is captured and reviewed, it remains
explicitly marked `pending_live_evidence`. Before this PR can leave draft status,
replace it with the exact CI-generated report and record the producing commit/run.

A frozen baseline must never be edited to make a result look better. New evidence
requires a new benchmark version or a clearly documented rerun.
