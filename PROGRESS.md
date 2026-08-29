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
- implementation/evidence head before this final ledger-only follow-up:
  `ff1ec102c7f128d4e10bfde7b823627680b6fea0`
- commits: `ff2605bf69eae7e857c32016cadcf2d50f4b290a` (Ruff formatting baseline),
  `fa8612dd2ddfacb9156c644489fe1db124db0311` (quality substrate),
  `3ba1e92268dc23f0f3f308caa19f9c591720d122` (progress ledger),
  `fea3ba7d9f3b2258e9df09c658aaf8d01a0e47d6` (quiet coverage-policy tests),
  `c5602251e206b25b0cb2909563469141df8ee57c` and
  `ff1ec102c7f128d4e10bfde7b823627680b6fea0` (ledger-only evidence corrections),
  and final PR head `240045b145a8ac8b8bb6809931b417a7923bc912` (documentation-only
  distinction between implementation/evidence and final ledger heads)
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

- SWOS CI #156 / run `32565677709`, SWOS Prose Benchmark #32 / run
  `32565677699`, SWOS Engineering Quality #5 / run `32565677696`, and SWOS
  CodeQL #5 / run `32565677682` all completed green for the exact implementation
  and evidence head above.
- The final PR head `240045b145a8ac8b8bb6809931b417a7923bc912` also completed
  green on SWOS CI #157 / run `32565827013`, SWOS Prose Benchmark #33 / run
  `32565827006`, SWOS Engineering Quality #6 / run `32565827022`, and SWOS
  CodeQL #6 / run `32565827025`.
- The hosted Python 3.11 quality job measured 85.46% package coverage and passed
  every configured critical-module floor.
- The active `Protect main` ruleset is active and now requires the 18 deterministic
  status contexts, linear history and review-thread resolution. The stochastic
  live OpenAI job is intentionally absent from that required list.
- The live workflow completed as a non-gating success; its verifier substep had
  two expected-outcome failures (both `REVIEW`) and its five-case
  no-diagnostics dogfood reported 2 `NO_CHANGE_RECOMMENDED` and 3 `PASS`.

### Verified merge gate

- PR #37 was squash-merged from expected final head
  `240045b145a8ac8b8bb6809931b417a7923bc912` as main merge SHA
  `15919f373bbee50fb05b87ed5be8980c66f734d6`.
- Post-merge main SWOS CI #158 / run `32565943168`, Engineering Quality #7 /
  run `32565943304`, CodeQL #7 / run `32565943190`, and the dependency-graph
  update run `32565945667` all completed successfully. SWOS CI included the
  DCO, semantic-delta, schema, governance, eight evaluation-plane, and live
  evidence jobs; the hosted quality run included Ruff, 186 deterministic tests,
  85.46% coverage, SCA, and Bandit.
- The active `Protect main` ruleset therefore enforced all 18 deterministic
  contexts on the G2 merge. This ledger update changes documentation only; it
  does not change source, workflow, or required-check configuration.
- Documentation-only PR #38 subsequently produced historical SWOS CI run
  `32566386846`: every semantic, schema, governance, evaluation-plane and live
  job passed, while DCO correctly rejected the GitHub-generated squash commit
  `1a2a0b1e907072722d037fd7657059f0dae05292` because its message contained a
  literal escaped `\n\nSigned-off-by` sequence rather than a standalone trailer.
  This is recorded as a historical DCO deviation, alongside the earlier M1
  squash deviation; the signed follow-up is a process guard, not a retroactive
  history repair, and `main` is not rewritten.

No v1.1 reranker/reference-runtime work may begin after this gate.

Live Luna/OpenAI verifier, dogfood and benchmark results remain stochastic
evidence and are not substitutes for deterministic merge gates.
## SWOS 100% Completion Progress (Programme Baseline)

