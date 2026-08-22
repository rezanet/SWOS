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
- current branch head: `fa8612dd2ddfacb9156c644489fe1db124db0311`
- commits: `ff2605bf69eae7e857c32016cadcf2d50f4b290a` (Ruff formatting baseline),
  `fa8612dd2ddfacb9156c644489fe1db124db0311` (quality substrate)
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

### Hosted evidence pending at this ledger revision

- PR #37 exact-head SWOS CI, Engineering Quality, CodeQL and benchmark runs are
  required before merge.
- the `Protect main` ruleset currently enforces deletion protection, non-fast-forward
  protection, linear history and review-thread resolution; required status checks
  still need to be verified/updated against the new exact job contexts.

Live Luna/OpenAI verifier, dogfood and benchmark results remain stochastic
evidence and are not substitutes for deterministic merge gates.
