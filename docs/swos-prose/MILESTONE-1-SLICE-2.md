# SWOS Prose — Milestone 1 Slice 2: Bidirectional Verifier Contract

**Status:** implementation slice 2 foundation + adversarial contract hardening  
**Goal:** define and enforce proposition-level verifier output before binding any real model/provider.

## Why this slice exists

PR #3 established deterministic hard gates and a provider-neutral verifier protocol. Slice 2 makes the provider contract materially stronger: the verifier must describe what source propositions were preserved and what candidate propositions are licensed by the source, while the SWOS Prose core independently validates that the report is complete and internally coherent.

The provider is not allowed to decide `PASS / REPAIR / REVIEW / REJECT`. The SWOS Prose core owns that decision.

## What this slice adds

- structured source and candidate proposition records;
- source -> candidate preservation mappings;
- candidate -> source licensing mappings;
- explicit preservation dimensions for modality, scope, attribution, causal force and relational direction;
- optional provider-extracted subject/relation/object fields;
- unresolved proposition-level findings;
- a static JSON-backed verifier provider for deterministic tests;
- translation from proposition reports into core semantic deltas;
- strict/review assurance requirements for a complete bidirectional report;
- regression tests proving that provider claims cannot override core safety decisions.

## Core contract validators

The core, not the provider, enforces these invariants:

1. **Source coverage** — every declared source proposition must have a source-to-candidate mapping. In `strict`/`review`, silent omission is a blocking malformed response; in `standard`, it routes to `REVIEW`.
2. **Candidate licensing coverage** — every declared candidate proposition must have a candidate-to-source mapping. An orphan candidate is treated as an unlicensed `CLAIM_ADDED` blocker.
3. **ID integrity** — mapping references to nonexistent source/candidate proposition IDs produce `MALFORMED_PROVIDER_RESPONSE` and block automatic approval rather than crashing or being ignored.
4. **Duplicate/contradictory report structure** — duplicate proposition IDs or duplicate mappings are surfaced as malformed-provider findings.
5. **Relational direction cross-check** — for a deliberately narrow set of binary relations that the core can parse deterministically (`associated with`, `correlated with`, `linked to`, `related to`), subject/object reversal becomes a `DIRECTION_REVERSAL` blocker even if the provider says direction is preserved.
6. **Provider directional metadata is non-authoritative** — if provider-supplied subject/relation/object fields disagree with the core parse, automatic approval is blocked.
7. **Empty-input boundary** — whitespace-only source/candidate is an explicit no-change `PASS`; adding text to an empty source or deleting all source text is a blocker. Changed non-semantic text with an empty proposition report remains `REVIEW`.
8. **Malformed provider payloads fail safely** — provider parsing/type errors become `MALFORMED_PROVIDER_RESPONSE`/`REVIEW`, not uncaught exceptions.

## Decision precedence

The runtime order is:

1. explicit empty/malformed input boundary checks;
2. deterministic hard-anchor/high-risk checks;
3. short-circuit on deterministic blocker;
4. provider proposition report;
5. core report-integrity validation;
6. core proposition-delta conversion and narrow deterministic direction check;
7. SWOS-owned decision classifier.

A provider returning `equivalent: true` cannot override:

- an unlicensed/orphan candidate proposition;
- a lost or silently omitted source proposition in strict assurance;
- malformed cross-references;
- an explicit modality/attribution/causal/direction preservation failure;
- a core-detected relation reversal;
- unresolved or incomplete mappings.

## Deliberate non-goals

This slice does **not**:

- call OpenAI, Anthropic, Google or any other model API;
- extract general propositions with an LLM;
- claim general dependency parsing from regexes;
- implement prose generation;
- implement repair loops;
- use embeddings as semantic approval;
- fully resolve lexical-negation, attribution-force or quantifier/modal-binding attack issues.

The relation-direction parser is intentionally narrow. Anything outside its reliable pattern remains the job of the semantic verifier and future attack-hardening work; the core must not pretend a heuristic is a proof.

## Static provider purpose

`StaticSemanticVerifierProvider` accepts JSON-compatible data and performs no inference. It lets tests model complete, contradictory, incomplete, malformed, unresolved and malicious verifier responses before any vendor/model adapter is introduced.

Only after this contract is stable should a real semantic-verifier adapter be implemented.
