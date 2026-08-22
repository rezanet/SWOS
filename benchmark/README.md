# SWOS Prose Active Benchmark (M1)

This directory is the empirical release gate for SWOS Prose. It is intentionally
separate from `skills/swos-prose`: packaging must describe measured behaviour, not
pre-commit assumptions.

## Corpus

`corpus/` contains exactly 56 synthetic, governed fixtures in the active benchmark.
Every fixture carries:

- a source passage for `polish`;
- a fixed semantic probe candidate and a human-labelled relation
  (`equivalent` or `material_change`);
- an explicit deterministic diagnostics expectation;
- a `must_not_abstain` safety label;
- category and benchmark-group metadata;
- an opt-in `stability_probe` flag.

The active corpus identity is `0.3.0-m1`. This benchmark identity is deliberately
separate from the development package version (`0.3.0-dev`) and from the frozen
v0.2 evidence described below.

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
56 active sources. It then applies the deterministic diagnostics decision to calculate the
exact current fast-path counterfactual: provider tokens attributable to cases that
would have abstained are tokens avoided by Diagnostics. Non-abstaining cases use
the same generation path, so a second stochastic 56-case run is unnecessary.

### Stability

`--mode stability --stability-runs 5` runs the 11 inherited live probes five times
and records the PASS/REVIEW/REJECT distribution per fixture.

## Frozen v0.2 baseline

The first governed live baseline is frozen from GitHub Actions run `32450085166`
against commit `7637a487a93266e30fcbefbc40ad2266fec600b8`.

Release-critical results:

- 50 governed fixtures;
- 22 human-labelled material-change probes;
- 0 unsafe semantic `PASS` outcomes;
- 0 unsafe diagnostic abstentions;
- 3 deterministic diagnostics abstentions (6% coverage);
- 2,358 tokens avoided out of 77,593 observed baseline tokens (3.04%);
- 11 stability probes repeated five times;
- 0 unsafe `PASS` outcomes across the repeated stability draws.

Equivalent-pair non-PASS outcomes remain visible as quality/stability costs rather
than being reclassified as safety failures.

`baseline.json` is the compact canonical claim surface. The exact complete
CI-generated report, including per-fixture and per-draw records, is preserved in
`artifacts/raw-evidence-v0.2/` as an xz-compressed, base64-transported exact raw report with a reconstruction manifest. `FROZEN_AT` records the
run, commits, corpus digest, raw report digest, and archive digest.

The active runner reads `benchmark/corpus/` and expects 56 fixtures by default. The
historical frozen-v0.2 evidence path is `benchmark/artifacts/raw-evidence-v0.2/`,
with its 50-case claim surface in `benchmark/baseline.json`; it remains immutable
and is not used as the active corpus.

## Commands

Deterministic corpus and diagnostics contract:

```bash
python3 benchmark/runner.py \
  --mode validate \
  --expect-count 56 \
  --output /tmp/swos-prose-benchmark-validate.json
```

Full live baseline (manual evidence campaign):

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

A frozen baseline is evidence, not a hand-written performance claim. The compact
canonical baseline may summarize the measured result, but every summary value must
be traceable to the preserved raw CI report and its cryptographic digest.

A frozen baseline must never be edited to make a result look better. New live
evidence requires a new benchmark version or a clearly documented rerun. Ordinary
PR pushes run the deterministic 56-case active corpus/diagnostics contract; the
expensive live Luna campaign is deliberately manual.
