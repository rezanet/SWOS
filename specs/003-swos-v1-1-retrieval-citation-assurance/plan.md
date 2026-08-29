# Implementation Plan: SWOS v1.1 Retrieval and Citation Assurance

## Scope

Implement only capability-ledger gaps V11-RERANK-001 and V11-CITE-001 through
V11-CITE-005, plus bounded V11-CLI-001 test coverage. Core/specification
`1.0.0`, reference runtime `v1.1` and Research Grade `v2.0` remain distinct.

## Dependency order

1. Define failing cross-encoder and citation-assurance tests.
2. Implement injectable reranker and broker binding.
3. Extend SourceRecord and retrieval metadata parsers.
4. Enforce source-owned retraction/licence/quotation/support admission.
5. Propagate assurance into EPG and audit artifacts.
6. Add offline CLI coverage and run exact-head gates.

## Requirement traceability

| Requirement | Implementation response |
|---|---|
| FR-001 | `swos_runtime/reranking.py` with injected model and complete score evidence. |
| FR-002 | Separate `rerank_binding` in broker and adapter composition. |
| FR-003 | SourceRecord normalization and OpenAlex/Crossref parser tests. |
| FR-004 | Source-owned retraction fields and finalizer clean-only gate. |
| FR-005 | Source-owned rights fields and finalizer cleared-only gate. |
| FR-006 | Existing exact-quote helper retained and negative tests expanded. |
| FR-007 | Existing frozen six-value vocabulary validated; only direct support admitted. |
| FR-008 | Finalizer writes assurance values into evidence and EPG outputs. |
| FR-009 | CLI tests inject offline bindings and credentials remain absent. |
| NFR-001 | Negative tests cover all fail-closed states. |
| NFR-002 | Optional dependency group; deterministic tests use fake model. |
| NFR-003 | No workflow/provider path added to PR checks. |
| NFR-004 | Version tracks unchanged. |
| NFR-005 | Strict existing schemas validate produced artifacts. |

## Risks

| Risk | Mitigation |
|---|---|
| Heavy ML dependency burdens base install | Keep sentence-transformers optional and lazily imported. |
| Crossref/OpenAlex absence mistaken for clean | Default to `not_checked` and uncleared rights. |
| Model-supplied booleans bypass external facts | Finalizer derives decisions from SourceRecord assurance only. |
| Existing fixture runs break silently | Update fixtures explicitly and retain unsafe negative cases. |
| Generative reranker remains active accidentally | Reference adapter gets a dedicated rerank binding and evidence identity. |

## Verification checkpoints

- Reranker tests pass before adapter integration.
- Citation assurance tests pass before full runtime suite.
- All generated audit artifacts validate against frozen schemas.
- Exact-head CI schedules deterministic checks only; live workflows remain skipped.

## Boundaries

This PR stops after retrieval/citation assurance. Governed stores are the next
Spec Kit slice and must consume these source assurance fields without redesigning
them.
