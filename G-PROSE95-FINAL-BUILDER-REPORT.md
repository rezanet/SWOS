# G-Prose95 Final Builder Report

Date: 2026-08-23
Repository: rezanet/SWOS  
Goal: **G1 — Complete SWOS Prose M1 and make PR #40 merge-ready**

## 1. Verdict

**GOAL ACHIEVED — READY FOR INDEPENDENT REVIEW.**

PR #40 is open, non-draft, and unmerged. The exact final code/evidence head is green locally and on hosted CI, the final exact-head hosted benchmark completed successfully, and the final adversarial review gate is pending only the independent review of this completed evidence package. No merge, release tag, v1.1 release, or out-of-scope platform work was performed.

The safety claims below are empirical observations on the governed benchmark commit identified in this report. They are not universal guarantees for arbitrary future prose or model behavior.

## 2. Exact repository and delivery identity

| Item | Exact value |
|---|---|
| Repository | https://github.com/rezanet/SWOS |
| Pull request | https://github.com/rezanet/SWOS/pull/40 |
| Working branch | codex/g-prose95 |
| Exact base/start commit | 2004efd5ac444e5eb639ac77e7eebcbabb6573a6 |
| Final code/evidence head | 317bf7e08944e62101528382214a6c147478997e |
| Final code fixes | a5808c76c56d0081eb20a9596b16ce982c740f0f — preserve unary context operators; 9d86ecb94d0e7726a30c9bb2dface72894176fcf — close wrapper and budget provenance gaps; 2b9b52a70b4ec563b98fe668cebd63fe6330f554 — guard Markdown link-label context claims; deb60c0db5e4899d21549e6daeb274546a2c8a75 — preserve punctuation inside closing context delimiters; 317bf7e08944e62101528382214a6c147478997e — harden context sentence boundaries, wrapper normalization, and image-label handling |
| Merge state | Open; not merged |
| Release/tag state | No release or tag created |
| Final report commit | Supplied in the final handoff; a Git commit cannot contain its own object ID |

All implementation commits in the governed range carry Signed-off-by trailers. The two pre-existing untracked M1 reports were not staged, modified, or included.

## 3. Delivered engine surface

The common rewrite → verify path now supports the existing polish mode plus:

- polish
- naturalise
- clarify
- tighten

The governed presets are scholarly-natural, precise-technical, plain-intelligent, elegant-essay, and executive. The canonical API is edit_text; the backward-compatible polish_text API now carries mode, preset, context, diagnostics, provider-call, token, cost, verifier, repair, and final-disposition provenance. The CLI, skill, README, benchmark runner, dogfood schema, and development documentation describe the same surface.

OpenAI rewrite and verifier adapters use structured response schemas and disable response storage. See the [OpenAI Responses API reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/output_item?lang=python).

## 4. Safety architecture and invariants

The M1 invariants remain enforced:

- repair is bounded to at most two attempts;
- repair is local-span only and mechanically confines all text outside the reviewed span;
- whole-text regeneration is not used as repair;
- eligibility requires exactly one token-level edit explainable by the reviewed modality, quantifier, attribution, negation, or causal lexical family;
- hard invariants bypass repair and remain REJECT;
- every repair attempt is re-verified;
- failed, uncertain, or unlocalised repair preserves the original safe source fallback and fails closed;
- repair provenance records attempt spans, before/after text, verifier judgment, provider-call state, tokens, cost, and failure reason.

G-Prose95 additionally enforces:

- context-before and context-after are explicitly untrusted read-only inputs;
- context-only claims must match a complete candidate sentence boundary rather than a substring;
- abbreviations, sentence-final initialisms, short sentences, Unicode terminators, terminal sentence force, case-sensitive identifiers, relational words, determiners, punctuation position, grouping symbols, internal decimal punctuation, and initialism position are preserved in context identity;
- recognized Markdown presentation prefixes are canonicalized only when followed by letter/quote content; numeric and operator-leading claims such as - 5 is positive. retain their unary sign;
- balanced Markdown emphasis, code, and strikethrough wrappers are canonicalized as presentation only; unbalanced or meaning-bearing operators remain visible;
- valid Markdown link destinations and image destinations are removed while comparing their visible labels; raw URLs outside link syntax remain meaning-bearing;
- the complete presentation surface is canonicalized before sentence splitting, including multi-sentence balanced wrappers, image alt labels, and conservative unlisted lowercase technical sentence starts;
- invalid, NUL-containing, or over-budget context exits before rewrite/verifier provider calls;
- context rejection is distinct from provider failure in CLI status and telemetry;
- diagnostics abstain only under reviewed conservative evidence and never silently license a semantic rewrite;
- mixed model-specific pricing is reported as unavailable rather than mispriced by one global rate.

## 5. Governed benchmark identity

The active benchmark is 0.4.0-g-prose95:

