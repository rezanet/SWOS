# G-Prose95 Final Builder Report

Date: 2026-08-22  
Repository: rezanet/SWOS  
Goal: G-Prose95 — bring SWOS Prose from approximately 75% to approximately 95% full-engine completion

## 1. Verdict

**GOAL ACHIEVED — READY FOR INDEPENDENT REVIEW / PR #40 IS MERGE-READY.**

The implementation, deterministic validation, governed benchmark, hosted exact-head benchmark, CI, and final adversarial review are complete. PR #40 remains open and unmerged by instruction. No release tag was created and no out-of-scope v1.1/platform work was started.

This is an empirical milestone result, not a universal or 100% guarantee. Safety claims in this report are bounded to the governed benchmark corpus identified below and to the observed hosted run.

## 2. Exact repository and delivery identity

| Item | Exact value |
|---|---|
| Repository | https://github.com/rezanet/SWOS |
| Working branch | codex/g-prose95 |
| Exact base/start commit | 2004efd5ac444e5eb639ac77e7eebcbabb6573a6 |
| Main implementation commit | f77aad639bbf4b182937c436e7944ca836136967 |
| CI benchmark-workflow correction | a9a62be123397c73d19739ce4b52af7d81c7348c |
| Final adversarial-fix/evidence head | 567d5c7d9f60d22521d8a5b0d29422ee9d7393bd |
| Pull request | https://github.com/rezanet/SWOS/pull/40 |
| Merge state | Open; not merged by this goal |
| Release/tag state | No tag or release created |

All three G-Prose95 implementation commits are DCO-signed with git commit -s. The final report is a docs-only commit after the evidence head; its exact branch SHA is reported in the final handoff because a Git commit cannot contain its own object ID.

## 3. Delivered engine surface

The implementation adds three new writer modes through the common rewrite/verify path while preserving the existing polish mode:

- polish
- naturalise
- clarify
- tighten

The five governed presets are:

- scholarly-natural
- precise-technical
- plain-intelligent
- elegant-essay
- executive

The canonical API is edit_text; the existing polish_text API remains compatible and now accepts mode, preset, context, and provenance controls. The CLI exposes mode and preset selection, and dogfood output records mode, preset, context safety, token usage, cost availability, provider-call counts, verifier calls, repair attempts, and final disposition. The skill and README documentation describe the same governed surface.

OpenAI rewrite and verifier adapters use structured response schemas and explicitly disable response storage. The structured-output behavior is aligned with the official Responses API output-item reference: https://platform.openai.com/docs/api-reference/responses-streaming/response/output_item?lang=python

## 4. Safety architecture preserved and strengthened

The M1 safety invariants remain active:

- repair is bounded to at most two attempts;
- repair is local-span only, with mechanical confinement outside the reviewed span;
- whole-text regeneration is not used as repair;
- repair eligibility requires one token-level edit explainable by the reviewed modality, quantifier, attribution, negation, or causal lexical family;
- hard invariants bypass repair and remain REJECT;
- every repair attempt is re-verified;
- failed or uncertain repair preserves the original safe source fallback and fails closed;
- attempt provenance includes before/after span data, verifier judgment, provider-call state, tokens, cost, and failure reason.

G-Prose95 adds the following protections:

- context-before and context-after are explicitly untrusted and cannot authorize a new claim;
- context-only claims are recognized only when they match an exact normalized candidate sentence boundary, preventing the System/subsystem substring false positive;
- invalid, NUL-containing, empty, or over-budget context returns without an unplanned rewrite call;
- context-only changes are forced to REVIEW and are represented as CONTEXT_ONLY_CLAIM deltas;
- diagnostics are conservative and fail closed: they can abstain only under reviewed evidence and never silently license a semantic rewrite.

## 5. Governed benchmark identity and deterministic results

The active benchmark is 0.4.0-g-prose95 with 76 fixtures. Its canonical corpus SHA-256 is:

