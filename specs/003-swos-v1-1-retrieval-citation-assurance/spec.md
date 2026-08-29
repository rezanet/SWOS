# Feature Specification: SWOS v1.1 Retrieval and Citation Assurance

## Objective

Implement the verified retrieval/citation gaps from capability ledger IDs
V11-RERANK-001, V11-CITE-001 through V11-CITE-005, and the bounded offline CLI
coverage in V11-CLI-001. Retain PR #41's OpenAlex/Crossref retrieval, exact-quote
gate, capability broker and provider-neutral orchestration.

### User Story 1 — Reproducible reranking

As a reviewer, I can identify the exact cross-encoder model and reproduce its
query-document scores from recorded inputs, while malformed or unavailable
scoring fails closed.

### User Story 2 — Externally checked citations

As a citation auditor, I can see normalized metadata, retraction state, licence
position, quotation evidence and support classification for every admitted
claim; unknown or unsafe checks cannot become verified citations.

### User Story 3 — Deterministic operator path

As a maintainer, I can exercise the end-to-end CLI with injected/offline
capabilities and prove that ordinary PR validation performs no provider call.

## Functional Requirements

- **FR-001:** Provide an explicit cross-encoder reranker that jointly scores one
  query-document pair at a time and records model identity and all scores.
- **FR-002:** Route the reference API adapter's semantic-rerank capability through
  the cross-encoder binding without moving scholarly authority into the adapter.
- **FR-003:** Normalize citation DOI, title, authors, date, URL and provider
  provenance from OpenAlex and Crossref.
- **FR-004:** Record retraction state, check source and check time; only `clean`
  sources may automatically support a claim.
- **FR-005:** Record licence, access state, redistribution decision, excerpt limit,
  check source and check time; unknown or uncleared rights fail closed.
- **FR-006:** Preserve exact quotation containment and derive quotation acceptance
  from retrieved source text rather than model assertion.
- **FR-007:** Validate all six frozen citation-support values and admit only
  `directly_supports`; partial, contextual, contradictory, laundering-risk and
  invalid decisions remain explicit failed/withheld evidence.
- **FR-008:** Emit retrieval/rerank/citation assurance evidence with complete
  provenance in the run audit pack.
- **FR-009:** Add deterministic CLI coverage that uses no provider credentials.

## Non-Functional Requirements

- **NFR-001:** All missing, malformed, non-finite, retracted, unchecked or
  rights-unknown evidence fails closed.
- **NFR-002:** The cross-encoder runtime is an optional retrieval dependency; the
  base deterministic suite remains lightweight and injects a test scorer.
- **NFR-003:** Ordinary PR checks never read provider credentials or perform paid
  calls.
- **NFR-004:** Core/specification remains `1.0.0`, reference runtime remains
  `v1.1`, and Research Grade remains `v2.0`.
- **NFR-005:** Frozen schemas and capability contracts are extended only through
  already-permitted fields and values.

## Commands

```powershell
python -m unittest tests/runtime/test_reranking.py tests/runtime/test_citation_assurance.py
python -m unittest discover -s tests/runtime -p 'test_*.py'
python tools/check_spec_kit_artifacts.py
python tools/validate_document_manifest.py
python tools/validate_schemas.py --strict
python tools/check_host_independence.py
python tools/check_vendor_leakage.py
python tools/check_portability_acceptance.py --definitions-only
python -m ruff format --check swos_runtime tests/runtime tools
python -m ruff check swos_runtime tests/runtime tools
```

## Project Structure

- `swos_runtime/reranking.py` — optional, injectable cross-encoder reference path.
- `swos_runtime/models.py` — normalized source assurance fields.
- `swos_runtime/retrieval.py` — OpenAlex/Crossref metadata and assurance parsing.
- `swos_runtime/broker.py` — independent rerank binding.
- `swos_runtime/adapter_factory.py` — reference binding composition.
- `swos_runtime/finalizer.py` — fail-closed citation admission and audit output.
- `tests/runtime/test_reranking.py` — cross-encoder behavior and negative paths.
- `tests/runtime/test_citation_assurance.py` — metadata, rights, retraction and support gates.

## Code and Document Style

Dependencies are injected behind a small callable surface:

```python
reranker = CrossEncoderReranker(model=fake_model, model_name="fixture-cross-encoder")
ranked, evidence = reranker.rerank(query, sources, top_k=5)
```

Network metadata remains untrusted. Parse defensively, use explicit defaults and
record unknown rather than inventing a clean or licensed result.

## Testing Strategy

Use TDD at the reranker, source parser and finalizer admission seams. Tests inject
fixed scorer outputs and recorded API-shaped payloads. Negative tests cover score
count/type/NaN, retraction, expression of concern, absent check evidence, unknown
rights, invalid support values and non-exact quotations. Then rerun all runtime,
schema, governance, host-independence and portability-definition gates.

## Boundaries

- Always: preserve existing public retrieval and exact-quote behavior.
- Always: record check source/time and model identity.
- Ask first: any frozen schema or capability-contract change.
- Never: treat a capability marker as proof a cross-encoder ran.
- Never: infer clean retraction or cleared rights from absent metadata.
- Never: install or invoke a paid provider in ordinary tests.
- Never: implement governed stores, human approval or public release in this PR.

## Success Criteria

- Cross-encoder fixtures deterministically rerank and malformed results fail.
- OpenAlex/Crossref fixtures produce normalized assurance evidence.
- Unsafe/unknown retraction and licence states cannot enter verified Evidence Matrix rows.
- Existing quotation and support decisions remain fail closed.
- Offline CLI and all deterministic repository gates pass.