| Measure | Value |
|---|---:|
| Fixture count | 76 |
| Corpus SHA-256 | b0b27d3b801f781e436837db1ab5bb0af0861bf2e1c233a67cb51435e30aead1 |
| Equivalent fixtures | 38 |
| Material-change fixtures | 38 |
| Stability probes | 16, five draws each |
| New G-Prose95 fixtures | prose-057.json through prose-076.json (20 files) |

The mode/preset matrix is:

~~~
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

The frozen v0.2 evidence remains untouched:

- freeze marker: benchmark/FROZEN_AT = v0.2.0-rc1;
- 50 frozen cases;
- frozen corpus SHA-256: 7d0ac58a083435a175a3dd728917b1f663e95ae83e29299865a11cde421c59be;
- evidence source commit: 7637a487a93266e30fcbefbc40ad2266fec600b8;
- frozen workflow run: 32450085166;
- frozen artifact: 9435636550.

## 6. Final exact-head hosted benchmark

| Item | Exact value |
|---|---|
| Workflow run | 32601464301 — success |
| Exact head | 317bf7e08944e62101528382214a6c147478997e |
| Corpus contract job | 97100254397 — success |
| Live evidence job | 97100254468 — success |
| Artifact | swos-prose-g-prose95-benchmark, ID 9483196936 |
| Generated at | 2026-08-22T22:05:51.2116Z |
| Model | gpt-5.6-luna for rewrite, verifier, and repair identity |

### Semantic safety

| Measure | Result |
|---|---:|
| Unsafe semantic PASSes | 0 |
| Equivalent statuses | PASS 27, REJECT 7, REVIEW 4 |
| Material-change statuses | REJECT 25, REPAIR 13 |
| Safety gate | true |
| Verifier calls | 44 |
| Total latency | 300,034.669 ms |
| Average latency | 3,947.825 ms |
| Cost | Unavailable; no pricing rates configured |

For material-change probes, PASS is unsafe; REVIEW and REJECT are fail-closed. REPAIR is a governed disposition, not an unsafe PASS.

### Diagnostics and efficiency

- unsafe diagnostic abstentions: [];
- expectation mismatches: [];
- missing expected signals: [];
- reviewed abstentions: 3;
- baseline tokens without diagnostics: input 101,167 / output 17,454 / total 118,621;
- counterfactual tokens with diagnostics: input 98,694 / output 17,280 / total 115,974;
- tokens saved: input 2,473 / output 174 / total 2,647;
- total token savings: 2.231476719973698%;
- baseline calls: rewrite 76, verifier 17, repair 0, total 93;
- calls saved by diagnostics: rewrite 3, verifier 0, repair 0, total 3;
- counterfactual calls: rewrite 73, verifier 17, repair 0, total 90;
- efficiency latency: 218,718.974 ms total, 2,877.881 ms average;
- efficiency unsafe abstentions: 0;
- repair records: 76 not attempted, 0 provider calls, 2 source fallbacks, attempt distribution {"0": 76};
- output-token limits: rewrite 4,000 / repair 4,000 / verifier 6,000;
- cost estimates: unavailable, never represented as zero.

The hosted mode/preset status matrix was:

~~~
clarify::executive             1: PASS 1
clarify::plain-intelligent     4: PASS 4
clarify::scholarly-natural     2: PASS 2
naturalise::executive          2: PASS 1, REJECT 1
naturalise::plain-intelligent  1: PASS 1
naturalise::precise-technical  2: PASS 2
naturalise::scholarly-natural  2: PASS 2
polish::none                  56: PASS 56
tighten::elegant-essay         2: PASS 2
tighten::precise-technical     4: PASS 3, REVIEW 1
~~~

### Stability

- 16 probes × 5 draws = 80 verifier draws;
- unsafe stability PASSes: 0;
- verifier calls: 80;
- total latency: 463,103.000 ms;
- average latency: 5,788.787 ms;
- cost: unavailable;
- verifier model: gpt-5.6-luna.

Stability is an observed variance measure on the governed probes, not a universal guarantee.

## 7. M1 repair contract

The deterministic six-fixture M1 contract passed with no failures:

- repair-001 through repair-005: PASS, one bounded attempt and one provider call each, final source preserved after verified repair;
- repair-006: hard-invariant REJECT, zero attempts, zero provider calls, source fallback preserved;
- contract: swos-prose-m1-bounded-repair;
- fixture count: 6, positive 5, negative 1, passed: true.

This contract proves orchestration, localization, confinement, re-verification, provenance, and fail-closed fallback. It does not claim arbitrary stochastic model-repair success.

## 8. Final local validation

All substantive local gates passed on the final code head:

| Gate | Result |
|---|---|
| Prose unit/contract suite | 240 tests, 11 expected live skips, OK |
| Executable coverage | 86.04%; policy PASS |
| Critical repair floor | 82.14% (required 80%) |
| Critical pipeline floor | 91.30% (required 85%) |
| Critical causal-scope floor | 98.78% (required 90%) |
| Critical deterministic floor | 98.57% (required 90%) |
| Critical propositions floor | 91.19% (required 85%) |
| Active benchmark validation | 76 cases; zero unsafe abstentions |
| M1 repair contract | 6/6; no failures |
| Schema validation | 30 artefacts; OK |
| Agent Skills validation | 5 skills; OK |
| Governance validation | 8 artefacts; OK |
| Eight-plane evaluation harness | All eight PASS; release decision RELEASE |
| Ruff lint | Full scope passed |
| Scoped Ruff format | 3 scoped files already formatted |
| Strict pip-audit | No known vulnerabilities |
| Bandit | 0 medium/high issues; 8 low informational findings |

The Windows checkout-wide Ruff format check still reports 33 reformattable files because of the repository's existing CRLF/autocrlf behavior. No unrelated files were reformatted; hosted Linux Engineering Quality passed.

## 9. Hosted CI and adversarial review

Final exact-head hosted workflows:

| Workflow | Run / jobs | Result |
|---|---|---|
| SWOS CI | run 32601458575; DCO 97100237302; schema 97100237374; skills 97100237369; prose tests 97100237365; governance 97100237385; OpenAI live 97100237416; eval jobs 97100258985, 97100258965, 97100259010, 97100258993, 97100258971, 97100258934, 97100258953, 97100259007 | success |
| SWOS Engineering Quality | run 32601458470; quality 97100236891; SCA 97100237318; Bandit 97100237015 | success |
| SWOS CodeQL | run 32601458516; CodeQL job 97100237040; analysis check 97100322542 | success |
| PR Prose Benchmark | run 32601458448; contract 97100236762; live job 97100237447 skipped by design | success |
| Manual exact-head Prose Benchmark | run 32601464301; contract 97100254397; live evidence 97100254468 | success |

Adversarial review history:

- the initial review raised benchmark call-accounting, repair-provenance, and active-corpus-default findings; these were fixed and regression-tested;
- subsequent exact-tree reviews drove fixes for quoted sentence boundaries, rejected-context provider bypass, model identity/provenance, diagnostic policy scope, sentence/initialism boundaries, semantic symbols, relation words, determiners, punctuation and case, Unicode terminators, mixed-model cost accounting, Markdown presentation markers, and unary-sign preservation;
- the prior exact-head review was 5000491740, reviewing a5808c76c56d0081eb20a9596b16ce982c740f0f; its wrapper and output-budget findings were fixed in 9d86ecb;
- review 5000575291 then identified a Markdown link-label bypass and stale report evidence; the link-label bypass is fixed in 2b9b52a, and review 5001087978 identified a terminal-delimiter punctuation bypass that is fixed in deb60c0;
- review 5001140299 identified three additional context-boundary P1s — unlisted lowercase technical starts, wrapper normalization order, and image alt labels — fixed in 317bf7e with focused regressions;
- this report records the final hosted evidence from 317bf7e;
- the final exact-head Codex review and resolution of all remaining threads are the last PR governance actions before independent review.

## 10. Files changed from the exact base

The implementation/evidence diff from 2004efd5ac444e5eb639ac77e7eebcbabb6573a6 to the final code head contains 53 files, 2,862 insertions, and 161 deletions, excluding this report file:

~~~
.env.example
.github/workflows/swos-prose-benchmark.yml
.gitignore
Makefile
README.md
benchmark/README.md
benchmark/corpus/prose-057.json through benchmark/corpus/prose-076.json (20 files)
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

The report itself is a separate documentation change. The two pre-existing untracked files G1-M1-SELF-HEALING-ENGINE-FINAL-BUILDER-REPORT.md and M1-SELF-HEALING-ENGINE-BUILDER-REPORT.md were left untouched.

## 11. Deviations, unresolved items, and recommendation

Deviations and limitations:

1. Dollar pricing is unavailable because SWOS_PROSE_INPUT_USD_PER_1K and SWOS_PROSE_OUTPUT_USD_PER_1K were not configured. Token, latency, provider-call, and model-identity evidence remains available; missing pricing is fail-closed.
2. The hosted live benchmark is a manual, non-gating workflow by design. It completed successfully and its artifact is recorded above; PR-gating corpus validation remains separate.
3. The full Windows Ruff format check is affected by the existing CRLF/autocrlf working-tree behavior. Scoped changed-file formatting and hosted Linux quality are green.
4. The benchmark claims zero unsafe PASSes and zero unsafe abstentions only for the governed corpus SHA above, not universally.
5. The final report commit SHA is supplied in the handoff because the report cannot contain its own Git object ID.

Unresolved correctness/safety items: none observed in the final hosted evidence. The final exact-head Codex review and thread-resolution state remain to be recorded after this report is pushed; no merge action is authorized in this builder task.

**Recommendation: READY FOR INDEPENDENT REVIEW.** PR #40 is merge-ready for an independent reviewer. Stop here pending that review and the user's separate merge decision; do not merge or tag in this builder task.