~~~text
b0b27d3b801f781e436837db1ab5bb0af0861bf2e1c233a67cb51435e30aead1
~~~

Corpus composition:

- 38 semantically equivalent fixtures;
- 38 material-change fixtures;
- 16 stability probes, each run five times in the hosted --mode all campaign;
- 20 new G-Prose95 fixtures, prose-057.json through prose-076.json;
- mode/preset matrix: polish::none 56, clarify 7, naturalise 7, and tighten 6 fixtures across the five presets.

The local active-corpus validation on the final evidence head reported:

- 76/76 fixtures loaded;
- zero unsafe diagnostic abstentions;
- zero expectation mismatches;
- three reviewed abstentions, all governed and fail-closed.

The frozen v0.2 evidence was not rewritten. benchmark/FROZEN_AT remains the v0.2.0-rc1 freeze with 50 cases, corpus SHA-256 7d0ac58a083435a175a3dd728917b1f663e95ae83e29299865a11cde421c59be, evidence source commit 7637a487a93266e30fcbefbc40ad2266fec600b8, workflow run 32450085166, and artifact 9435636550.

## 6. Final exact-head hosted benchmark

Final hosted campaign:

- workflow run: 32570178134;
- exact head: 567d5c7d9f60d22521d8a5b0d29422ee9d7393bd;
- contract job: 97024439568 — success;
- live benchmark job: 97024439498 — success;
- evidence artifact: swos-prose-g-prose95-benchmark, artifact ID 9475303328;
- generated report timestamp: 2026-08-22T11:24:21Z;
- benchmark version: 0.4.0-g-prose95.

Final semantic-safety result:

| Measure | Result |
|---|---:|
| Unsafe semantic PASSes | 0 |
| Equivalent fixture statuses | PASS 31, REJECT 7 |
| Material-change fixture statuses | REJECT 25, REPAIR 13 |
| Verifier calls | 44 |
| Total semantic-safety latency | 291,743.969 ms |
| Average semantic-safety latency | 3,838.736 ms |

REPAIR is retained as a governed final disposition for material-change probes; it is not counted as an unsafe PASS. The safety gate passed.

Final diagnostics and efficiency result:

- unsafe diagnostic abstentions: 0;
- expectation mismatches: 0;
- reviewed abstentions: 3;
- baseline tokens without diagnostics: 122,617;
- counterfactual tokens with exact diagnostics skips: 116,726;
- observed/counterfactual tokens saved: 5,891 (4.80439090827536%);
- baseline provider calls: 94 (rewrite 76, verifier 18, repair 0);
- counterfactual provider calls: 90, with 4 calls saved by diagnostics;
- efficiency latency: 245,268.181 ms total, 3,227.213 ms average;
- unsafe abstentions in efficiency evidence: 0.

The final efficiency record retained the complete repair distribution: 76 records, zero repair attempts, zero repair provider calls, two source fallbacks, and an attempt-count distribution of {"0": 76}. This is an observed result for the diagnostics-disabled active corpus, not a claim that the repair path is untested; the deterministic M1 repair contract below exercises the bounded repair orchestration directly.

Final stability result:

- 16 probes × 5 draws = 80 verifier draws;
- unsafe stability PASSes: 0;
- verifier calls: 80;
- total stability latency: 518,398.488 ms;
- average stability latency: 6,479.981 ms;
- repeated-verifier overhead: 80 draws / 80 verifier calls.

## 7. Repair contract and adversarial regressions

The final local deterministic repair contract used six fixtures:

- repair-001 through repair-005: PASS, one bounded repair attempt and one provider call each;
- repair-006: hard-invariant REJECT, zero repair attempts, zero repair provider calls, source fallback preserved.

The contract passed with no failures. Its own note correctly limits the claim to deterministic orchestration, localization, and confinement; it does not claim arbitrary stochastic model repair success.

The adversarial regression suite covers:

- unrelated proposition changes combined with each reviewed lexical family, all barred from local repair;
- modality, quantifier, attribution, negation, and causal-family eligibility;
- hard-invariant number changes;
- context-only claim introduction and exact sentence-boundary matching;
- invalid context returning with rewrite_call_count == 0;
- repair outcome, fallback, attempt-count, and provider-call distributions in benchmark records.

## 8. Local validation evidence

All substantive local gates passed on the final evidence head 567d5c7:

| Gate | Result |
|---|---|
| Prose unit/contract tests | 205 tests, 11 expected live skips, OK |
| Schema validation | 30 artefacts, OK |
| Agent Skills validation | 5 skills, OK |
| Governance validation | 8 artefacts, six mechanised controls, OK |
| Eight-plane evaluation harness | retrieval, grounding, citation, scholarly, governance, regression, memory-contamination, adversarial — all PASS; release decision RELEASE |
| Active benchmark validation | 76 cases, no unsafe abstentions or mismatches |
| Deterministic repair contract | 6/6 contract cases, no failures |
| Scoped Ruff format check | All five changed review-fix files already formatted |
| Ruff lint | All checks passed |
| Coverage | 85.48% executable swos_prose scope; policy PASS |
| Critical repair floor | 82.14% (required 80%) |
| Critical pipeline floor | 88.54% (required 85%) |
| Critical causal floor | 98.78% (required 90%) |
| Critical deterministic floor | 98.57% (required 90%) |
| Critical propositions floor | 91.19% (required 85%) |
| pip-audit | No known vulnerabilities |
| Bandit | 0 medium/high; 8 low informational findings |

The Windows checkout-wide Ruff format check reports 33 files as reformattable because of the repository's existing CRLF/autocrlf working-tree behavior. The changed files pass explicit format checks, the hosted Linux engineering-quality job passed, and no unrelated files were reformatted.

## 9. Hosted CI and review provenance

The exact evidence head passed the hosted checks below:

| Workflow run | Result and job evidence |
|---|---|
| SWOS CI 32569981255 | success; schema 97023976713, skills 97023976725, prose tests 97023976757, governance 97023976640, DCO 97023976706, OpenAI live evidence 97023976689, eight evaluation jobs 97023995859, 97023995871, 97023995875, 97023995884, 97023995886, 97023995892, 97023995925, 97023996019 |
| SWOS Engineering Quality 32569981256 | success; quality baseline 97023976758, SCA 97023976721, Bandit 97023976641 |
| SWOS CodeQL 32569981257 | success; CodeQL job 97023976486 |
| PR benchmark contract 32569981258 | success; contract job 97023976626; live job intentionally skipped on pull requests |
| Final manual G-Prose95 benchmark 32570178134 | success; contract 97024439568, live evidence 97024439498, artifact 9475303328 |

The exact-head OpenAI live-evidence job 97023976689 passed live verifier regressions (11 tests, OK) and a five-case strict dogfood batch (5 samples: NO_CHANGE_RECOMMENDED 4, PASS 1), with five JSON evidence files uploaded. The hosted live benchmark used gpt-5.6-luna for rewrite and verification.

Codex adversarial review:

- initial review on a9a62be raised three P2 findings;
- all three were fixed in 567d5c7 with regression tests and benchmark provenance changes;
- replies were posted as review comments 3835888724, 3835888768, and 3835888783;
- fresh exact-head Codex review 5000014379 reviewed 567d5c7d9f60d22521d8a5b0d29422ee9d7393bd and returned no suggestions;
- original review threads PRRT_kwDOT9f0pM6bYSyI, PRRT_kwDOT9f0pM6bYSyM, and PRRT_kwDOT9f0pM6bYSyP are resolved.

## 10. Cost and performance accounting

Cost accounting is implemented and reported fail-closed. The final benchmark correctly reports cost as unavailable because SWOS_PROSE_INPUT_USD_PER_1K and SWOS_PROSE_OUTPUT_USD_PER_1K were not configured. Missing pricing is never represented as zero and no secret or pricing credential was stored in the repository, logs, or report.

