# SWOS Prose — Milestone 1 Slice 2: Bidirectional Verifier Contract

**Status:** implementation slice 2 foundation  
**Goal:** define and exercise proposition-level verifier output before binding any real model/provider.

## Why this slice exists

PR #3 established deterministic hard gates and a provider-neutral verifier protocol. This slice makes the provider contract materially stronger: the verifier must be able to describe what source propositions were preserved and what candidate propositions are licensed by the source.

The provider is still not allowed to decide `PASS / REPAIR / REVIEW / REJECT`. The SWOS Prose core owns that decision.

## What this slice adds

- structured source and candidate proposition records;
- source -> candidate preservation mappings;
- candidate -> source licensing mappings;
- explicit preservation dimensions for modality, scope, attribution and causal force;
- unresolved proposition-level findings;
- a static JSON-backed verifier provider for deterministic tests;
- translation from proposition reports into core semantic deltas;
- strict-mode requirement for a bidirectional proposition report;
- regression tests proving that a provider cannot override core safety decisions.

## Deliberate non-goals

This slice does **not**:

- call OpenAI, Anthropic, Google or any other model API;
- extract propositions with an LLM;
- implement prose generation;
- implement repairs;
- claim semantic equivalence from embeddings;
- resolve the adversarial attack issues opened after PR #3.

## Decision precedence

The runtime order is:

1. deterministic hard-anchor/high-risk checks;
2. short-circuit on deterministic blocker;
3. provider proposition report;
4. SWOS-owned conversion of provider claims into semantic deltas;
5. SWOS-owned decision classifier.

A provider returning `equivalent: true` cannot override:

- an unlicensed candidate proposition;
- a lost source proposition;
- an explicit modality/attribution/causal preservation failure;
- an unresolved or incomplete mapping in strict/review assurance.

## Static provider purpose

`StaticSemanticVerifierProvider` accepts JSON-compatible data and performs no inference. It lets the test suite model:

- a complete safe report;
- a malicious provider claiming equivalence while reporting an added claim;
- missing mappings;
- unresolved scope;
- provider disagreement;
- deterministic short-circuit behaviour.

Only after this contract is stable should a real semantic-verifier adapter be implemented.

## Next implementation step

Bind a real semantic verifier behind the same protocol and test it against the attack corpus. The first real provider must emit this structured report; it must not return only a prose explanation or a single similarity score.