**Programme baseline:** 2026-08-22
**Baseline main SHA:** `eb704e4baec57124a6d54065ff99ea3d5128c35c`
**Baseline report:** [`BASELINE_REPORT.md`](BASELINE_REPORT.md)
**Historical programme branch:** `programme/swos-100-completion-baseline`
**Current programme branch:** `main`
**Last reconciled:** 2026-08-23
**Current reconciled main SHA:** `e79dbd3185703defa6bdba7fe2511ce3f260c9a8`

> This file tracks progress against SWOS as defined by its contracts, issues, source and authoritative roadmap. Percentages are planning estimates, not quality scores or release claims.

## Programme Status

| Milestone | SWOS-native interpretation | Status | Evidence / blockers |
|---|---|---|---|
| 0 | Repository Discovery and Baseline | **COMPLETE** | `BASELINE_REPORT.md`; repo/issues/PRs/architecture/CI inspected |
| 1 | Environment, CI and Quality Baseline | **COMPLETE** | PR #37 merged as `15919f373bbee50fb05b87ed5be8980c66f734d6`; reproducible lock, Ruff, >=80% executable coverage floor, critical-module floors, pip-audit, Bandit, CodeQL, required checks/ruleset, existing governance and eight-plane gates preserved |
| 2 | Core Reference Implementation / roadmap v1.1 | NOT STARTED | Cross-encoder reranker remains the first implementation target, followed by orchestrator/state store, EPG/SDL/RPM stores, corpus adapters, end-to-end CLI and SUT-bound harness |
| 3 | Host/User Interaction Layer | NOT STARTED | Complete specified host adapters/operator UX only when the reference runtime exists; no fictional browser frontend unless requirements introduce one |
| 4 | Feature Completion and Semantic Hardening | **IN PROGRESS** | SWOS Prose M1 and G-Prose95 landed; remaining open semantic issues include #4, #5, #6, #7, #12, #13, #14, #16 and verifier-stability issue #32 |
| 5 | Security Hardening | **IN PROGRESS** | Engineering substrate now includes SCA/SAST/CodeQL and repository protections; runtime egress, store integrity, memory poisoning, malformed-tool and production-surface controls remain future work |
| 6 | Performance, Cost and Scalability | **IN PROGRESS** | G-Prose95 records provider calls, tokens, latency and fail-closed cost availability; retrieval/reranking, state-store, provenance-growth, throughput and concurrency performance remain unimplemented |
| 7 | Testing and Quality Gates | **IN PROGRESS** | SWOS Prose executable coverage is above the 80% floor with higher critical-module floors; eight evaluation planes, benchmark contracts, SCA/SAST and deterministic Prose tests are enforced. Whole-system/SUT, mutation and broader runtime coverage remain future work |
| 8 | Documentation, Distribution and Deployment | **IN PROGRESS** | Portable SWOS Prose skill, CLI, package metadata, development docs and governed benchmark documentation exist; full reference-runtime operator/deployment docs wait on v1.1 implementation |
| 9 | Final Integration and Release | NOT STARTED | No v1.1/v2/v3 final release; exact final scope, SDL approval, release notes and verified tag remain future gates |

## Current Repository Release State

### Platform

- `VERSION`: **1.0.0** — Specification Lock.
- Contracts/schemas/governance/evaluation/portability foundation: released.
- v1.1 Reference Implementation: not yet implemented.
- v2 Research Grade: future roadmap.
- v3 Product Grade: future roadmap.

### SWOS Prose

- Last formally released package surface: **0.2.0**.
- Current development package on `main`: **0.4.0-dev**.
- Frozen governed v0.2 benchmark: 50 cases; immutable release evidence remains preserved.
- Active governed G-Prose95 benchmark: **0.4.0-g-prose95**, 76 cases (38 equivalent / 38 material-change), 16 stability probes.
- G-Prose95 final governed live evidence recorded zero unsafe semantic PASS outcomes and zero unsafe diagnostic abstentions on its exact benchmark campaign.
- No new release tag was created for G-Prose95; development identity, benchmark identity and platform version remain distinct.

