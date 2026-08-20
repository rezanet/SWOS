# SWOS Prose — Milestone 2 Slice 1: Basic Polish Pipeline

**Status:** implementation candidate  
**Mode:** `polish` only  
**Goal:** connect real rewrite generation to the existing semantic verifier with safe fallback.

## Product boundary

This is the first SWOS Prose slice that generates prose.

The pipeline is deliberately narrow:

```text
SOURCE
  -> protected-anchor extraction
  -> one polish candidate
  -> semantic verification
  -> PASS: candidate
  -> anything else: source fallback
```

There is **no repair loop** in this slice. `REPAIR`, `REVIEW`, and `REJECT` are all non-releasable outcomes and preserve the source.

## Rewrite provider

`RewriteProvider` is provider-agnostic. The first real adapter is `OpenAIResponsesRewriteProvider`, which uses strict JSON-schema output through the Responses API.

The rewriter:

- implements only `mode="polish"`;
- receives protected numbers, citations, and quotations;
- receives a compact rewrite plan;
- must preserve protected anchors verbatim;
- may improve clarity, sentence construction, local flow, concision, and natural readability;
- may not add facts, examples, evidence, citations, quotations, explanations, or conclusions;
- may not strengthen certainty or causality;
- may not change attribution, scope, chronology, negation, conditions, exceptions, epistemic type, or normative stance;
- returns the source unchanged when no safe improvement is available.

The rewrite provider never approves its own output.

## Core API

```python
from swos_prose import polish_text
from swos_prose.providers.openai_rewrite import OpenAIResponsesRewriteProvider
from swos_prose.providers.openai_responses import OpenAIResponsesSemanticVerifierProvider

result = polish_text(
    source="The analysis was performed using a t-test.",
    rewrite_provider=OpenAIResponsesRewriteProvider(),
    verifier_provider=OpenAIResponsesSemanticVerifierProvider(),
    assurance="strict",
)

print(result.final_text)
print(result.verification_status)
```

## Safety rule

Only:

```text
verification.status == PASS
```

may release the candidate automatically.

Until a repair loop exists:

```text
REPAIR -> source
REVIEW -> source
REJECT -> source
```

This is intentionally stricter than treating `REPAIR` as usable prose.

## Tests

Provider-independent tests cover:

- safe candidate -> PASS -> candidate returned;
- numeric drift -> deterministic REJECT -> source fallback before verifier call;
- changed candidate without semantic verifier -> REVIEW -> source fallback;
- synthetic REPAIR -> source fallback because repair is not implemented;
- protected anchors passed verbatim to the rewrite provider;
- empty input no-op;
- OpenAI rewrite adapter request shape, strict schema, `store=False`, temperature 0, and token accounting;
- unsupported rewrite modes fail explicitly.

## Deliberate non-goals

This slice does not implement:

- `naturalise`;
- `clarify`;
- `tighten`;
- diagnostics;
- multi-candidate ranking;
- repair;
- paragraph-context editing beyond optional read-only context parameters;
- voice/style profiles;
- document-wide flow;
- claims that a live hosted model has already met the benchmark.

## Next slice

Dogfood `polish` against real prose, collect the rejected/reviewed candidates, and use those failures to design the bounded local repair loop. Do not broaden into additional modes until the basic rewrite -> verify -> fallback path is stable.
