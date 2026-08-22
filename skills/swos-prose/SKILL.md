---
name: swos-prose
description: Semantic-safe prose polishing for text whose meaning is already settled. Use when asked to polish, edit, clarify, tighten wording, reduce repetition, improve sentence construction, or make academic, technical, explanatory, or enterprise prose read more naturally without changing its factual claims, attribution, uncertainty, modality, degree, causality, numbers, citations, quotations, chronology, conditions, or normative force. Runs conservative pre-generation diagnostics, one rewrite proposal when needed, independent semantic verification, and bounded local repair for a reviewed set of lexical semantic drifts; unsafe or uncertain outputs fall back to the source.
license: MIT
compatibility: Requires the installable SWOS Prose Python package (`pip install -e .` from the SWOS repo root). Changed prose needs a rewrite provider and an independent semantic verifier; bundled OpenAI Responses adapters require an API key. Exact reviewed diagnostics exemplars can abstain locally with zero provider calls. No host-specific runtime is required.
metadata:
  version: 0.4.0-dev
  swos_component: prose
  spec: agent-skills
  benchmark: benchmark/baseline.json
allowed-tools: []
---

# SWOS Prose

Rewrite the language. Preserve the meaning.

SWOS Prose is a **post-draft semantic-safe editing layer**. Use it only after the
claims, evidence, citations and argument are already settled. Its job is to improve
wording without silently changing what the author committed to.

## Installation

The portable skill metadata and executable Python engine are separate. Copying
this `SKILL.md` does not install the engine. From the SWOS repository root:

```bash
python3 -m pip install -e .
```

## Development surface: G-Prose95 / Full Engine

The implemented modes are `polish`, `naturalise`, `clarify` and `tighten`. Five
explicit register presets are available: `scholarly-natural`, `precise-technical`,
`plain-intelligent`, `elegant-essay` and `executive`. All modes use the same
semantic-safe pipeline. **Bounded local repair** remains a salvage operation after
verification identifies a reviewed, high-confidence lexical drift; it is never
repeated whole-text generation. Supported assurance levels remain `standard`,
`strict` and `review`; prefer `strict` for force-sensitive prose.

## Safety contract

A writer mode may improve sentence construction, local flow, concision, unnecessary
repetition, natural readability, wording and syntax. It must preserve every
material proposition; attribution; uncertainty and epistemic status; modality;
degree and scalar force; negation; causal force; scope and quantifiers;
chronology, conditions and exceptions; normative stance; and protected numbers,
citations and quotations.

Never add facts, evidence, examples, citations, explanations or conclusions.
Never resolve ambiguity by guessing. Never strengthen association into causation,
possibility into certainty, or a qualified statement into an unqualified one.

## Execution order

1. **Diagnose before generation.** The narrow reviewed fast path may return
   `NO_CHANGE_RECOMMENDED` with zero provider calls.
2. **Generate once when needed.** The rewrite provider proposes wording; it does
   not approve its own work.
3. **Verify independently.** Changed text is checked by deterministic semantic
   deltas and, when required, an independent semantic verifier.
4. **Repair only a bounded local defect.** The M1 loop can repair modality, quantifier,
   attribution, negation or causal-strength drift only when the offending region
   is localised at >=95% confidence. Numbers, citations, quotations, structural
   scope changes and proposition additions/removals are not repairable. At most
   two repair attempts are permitted.
5. **Mechanically confine and re-verify.** A proposal is rejected before semantic
   verification if any text outside the authorised span changes. A repaired
   candidate is released only if the ordinary verifier path returns `PASS`.
6. **Fail closed.** `REPAIR`, `REVIEW`, `REJECT`, malformed output or provider
   failure preserves the original source unless repair subsequently earns PASS.

The repair loop never turns uncertainty into permission. If localisation is
ambiguous, the defect is structural, or re-verification remains non-PASS, the
source is preserved.

## Interpret the result