## Completed Delivery Gates Since Baseline

### M1 — Self-Healing Engine

PR **#36 — M1: Self-Healing Engine (Repair Loop)** is **MERGED**.

- final PR head: `75cd3db94946a9928961c3e62a13971b78972ac1`;
- merge SHA: `010de54ebcd0ec3dba98f75d71ec3a503d02a98b`;
- active M1 benchmark identity: `0.3.0-m1`, 56 cases;
- bounded lexical repair families: modality, quantifier, attribution, negation and causal-strength drift;
- maximum two repair attempts;
- local-span confinement and full re-verification preserved;
- hard invariants bypass repair;
- provider provenance and repair token accounting retained;
- frozen v0.2 evidence unchanged.

### Contributor workflow

PR **#17 — contributor issue / PR templates** is **MERGED**.

- final PR head: `bc7a036b2822a329139695509d38f46ad716cb47`;
- merge SHA: `ff0b4d52048b6e07b23fb1a33c064b47ee174b95`.

### G2 — Engineering Substrate and CI Quality Baseline

PR **#37** is **MERGED**.

- final PR head: `240045b145a8ac8b8bb6809931b417a7923bc912`;
- merge SHA: `15919f373bbee50fb05b87ed5be8980c66f734d6`;
- exact developer/CI dependency lock;
- Ruff format/lint gates;
- executable-Python coverage floor >=80% plus higher critical-module floors;
- pip-audit SCA;
- Bandit Python SAST;
- CodeQL;
- active benchmark contract on pull requests;
- `Protect main` ruleset with deterministic required contexts, linear history and review-thread resolution;
- schema, Agent Skills, governance, DCO and all eight evaluation planes preserved.

PR #38 recorded the verified G2 merge; PR #39 hardened the governed squash/DCO checklist and records the historical unsigned-commit deviation without rewriting history.

### G-Prose95 — Full SWOS Prose Engine Surface

PR **#40 — G-Prose95: Complete SWOS Prose full-engine surface** is **MERGED**.

- final implementation/evidence head: `317bf7e08944e62101528382214a6c147478997e`;
- final PR head after report-only commits: `e0f4651733b0d196ec24215e6e6d7f52c17c5072`;
- squash merge/main SHA: `e79dbd3185703defa6bdba7fe2511ce3f260c9a8`;
- merge commit contains a standalone DCO `Signed-off-by:` trailer;
- implemented modes: `polish`, `naturalise`, `clarify`, `tighten`;
- implemented presets: `scholarly-natural`, `precise-technical`, `plain-intelligent`, `elegant-essay`, `executive`;
- all modes share the same deterministic verification, independent semantic-verifier, bounded repair and fail-closed source-fallback path;
- read-only surrounding context is explicitly untrusted and context-only claims are deterministically guarded;
- diagnostics abstain only on reviewed positive evidence;
- active benchmark expanded to 76 governed cases under `0.4.0-g-prose95`;
- exact live campaign: zero unsafe material-change PASS outcomes and zero unsafe diagnostic abstentions;
- final deterministic suite: 240 tests with 11 expected live skips on the final implementation head;
- executable SWOS Prose coverage on hosted Linux: approximately 86%, with all critical floors passing;
- Ruff, pip-audit, Bandit, CodeQL, schema, skills, governance and all eight evaluation planes passed in the governed PR evidence;
- all 44 PR review threads were resolved;
- final additional Codex bot review was unavailable because the external Codex review quota was exhausted; independent ChatGPT review found no remaining P0/P1/P2 blocker before merge;
- no release/tag, v1.1 implementation or unrelated platform work was included.

## Open Work Inventory

### Open semantic / Prose issues

