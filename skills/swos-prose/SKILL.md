---
name: swos-prose
description: Semantic-safe prose polishing for text whose meaning is already settled. Use when asked to polish, edit, clarify, tighten wording, reduce repetition, improve sentence construction, or make academic, technical, explanatory, or enterprise prose read more naturally without changing its factual claims, attribution, uncertainty, modality, degree, causality, numbers, citations, quotations, chronology, conditions, or normative force. Runs conservative pre-generation diagnostics, one rewrite proposal when needed, and independent semantic verification; unsafe or uncertain rewrites fall back to the source.
license: MIT
compatibility: Requires the SWOS Prose Python package. Changed prose needs a rewrite provider and an independent semantic-verifier provider; the bundled OpenAI Responses adapters require the optional openai package and an API key. Exact reviewed diagnostics exemplars can abstain with zero provider calls. No host-specific runtime is required.
metadata:
  version: 0.2.0
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

## Released surface: v0.2

Only `mode=polish` is released in v0.2.

`naturalise`, `clarify` and `tighten` are useful user intents, but they are **not
separate implemented modes yet**. Route those requests through `polish` only when
the requested improvement can be made under the same semantic-preservation
contract. Do not advertise or invoke nonexistent modes.

Supported assurance levels are `standard`, `strict` and `review`. Prefer `strict`
for scholarly, technical, policy, legal-adjacent, quantitative or otherwise
force-sensitive prose.

## Safety contract

A polish may improve:

- sentence construction and local flow;
- concision and unnecessary repetition;
- natural readability;
- wording and syntax.

It must preserve:

- every material proposition;
- attribution and source responsibility;
- uncertainty and epistemic status;
- modality (`may`, `might`, `must`, `should`, and related force);
- degree and scalar force (`slightly`, `substantially`, `nearly`, and related terms);
- negation;
- causal force;
- scope and quantifiers;
- chronology, conditions and exceptions;
- normative stance;
- protected numbers, citations and quotations verbatim where the current engine
  marks them as anchors.

Never add facts, evidence, examples, citations, explanations or conclusions. Never
resolve ambiguity by guessing. Never strengthen an association into causation,
possibility into certainty, or a qualified statement into an unqualified one.

## Execution order

1. **Diagnose before generation.** The current deterministic fast path may return
   `NO_CHANGE_RECOMMENDED` only for an exact reviewed whole-sentence exemplar with
   no blocking signal and no neighbouring context that requires richer analysis.
2. **Generate once when needed.** The rewrite provider proposes wording; it does
   not approve its own work.
3. **Verify independently.** Changed text is checked by the semantic-delta engine
   and, when required, an independent semantic verifier.
4. **Fail closed.** Only verified `PASS` text is automatically released. `REVIEW`,
   `REJECT`, malformed provider output or provider failure returns the original
   source as `final_text`.

There is no repair loop in v0.2.

## Interpret the result

| Outcome | Meaning | Action |
|---|---|---|
| `NO_CHANGE_RECOMMENDED` | Source is returned unchanged; diagnostics or a no-op boundary avoided a rewrite | Keep the source |
| `PASS` | Candidate passed the current semantic-safety contract | Candidate may be used automatically |
| `REVIEW` | Equivalence is unresolved or a warning remains | Keep source; ask for human review if a rewrite is still wanted |
| `REJECT` | A blocking semantic delta was detected | Keep source; do not use the candidate |
| provider failure | Generation or verification failed safely | Keep source; report the failure |

Do not reinterpret `REVIEW` as a soft PASS. Conservatism is an intended property.

## Boundaries

SWOS Prose does **not** establish whether the source itself is true, well-cited or
well-researched. Use `swos-core` and `swos-citation-auditor` for evidence and
citation integrity before polishing.

Do not use v0.2 to:

- invent or repair missing facts;
- change an author's position;
- perform free creative rewriting where semantic drift is desired;
- translate between languages;
- normalize protected numbers, citations or quotations;
- promise deterministic verifier outcomes on equivalent paraphrases.

Verifier stability is tracked separately in issue #32; safe uncertainty remains
`REVIEW`/`REJECT` rather than being coerced into PASS.

## Governed benchmark evidence

The frozen v0.2 benchmark is [`benchmark/baseline.json`](../../benchmark/baseline.json).
On that **specific governed 50-case benchmark**:

- 22 labelled material-change probes produced **0 unsafe PASS** outcomes;
- Diagnostics produced **0 unsafe abstentions**;
- the exact reviewed fast path abstained on 3/50 cases (6% coverage);
- the measured token counterfactual saved 2,358 of 77,593 tokens (**3.04%**);
- 11 stability probes were repeated five times with **0 unsafe PASS** outcomes.

These are benchmark observations, not a universal guarantee for arbitrary prose.
Equivalent-pair REVIEW/REJECT outcomes remain visible in the baseline as
quality/stability costs.

## CLI

The CLI keeps stdout composable: plain `polish` prints only `final_text`; status and
setup messages go to stderr. Use `--json` for the full diagnostics, verification and
token record.

### Example 1 - polish literal text

```bash
export OPENAI_API_KEY=...
python3 -m swos_prose.cli polish \
  --source "The analysis was performed using a t-test." \
  --assurance strict \
  --json
```

### Example 2 - polish a file with read-only context

```bash
python3 -m swos_prose.cli polish \
  --source draft-paragraph.txt \
  --context-before previous-paragraph.txt \
  --context-after next-paragraph.txt \
  --assurance strict
```

Supplying neighbouring context disables the current early diagnostics abstention
unless future diagnostics become context-aware; context may inform flow but may not
license a new proposition absent from the source.

For semantic-calibration work that must force the provider/verifier path, add
`--skip-diagnostics`. Do not use that flag merely to chase a rewrite when the fast
path correctly abstains.

## Library API

### Example 3 - call `polish_text`

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
print(result.generation_skipped_by_diagnostics)
```

Consumers should use `final_text`, not the raw `candidate`, unless they are building
a review interface that deliberately exposes rejected/uncertain proposals.

## Verification-only API

When a candidate already exists, use `verify_rewrite(source=..., candidate=...)`.
Changed text without a bound semantic verifier cannot receive automatic PASS under
the strict/review contract.

## Resources

- [`benchmark/baseline.json`](../../benchmark/baseline.json) - frozen compact v0.2 benchmark claims
- [`benchmark/FROZEN_AT`](../../benchmark/FROZEN_AT) - evidence provenance and digests
- [`docs/swos-prose/MILESTONE-2-POLISH.md`](../../docs/swos-prose/MILESTONE-2-POLISH.md) - polish implementation contract
- [`swos_prose/`](../../swos_prose/) - host-neutral Python implementation