Observed performance on the final hosted campaign was:

- semantic safety: 44 verifier calls, 291,743.969 ms total, 3,838.736 ms average;
- diagnostics-disabled efficiency: 94 baseline calls, 245,268.181 ms total, 3,227.213 ms average;
- stability: 80 verifier calls, 518,398.488 ms total, 6,479.981 ms average.

The complete per-mode/per-preset accounting is retained in the uploaded benchmark JSON. The governed fixture matrix is:

~~~text
clarify::executive=1
clarify::plain-intelligent=4
clarify::scholarly-natural=2
naturalise::executive=2
naturalise::plain-intelligent=1
naturalise::precise-technical=2
naturalise::scholarly-natural=2
polish::none=56
tighten::elegant-essay=2
tighten::precise-technical=4
~~~

## 11. Files changed from the exact base

The implementation/evidence diff from 2004efd5ac444e5eb639ac77e7eebcbabb6573a6 contains 53 files and 2,102 insertions / 159 deletions:

~~~text
.env.example
.github/workflows/swos-prose-benchmark.yml
.gitignore
Makefile
README.md
benchmark/README.md
benchmark/corpus/prose-057.json through benchmark/corpus/prose-076.json
benchmark/fixture_schema.json
benchmark/runner.py
docs/DEVELOPMENT.md
docs/G-PROSE95-SPEC.md
pyproject.toml
skills/swos-prose/SKILL.md
swos_prose/__init__.py
swos_prose/cli.py
swos_prose/context.py
swos_prose/cost.py
swos_prose/diagnostics.py
swos_prose/dogfood.py
swos_prose/models.py
swos_prose/modes.py
swos_prose/pipeline.py
swos_prose/providers/openai_responses.py
swos_prose/providers/openai_rewrite.py
swos_prose/repair.py
swos_prose/rewrite.py
tasks/plan.md
tasks/todo.md
tests/prose/test_benchmark_contract.py
tests/prose/test_cli_polish.py
tests/prose/test_g_prose95_contract.py
tests/prose/test_openai_provider.py
tests/prose/test_polish_pipeline.py
tests/prose/test_repair.py
~~~

The prose-057.json through prose-076.json entry represents 20 individual tracked fixture files. The two pre-existing untracked M1 builder reports in the working tree were not staged, modified, or included in this goal's diff.

## 12. Deviations, inherited history, risks, and remaining gap

Deviations and limitations:

1. Pricing rates were intentionally absent, so dollar costs are unavailable while token counts and call counts remain measured.
2. The manual hosted benchmark is a non-gating workflow by design; it completed successfully and its artifact is recorded above.
3. Local full-worktree Ruff format output is affected by Windows CRLF/autocrlf behavior. Hosted Linux CI is green, and unrelated files were left untouched.
4. Historical repository governance records include the earlier M1 squash-merge DCO accounting discrepancy (32563838579) and a prior docs PR #38 escaped-newline DCO issue. Those inherited records were not changed by G-Prose95; the exact G-Prose95 head passed its own DCO job.
5. The branch remains unmerged and untagged so an independent reviewer retains the merge decision.

Risks and remaining gap:

- Hosted model behavior is stochastic and can drift with model/provider changes; five-draw stability evidence bounds observed variance but is not a universal guarantee.
- The benchmark demonstrates zero unsafe PASSes and zero unsafe abstentions on the frozen active corpus, not on arbitrary future prose.
- The target is an empirical full-engine completion milestone, not a claim that prose quality can be reduced to a universal percentage.
- Independent review should inspect the exact final branch head and the uploaded final benchmark artifact before merge.

## 13. Recommendation

**READY FOR INDEPENDENT REVIEW.** The code/evidence head is green, the exact-head hosted benchmark is successful, the three adversarial P2 findings are fixed and resolved after clean re-review, and PR #40 is merge-ready. Stop here pending independent review and the user's merge decision.
