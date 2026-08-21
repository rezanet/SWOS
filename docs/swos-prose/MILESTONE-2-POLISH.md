# SWOS Prose — Milestone 2: Polish Pipeline

**Status:** implementation candidate  
**Mode:** `polish` only  
**Goal:** connect real rewrite generation to the semantic verifier with safe fallback, while proving a conservative zero-provider abstention contract.

## Product boundary

The pipeline remains deliberately narrow:

```text
SOURCE
  -> conservative pre-generation diagnostics
     -> reviewed whole-sentence exemplar + no warning: source returned unchanged
     -> otherwise continue
  -> protected-anchor extraction
  -> one polish candidate
  -> semantic verification
  -> PASS: candidate
  -> anything else: source fallback
```

There is **no repair loop** in this slice. `REPAIR`, `REVIEW`, and `REJECT` are all non-releasable outcomes and preserve the source.

## Pre-generation diagnostics

The first diagnostics slice is deliberately fail-closed. It is not a style score, grammar checker, parser, or semantic verifier.

`NO_CHANGE_RECOMMENDED` is available only when:

- the complete source sentence matches an explicitly reviewed whole-sentence abstention exemplar;
- no reviewed editorial-defect or uncertainty signal is present;
- no neighbouring `context_before` / `context_after` is supplied.

The absence of a known defect is never enough by itself, and no wildcard/object-span grammar is used to certify arbitrary English. Anything outside the reviewed exemplar set becomes `PROCEED_TO_REWRITE`, which means only that diagnostics are not confident enough to abstain.

The exemplar set is intentionally tiny. Expanding zero-cost abstention coverage is a Benchmark task: add complete reviewed exemplars only when empirical evidence justifies them instead of making deterministic parsing progressively more permissive.

A diagnostics abstention is a no-op: candidate and final text are the source, no rewrite provider is called, no semantic verifier is called, and token usage remains zero. `PolishResult` records `diagnostics_before` and `generation_skipped_by_diagnostics` so callers can distinguish this path from verifier-backed outcomes.

For semantic calibration, diagnostics can be explicitly disabled with `run_diagnostics=False`; the CLI exposes this as `--skip-diagnostics`. The trusted five-case Luna calibration workflow uses that bypass so diagnostics cannot hide verifier coverage.

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
print(result.diagnostics_before)
```

## Safety rule

A **changed candidate** may be released automatically only when:

```text
verification.status == PASS
```

A diagnostics abstention does not release a changed candidate; it returns the original source unchanged.

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
- reviewed exemplar -> source unchanged with zero provider calls;
- absence of a reviewed exemplar -> proceed to rewrite even when the sentence appears well formed;
- malformed coordinated tails cannot hide behind a trusted predicate substring;
- force-bearing language -> proceed to richer rewrite/verifier path;
- neighbouring context -> no early diagnostics abstention;
- explicit diagnostics bypass for semantic calibration;
- dogfood summary reports the actual diagnostics mode;
- OpenAI rewrite adapter request shape, strict schema, `store=False`, optional temperature forwarding, and token accounting;
- unsupported rewrite modes fail explicitly.

## Deliberate non-goals

This slice does not implement:

- `naturalise`;
- `clarify`;
- `tighten`;
- context-aware diagnostics;
- post-rewrite diagnostics;
- broad grammar or spelling proof;
- general deterministic certification of already-good English;
- multi-candidate ranking;
- repair;
- voice/style profiles;
- document-wide flow;
- claims that a hosted verifier is deterministic.

## Next slice

Use dogfood and benchmark evidence to measure three things separately: semantic safety, editorial improvement, and diagnostics efficiency. Keep the diagnostics-enabled efficiency campaign separate from the diagnostics-disabled semantic-calibration campaign. Expand the abstention exemplar set only from reviewed benchmark evidence; do not broaden it through a parser exception arms race.
