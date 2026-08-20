# SWOS Prose — Milestone 1: Semantic Delta Engine

**Status:** implementation slice 1 of the SWOS Prose v0.2 specification  
**Goal:** prove that SWOS Prose can recognise meaning drift before it is allowed to generate prose.

## Why this comes first

A prose engine is only distinctive if it can improve language without silently changing claims. Presets, humanisation and document flow are deliberately deferred until the verifier can reject known semantic traps.

## This PR builds

- an executable `swos_prose` Python package;
- protected-anchor extraction for numbers, citations and direct quotations;
- high-risk linguistic signals for negation, modality, causality, quantifiers, scope and attribution;
- structured `SemanticDelta` records;
- `PASS / REPAIR / REVIEW / REJECT` result states;
- a provider-neutral `SemanticVerifierProvider` protocol;
- a `verify_rewrite()` pipeline;
- a `verify` CLI;
- regression tests for the first semantic traps;
- CI execution of the deterministic prose tests.

## Deliberate safety behaviour

Changed text without a bound semantic verifier cannot receive an automatic `PASS`. If deterministic checks find no blocker but proposition-level equivalence is unresolved, the result is `REVIEW`.

Embedding similarity is not an approval mechanism.

Hard protected anchors are fail-closed in this slice:

- number drift -> `REJECT`;
- citation removal/change -> `REJECT`;
- direct quotation change -> `REJECT`.

Clear semantic strengthening is also rejected, including:

- negation flip;
- `may` -> unqualified assertion;
- `suggests` -> `demonstrates`;
- association -> causation;
- `some` -> `most/all`;
- attribution removal.

Potentially safe but ambiguous changes, such as paraphrased scope markers, are routed to `REVIEW` rather than guessed safe.

## Not in this PR

- prose generation;
- repair loops;
- style presets;
- full document editing;
- voice/style-reference imitation;
- provider SDK bindings;
- embedding-based semantic approval;
- governance expansion.

## Next slice

Milestone 1 continues with a real model/provider adapter and proposition-level bidirectional verification:

1. source proposition -> candidate proposition preservation;
2. candidate proposition -> source licensing;
3. disagreement between deterministic and model-assisted analysis -> `REVIEW`;
4. structured provider deltas consumed by the core classifier.

Only after the semantic verifier is credible should Milestone 2 add `polish`, `naturalise`, `clarify` and `tighten` generation.

## Reviewer checklist

Reviewers should verify that:

- no changed candidate can silently PASS without semantic verification;
- known hard-anchor corruption fails closed;
- causality/certainty/negation traps cannot PASS;
- uncertain equivalence routes to REVIEW;
- provider code cannot directly declare final release status; the core classifier owns the decision;
- tests exercise the failure cases, not just happy paths.