| Outcome | Meaning | Action |
|---|---|---|
| `NO_CHANGE_RECOMMENDED` | Source returned unchanged; no rewrite needed | Keep source |
| `PASS` | Candidate, including any bounded repair, passed current safety gates | May use automatically |
| `REPAIR` | A bounded lexical defect is identified but not yet safely salvaged | Do not release |
| `REVIEW` | Equivalence unresolved or warning remains | Keep source; human review if needed |
| `REJECT` | Blocking semantic delta detected | Keep source |
| provider failure | Generation, repair or verification failed safely | Keep source |

Do not reinterpret `REPAIR` or `REVIEW` as soft PASS.

## Boundaries

SWOS Prose does not establish whether the source itself is true, well-cited or
well-researched. Do not use this surface to invent or repair missing facts, change
an author's position, translate, perform free creative rewriting, repair changed
protected numbers/citations/quotations, or structurally reconstruct missing
scopes or propositions.

Verifier stability is reported as a distribution in the active G-Prose95 benchmark;
safe uncertainty remains `REVIEW`/`REJECT` instead of being coerced into PASS.

## Governed benchmark evidence

The frozen v0.2 release benchmark remains
[`benchmark/baseline.json`](../../benchmark/baseline.json). It is immutable release
provenance and is **not rewritten by M1**. On that specific governed 50-case v0.2
benchmark, 22 labelled material-change probes produced 0 unsafe PASS outcomes,
diagnostics produced 0 unsafe abstentions, the exact reviewed fast path abstained
on 3/50 cases, measured token savings were 3.04%, and 11 stability probes repeated
five times produced 0 unsafe PASS outcomes.

The active G-Prose95 corpus contains 76 cases covering all modes, all five presets,
equivalent and material-change probes, context traps, and 16 stability probes.
The six M1 repair fixtures remain governed. The deterministic repair contract
proves localisation, confinement and state transitions; stochastic model repair
quality must be reported separately.
Benchmark observations are not universal guarantees.

Live benchmark reports also record provider calls, latency and optional cost
estimates. Cost remains unavailable unless both explicit USD-per-1K-token rates
are configured, and pricing telemetry never changes a safety outcome.

## CLI

Plain `swos-prose polish` prints only `final_text`; use `--mode`, `--preset`, and
`--json` for the selected policy, diagnostics, verification, repair provenance,
and token/cost records.

```bash
export OPENAI_API_KEY=...
swos-prose polish --mode naturalise --preset scholarly-natural \
  --source "The analysis was performed using a t-test." --assurance strict --json
```

Use `--skip-diagnostics` only for semantic-calibration runs that must force the
provider/verifier path.

## Library API

```python
from swos_prose import polish_text
from swos_prose.providers.openai_rewrite import OpenAIResponsesRewriteProvider
from swos_prose.providers.openai_responses import OpenAIResponsesSemanticVerifierProvider

result = polish_text(
    source="The revised workflow reduced implementation errors and simplified later review.",
    rewrite_provider=OpenAIResponsesRewriteProvider(),
    verifier_provider=OpenAIResponsesSemanticVerifierProvider(),
    assurance="strict",
)
print(result.final_text)
print(result.verification_status)
print(result.repair_success)
print(result.repair_attempts)
```

Each serialized repair attempt includes additive `provider_notes` provenance
from the repair invocation (when supplied), including provider/model, prompt
version, input hash and response ID metadata.

Consumers should use `final_text`, not raw `candidate`, unless deliberately
building a review interface. `verify_rewrite` remains a verification primitive;
the higher-level polish pipeline owns bounded repair.

## Resources

- [`benchmark/baseline.json`](../../benchmark/baseline.json) — frozen v0.2 release claims
- [`benchmark/FROZEN_AT`](../../benchmark/FROZEN_AT) — frozen v0.2 evidence provenance
- [`swos_prose/repair.py`](../../swos_prose/repair.py) — bounded M1 repair implementation
- [`swos_prose/`](../../swos_prose/) — host-neutral Python implementation
