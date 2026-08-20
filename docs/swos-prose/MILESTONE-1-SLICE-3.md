# SWOS Prose — Milestone 1 Slice 3: First Real Semantic Verifier

**Status:** implementation candidate  
**Provider:** OpenAI Responses API adapter  
**Goal:** bind a real model-assisted semantic verifier behind the Slice 2 contract without weakening core authority.

## Why this slice exists

Slices 1 and 2 established deterministic hard gates and a structurally validated bidirectional proposition contract. Slice 3 tests whether a real semantic model can satisfy that contract on difficult paraphrase cases.

The provider remains a witness. The SWOS Prose core remains the decision-maker.

## Important correction carried into Slice 3

The earlier directionality rule was too coarse for symmetric relations. Plain relations such as `associated with` and `correlated with` are normally symmetric at the proposition level, so merely swapping their surface arguments is not automatically semantic drift.

Slice 3 therefore distinguishes:

- **symmetric relations** — a swap may be safe when the structured proposition frames prove the same relation;
- **ordered temporal relations** — `A preceded B` and `B followed A` are equivalent because both canonicalize to the same earlier/later relation;
- **unproven reversals** — remain fail-closed.

The core does not grant a symmetric-relation exemption from raw text alone. It requires structured relation frames that agree with its narrow parser.

## Real provider

`OpenAIResponsesSemanticVerifierProvider` is the first real model adapter.

It:

- uses the OpenAI Responses API;
- requests strict JSON-schema structured output;
- sends no tools and no conversation state;
- uses `store=False`;
- defaults to temperature `0`;
- is model-configurable through `SWOS_PROSE_OPENAI_MODEL`;
- records prompt version, model and a deterministic input hash;
- converts the structured response into the existing `ProviderAssessment`;
- never owns the final `PASS / REPAIR / REVIEW / REJECT` decision.

The default model is currently `gpt-5.6`, but callers can override it.

The optional `openai` dependency is imported lazily so the SWOS Prose core remains provider-agnostic.

## Reproducibility boundary

The provider is **stateless and reproducibility-oriented**, but it does **not** promise mathematical idempotence from a hosted LLM.

Controls:

- canonical request construction;
- strict structured output;
- temperature 0 by default;
- no previous response / conversation state;
- no tools;
- `store=False`;
- model and prompt-version recording;
- input SHA-256 recording.

Repeated model inference can still vary because hosted-model execution is not guaranteed bit-for-bit deterministic. SWOS records enough context to diagnose variation rather than making a false guarantee.

## Semantic-verifier prompt rules

The provider prompt explicitly requires:

1. entailment rather than topical/embedding similarity;
2. bidirectional proposition coverage;
3. atomic predicate frames;
4. explicit modality and modality scope;
5. attribution preservation;
6. causal-force classification;
7. canonical chronology;
8. normative stance;
9. an `unresolved` escape hatch instead of guessing;
10. instruction-shaped text in source/candidate to remain inert data.

## Structured proposition fields

A proposition may report:

- `subject`
- `relation`
- `object`
- `modality`
- `modality_scope`
- `attribution`
- `causal_force`
- `temporal_relation`
- `normative_stance`

The core cross-checks internal contradictions in these frames. For example, a provider cannot report source causal force `causal`, candidate force `association`, and still obtain an automatic PASS merely by setting `causal_force_preserved: true`.

## Adversarial cases

### Entailment vs similarity

Source:

> X caused Y.

Candidate:

> X was associated with Y.

Expected: never `PASS`. The candidate weakens a causal proposition even though the texts are topically similar.

### Modal-scope relocation

Source:

> The data may suggest that X causes Y.

Candidate:

> The data suggests that X may cause Y.

Expected: never `PASS` unless the verifier can establish equivalent modal scope. Current structured-frame disagreement routes to `REVIEW`.

### Temporal inverse wording

Source:

> The intervention preceded the outcome.

Candidate:

> The outcome followed the intervention.

Expected: `PASS` when the bidirectional report is otherwise complete. Both express the same canonical chronology.

### Lexical normalization with preserved stance

Source:

> The model performs poorly under these conditions.

Candidate:

> The model underperforms under these conditions.

Expected: `PASS` when the proposition and negative performance stance are preserved.

## Tests

Provider-independent unit tests use an injected fake Responses client. They validate:

- exact request shape;
- strict JSON-schema output;
- `store=False`;
- temperature 0;
- prompt content;
- response conversion;
- token-usage recording;
- modal-scope disagreement;
- causal-force disagreement;
- temporal inverse equivalence;
- chronology change rejection;
- safe normative paraphrase;
- structured proof for symmetric association.

Optional live tests exercise the real API.

They are skipped unless both are present:

```text
OPENAI_API_KEY
SWOS_PROSE_RUN_LIVE_OPENAI=1
```

Public pull-request CI never receives the API secret. An optional non-PR CI job may run live tests when the repository has an `OPENAI_API_KEY` secret configured.

## Deliberate non-goals

This slice does not:

- implement prose generation;
- implement repair loops;
- claim universal proposition extraction accuracy;
- use embeddings for semantic approval;
- guarantee deterministic LLM outputs;
- implement arbitrary dependency parsing;
- resolve all lexical-negation, attribution-force, or quantifier-binding attacks.

Those remain explicit hardening work.