- [ ] #4 lexical negation beyond explicit `not`/`never`
- [ ] #5 attribution-force drift
- [ ] #6 quantifier binding and modal scope
- [ ] #7 relational direction and causal-role reversal
- [ ] #12 causal explanations added during polish
- [ ] #13 referential hallucination from read-only context
- [ ] #14 qualification deletion during compression
- [ ] #16 citation attachment broadening during reordering
- [ ] #32 semantic-verifier stability on equivalent paraphrases

These issues remain explicit hardening work. G-Prose95 does not silently close them merely because its governed benchmark passed.

### Open pull-request carry-over from baseline

- [x] #17 contributor issue / PR templates — merged
- [x] #36 M1 Self-Healing Engine — merged
- [x] #37 Engineering Substrate and CI Quality Baseline — merged
- [x] #40 G-Prose95 full-engine surface — merged

### v1.1 Reference Implementation — next major dependency

- [ ] **Cross-encoder reranker reference implementation — first**
- [ ] Reference orchestrator
- [ ] Scholarly state store
- [ ] EPG store with hash chaining
- [ ] SDL store with hash chaining
- [ ] RPM store with governed writes / hash chaining
- [ ] Open scholarly-index corpus adapters
- [ ] End-to-end SWOS CLI
- [ ] Eight-plane harness bound to a real system under test

### v2 Research Grade

- [ ] RPM in production across projects
- [ ] Formalised discipline ontologies
- [ ] Trained citation-support classifier
- [ ] Measured source-diversity controls
- [ ] Discipline-specific method-critique depth
- [ ] Full PROV round-trip certification
- [ ] Image/object-analysis tool
- [ ] Governed promotion of art history / art criticism to agents where justified
- [ ] Multimodal scholarly reasoning

### v3 Product Grade

- [ ] Enterprise identity
- [ ] RBAC / ABAC
- [ ] Tenant isolation
- [ ] Observability dashboards
- [ ] Drift monitoring
- [ ] Incident workflow automation
- [ ] Compliance reporting
- [ ] Cost controls
- [ ] Service management

## Quality Baseline — Reconciled 2026-08-23

| Gate / metric | Current state |
|---|---|
| Frozen schema validation | **Enforced** |
| Agent Skills six-field lint | **Enforced** |
| Governance policy validation | **Enforced** |
| Eight-plane evaluation harness | **Enforced** |
| SWOS Prose unit/adversarial suite | **Enforced** |
| SWOS Prose package/CLI smoke test | **Enforced** |
| Live OpenAI evidence | Present and deliberately non-gating except unsafe/contract regressions |
| DCO | **Enforced**; governed merge checklist hardened |
| General Python lint/format | **Established — Ruff** |
| Numeric executable-Python coverage | **Established — >=80% total floor plus critical-module floors** |
| Dependency vulnerability scan | **Established — pip-audit** |
| Python SAST | **Established — Bandit** |
| Repository SAST | **Established — CodeQL** |
| Secret scanning / push protection | Repository-managed protection documented under G2 |
| Required GitHub checks | **Established under Protect main ruleset** |
| Active Prose benchmark contract | **76-case G-Prose95 contract** |
| Frozen v0.2 evidence | **Immutable and retained** |

## Programme Gate

Milestone 0 and the Engineering Substrate/CI baseline are complete. SWOS Prose has reached the governed G-Prose95 full-engine development surface and is no longer the principal implementation dependency.

**Next major implementation goal:** roadmap v1.1 retrieval, beginning with the cross-encoder reranker reference implementation. Do not skip directly to the orchestrator or v2/v3 product work before the retrieval/reranking reference path is implemented and evaluated.

## Project Completion Estimate

The original **~35%** estimate was a baseline planning estimate taken before M1, G2 and G-Prose95 landed. It is now stale and is intentionally **not replaced by an invented percentage**.

The next programme goal should establish a component-weighted completion ledger tied to acceptance tests for v1.1, v2 and v3. Until that exists, use milestone status and evidence rather than a single percentage as the authoritative progress indicator.
