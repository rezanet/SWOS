# SWOS engineering progress

This ledger records repository-grounded state and exact evidence. Percentages are
quality measurements, not claims about completion of the larger SWOS roadmap.

## Verified M1 history

- PR #36, **M1: Self-Healing Engine (Repair Loop)**, was squash-merged from
  expected head `75cd3db94946a9928961c3e62a13971b78972ac1` as
  `010de54ebcd0ec3dba98f75d71ec3a503d02a98b`.
- Post-merge SWOS CI run `32563838579` (#149) passed every semantic, schema,
  governance, evaluation-plane and live-evidence job but failed only DCO because
  the GitHub-generated squash commit lacked a `Signed-off-by` trailer. This is
  retained as a historical deviation; main history was not rewritten.
- PR #17 was safely refreshed from M1 main, its stale template-link review finding
  was fixed and resolved, and it was squash-merged with an explicit DCO trailer as
  `ff0b4d52048b6e07b23fb1a33c064b47ee174b95`. Post-merge SWOS CI run
  `32564424163` (#151) passed all jobs, including DCO.

## G2 — Engineering Substrate and CI Quality Baseline

PR #37: [G2: Engineering Substrate and CI Quality Baseline](https://github.com/rezanet/SWOS/pull/37)

- exact base: `ff0b4d52048b6e07b23fb1a33c064b47ee174b95`
- current branch head: `fea3ba7d9f3b2258e9df09c658aaf8d01a0e47d6`
- commits: `ff2605bf69eae7e857c32016cadcf2d50f4b290a` (Ruff formatting baseline),
  `fa8612dd2ddfacb9156c644489fe1db124db0311` (quality substrate),
  `3ba1e92268dc23f0f3f308caa19f9c591720d122` (progress ledger),
  `fea3ba7d9f3b2258e9df09c658aaf8d01a0e47d6` (quiet coverage-policy tests)
- no v1.1 reranker/reference-runtime work is included or started

### Local evidence

- 186 deterministic Prose tests passed; 11 live tests skipped without a key.
- executable `swos_prose` coverage measured at **85.39%** against a new 80%
  whole-package floor; M1 critical-module floors also passed:
  `repair.py` 83.23%, `pipeline.py` 90.98%, `causal_scope.py` 98.78%,
  `deterministic.py` 98.57%, `propositions.py` 91.19%.
- Ruff format and lint passed across `swos_prose`, benchmark, evaluation, tools
  and tests.
- `pip-audit` found no known vulnerabilities in `requirements-dev.lock`.
- Bandit found no medium/high issues in executable Python.
- schema validation (30 artefacts), Agent Skills lint (5 skills), governance (8
  artefacts), all eight evaluation planes, active 56-case benchmark validation,
  and the deterministic six-fixture repair contract passed.
- a clean editable-install replay passed locally on Python 3.14; hosted CI is the
  authoritative Python 3.11 replay.

### Exact-head hosted evidence

- SWOS CI #155 / run `32565431253`, SWOS Prose Benchmark #31 / run
  `32565431257`, SWOS Engineering Quality #4 / run `32565431261`, and SWOS
  CodeQL #4 / run `32565431304` all completed green for the exact head.
- The hosted Python 3.11 quality job measured 85.46% package coverage and passed
  every configured critical-module floor.
- The active `Protect main` ruleset is active and now requires the 18 deterministic
  status contexts, linear history and review-thread resolution. The stochastic
  live OpenAI job is intentionally absent from that required list.
- The live workflow completed as a non-gating success; its verifier substep had
  two expected-outcome failures (both `REVIEW`) and its five-case
  no-diagnostics dogfood reported 2 `NO_CHANGE_RECOMMENDED` and 3 `PASS`.

### Merge gate

PR #37 is ready for independent adversarial review at the exact head. Merge and
post-merge main CI remain outstanding; no v1.1 work may begin after this gate.

Live Luna/OpenAI verifier, dogfood and benchmark results remain stochastic
evidence and are not substitutes for deterministic merge gates.
