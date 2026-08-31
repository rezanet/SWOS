# SWOS v1.1 Runtime Capability Ledger

**Reconciliation base:** `5eec89e88e11e9659299d51c1bbf8289b81e464f`

**PR #41 merge inspected:** `156e2b7faa70f9affce2ed93d7dc3cb6e19b938e`

**Authority:** `docs/roadmap.md`, the historical `v1.1` roadmap at the PR #41
merge, frozen Core `1.0.0` contracts/governance, and the PR #41 governed outcome
contract. PR prose is not evidence unless linked below to an exact artifact.

## Status key

`specified` < `implemented` < `tested` < `demonstrated` < `certified`.
The state column records the highest state proved for the complete named
requirement, not for a partial nearby artifact.

## Authority coverage

| Authority requirement group | Capability IDs |
|---|---|
| Historical `v1.1` roadmap at PR #41: reference orchestrator and state store | V11-ORCH-001, V11-STATE-001, V11-WORK-001 |
| Historical `v1.1` roadmap: EPG, SDL and RPM stores with hash chaining | V11-STORE-001 through V11-STORE-006, V11-AUDIT-001 |
| Historical `v1.1` roadmap: cross-encoder reranker first | V11-RERANK-001 |
| Historical `v1.1` roadmap: open scholarly-index adapters | V11-RETR-001, V11-RETR-002 |
| Historical `v1.1` roadmap: working end-to-end CLI | V11-CLI-001 |
| Historical `v1.1` roadmap: full harness bound to a real SUT | V11-EVAL-001, V11-EVAL-002 |
| Current Phase 1 retrieval/citation outputs | V11-RETR-001 through V11-RETR-002, V11-RERANK-001, V11-CITE-001 through V11-CITE-005 |
| Current Phase 1 governed-store/audit outputs | V11-EVID-001, V11-ARG-001, V11-STORE-001 through V11-STORE-006, V11-AUDIT-001 |
| Current Phase 1 evaluation/human-approval outputs | V11-REVIEW-001, V11-REVIEW-002, V11-EVAL-001, V11-EVAL-002, V11-APPROVAL-001 |
| Current Phase 1 public proof/release outputs | V11-PROOF-001, V11-REL-001 through V11-REL-006 |
| PR #41 governed runtime and portability contract | V11-ARCH-001, V11-WORK-001, V11-INST-001, V11-HOST-001, V11-PORT-001, V11-PROSE-001 |

## Capability evidence

| ID | v1.1 requirement | Slice | State | Implementation evidence | Deterministic test evidence | Demonstration / certification evidence | Verified gap and disposition |
|---|---|---|---|---|---|---|---|
| V11-ARCH-001 | Provider-neutral SWOS authority and capability broker | Reconciliation | tested | `swos_runtime/broker.py`; `swos_runtime/capabilities.py`; `contracts/capability-contract/capabilities-v1.json` | `tests/runtime/test_broker.py`; `tests/runtime/test_capabilities.py` | Demonstration: —; certification: — | No runtime gap; retain as substrate. |
| V11-WORK-001 | Persistent SWOS-owned work-order state machine | Reconciliation | tested | `swos_runtime/work_orders.py::WorkOrderRun` | `tests/runtime/test_work_orders.py` | Demonstration: host-flow fixture exports a replay bundle; certification: — | No implementation gap; public host execution remains release evidence work. |
| V11-INST-001 | Canonical hashed stage instructions | Reconciliation | tested | `swos_runtime/instructions.py`; `contracts/stage-instruction/stage-instructions-v1.json` | `tests/runtime/test_instructions.py` | Demonstration: —; certification: — | No gap; retain. |
| V11-HOST-001 | Replay/interchange host bundle separated from live execution | Reconciliation | tested | `swos_runtime/host_bundle.py`; `swos_runtime/work_orders.py::WorkOrderRun.export_host_bundle` | `tests/runtime/test_host_bundle.py`; `tests/runtime/test_work_orders.py::test_subscription_flow_is_swos_driven_and_exports_replay_bundle` | Demonstration: deterministic fixture; certification: — | No code gap; live host profiles remain uncertified. |
| V11-PORT-001 | Host/model/retrieval portability definitions without vendor authority leakage | Reconciliation | tested | adapter manifests; `tools/check_host_independence.py`; `tools/check_vendor_leakage.py`; `acceptance/portability/matrix-v1.json` | `tests/runtime/test_acceptance_matrix.py`; definitions-only validators | Demonstration: no complete checked-in hard-matrix evidence; certification: — | Execute only in explicit live release profiles after functional slices. |
| V11-ORCH-001 | Reference orchestrator for research through governed finalization | Reconciliation | demonstrated | `swos_runtime/orchestrator.py::AutonomousSWOS.run` | `tests/runtime/test_runtime.py`; `tests/runtime/test_research_expansion.py` | Demonstration: `RuntimeTests.test_complete_injected_run_is_approved_and_inspectable`; certification: — | Existing deterministic path retained; public-source independent proof remains V11-PROOF-001. |
| V11-STATE-001 | Reference scholarly state store | Governed stores | tested | file-backed `WorkOrderRun` state and `swos_runtime/finalizer.py::_scholarly_state` | `tests/runtime/test_work_orders.py`; complete injected run checks `scholarly-state.json` | Demonstration: deterministic run artifact; certification: — | Current state is run-local; durable correction/supersession is owned by V11-STORE-006. |
| V11-RETR-001 | Corpus adapters for open scholarly indexes | Retrieval | tested | `swos_runtime/retrieval.py::PublicWebRetriever._openalex`; `::_crossref` | `tests/runtime/test_retrieval.py::test_openalex_adapter_parses_verified_record_and_handles_error`; `::test_crossref_adapter_parses_record_and_handles_error` | Demonstration: mocked public responses only; certification: — | Keep adapters; add recorded public-source demonstration in retrieval slice. |
| V11-RETR-002 | Public authoritative web retrieval with source text, not search-summary evidence | Retrieval | tested | `swos_runtime/retrieval.py::PublicWebRetriever._openai_web`; seeded primary-law retrieval | `tests/runtime/test_retrieval.py::test_web_discovery_fetches_page_not_search_summary`; `::test_legal_seed_and_composite_retrieval_dedupe` | Demonstration: mocked responses; certification: — | Complete deterministic fixtures and later public proof; no ordinary paid call. |
| V11-RERANK-001 | Cross-encoder reranker reference implementation before capability expansion | Retrieval | tested | `swos_runtime/reranking.py::CrossEncoderReranker`; dedicated broker binding; reference adapter composition | `tests/runtime/test_reranking.py` covers scores, order, identity, malformed output, empty input and binding separation | Demonstration: deterministic injected cross-encoder; certification: — | Optional model dependency remains lazy; release demonstration remains in V11-PROOF-001. |
| V11-CITE-001 | Citation identity and bibliographic metadata | Retrieval | tested | `swos_runtime/models.py::SourceRecord`; OpenAlex/Crossref parsing; source register output | OpenAlex and Crossref adapter tests cover DOI, title, authors, date, URL and provider | Demonstration: deterministic run artifact; certification: — | Preserve normalized metadata through governed stores and public proof. |
| V11-CITE-002 | Retraction-status checking before support/release | Retrieval | tested | OpenAlex `is_retracted` and Crossref relation normalization; source-owned finalizer gate; EPG propagation | `tests/runtime/test_citation_assurance.py`; retrieval parser tests; finalizer suite | Demonstration: deterministic registry fixtures; certification: — | Unknown, corrected and retracted states remain inadmissible for automatic support. |
| V11-CITE-003 | Licence and source-rights checking before store/export | Retrieval | tested | OpenAlex/Crossref licence normalization; source-owned finalizer gate; EPG and source-register propagation | `tests/runtime/test_citation_assurance.py`; retrieval parser tests; finalizer suite | Demonstration: deterministic allow/unknown fixtures; certification: — | Unknown or unrecognized rights remain fail-closed; public proof must record exact rights evidence. |
| V11-CITE-004 | Exact quotation verification against retrieved source text | Retrieval | tested | `swos_runtime/governance.py::exact_quote_supported`; finalizer evidence gate | `RuntimeTests.test_exact_quote_must_be_in_source`; `HostNativeFinalizerTests.test_quote_not_in_source_is_rejected_before_argument_or_draft` | Demonstration: complete injected run; certification: — | Add locator/boundary evidence in retrieval slice; core containment gate retained. |
| V11-CITE-005 | Claim-support classification with fail-closed decisions | Retrieval | tested | `CapabilityBroker.citation_support_audit`; `WorkOrderRun._validate_citation_audit`; finalizer accepts only `directly_supports` | runtime bad-evidence/work-order validation plus all non-direct rejection fixtures | Demonstration: complete injected run; certification: — | Trained classifier remains `v2.0`; the v1.1 gate preserves all six frozen support values. |
| V11-EVID-001 | Evidence Matrix generated before drafting | Governed stores | demonstrated | `swos_runtime/finalizer.py::_evidence_matrix`; frozen schema | runtime acceptance and complete-run tests | Demonstration: `evidence-matrix.json` in complete injected run; certification: — | Persist through governed store API and correction history in stores slice. |
| V11-ARG-001 | Explicit Argument Graph before drafting | Governed stores | demonstrated | `swos_runtime/finalizer.py::_argument_graph`; frozen schema | runtime acceptance and finalizer tests | Demonstration: `argument-graph.json` in complete injected run; certification: — | Persist and verify correction/supersession in stores slice. |
| V11-PROSE-001 | Draft transformation passes SWOS Prose verification with source fallback | Reconciliation | tested | orchestrator Prose capability path; `swos_prose/` | runtime complete-run tests plus 240 Prose tests | Demonstration: deterministic injected run; certification: G-Prose95 certifies Prose profile only, not v1.1 runtime | No v1.1 runtime implementation gap. |
| V11-REVIEW-001 | Bounded review/revision loop with blockers routed back to work | Evaluation | tested | orchestrator/work-order review stages; finalized review artifacts; governance-plane evaluation | blocker routing tests plus `tests/runtime/test_evaluation.py` | Demonstration: one deterministic finalized run evaluated across all eight planes; certification: — | Public-source independent reproduction remains V11-PROOF-001. |
| V11-REVIEW-002 | Reviewer independence recorded truthfully | Evaluation | tested | nested citation and hostile review-assurance evidence; distinct capability-event instruction identities; governance-plane evaluation | unknown-independence and same-instruction negative tests plus complete evaluation subject | Demonstration: separated deterministic reviewer execution evidence; certification: — | A named human release approver is recorded separately under V11-APPROVAL-001. |
| V11-STORE-001 | File-backed EPG store | Governed stores | tested | `swos_runtime/stores.py::GovernedJsonStore`; finalizer-bound `governed-stores/epg.jsonl` | `tests/runtime/test_stores.py`; `tests/runtime/test_finalizer.py` | Demonstration: deterministic finalized run; certification: — | Public-source independent proof remains V11-PROOF-001. |
| V11-STORE-002 | File-backed SDL store | Governed stores | tested | `GovernedJsonStore`; finalizer-bound `governed-stores/sdl.jsonl` | store append/reopen and finalized-run tests | Demonstration: deterministic finalized run; certification: — | Human approval evaluation remains V11-APPROVAL-001. |
| V11-STORE-003 | File-backed RPM store with governed writes | Governed stores | tested | `swos_runtime/stores.py::ResearchProgrammeMemoryStore`; finalizer-bound `governed-stores/rpm.jsonl` | RPM provenance, expiry, actor-type and approval negative paths | Demonstration: deterministic empty RPM snapshot binding; certification: — | Durable writes fail closed without source, EPG, SDL and explicit human approval evidence. |
| V11-STORE-004 | Evidence Matrix and Argument Graph governed persistence | Governed stores | tested | shared `GovernedJsonStore`; `governed-stores/evidence_matrix.jsonl`; `governed-stores/argument_graph.jsonl` | five-artifact binding and finalized-run verification | Demonstration: deterministic finalized run; certification: — | Evaluation-plane binding remains V11-EVAL-001. |
| V11-STORE-005 | Hash chaining for EPG, SDL and RPM records | Governed stores | tested | canonical JSON SHA-256 record and previous-hash verification in `GovernedJsonStore` | tamper, missing, reorder, duplicate, chain-link and malformed-record tests | Demonstration: deterministic store chains; certification: — | Verifier rejects any broken chain before returning records. |
| V11-STORE-006 | Correction and supersession preserve prior records | Governed stores | tested | immutable correction/supersession records plus derived active and lifecycle views | correction, inactive-target and prior-record preservation tests | Demonstration: deterministic store lifecycle; certification: — | Prior bytes remain append-only; lifecycle reciprocity is derived and verified. |
| V11-AUDIT-001 | Deterministic complete audit-pack verification | Governed stores | tested | `tools/validate_autonomous_run.py`; manifest, schema, store-chain, exact-artifact and declared-head verification | runtime tamper/manifest/store tests; complete injected run | Demonstration: deterministic complete run; certification: — | Public-source independent reproduction remains V11-PROOF-001. |
| V11-CLI-001 | Working end-to-end SWOS CLI | Reconciliation | tested | `swos_runtime/cli.py::main` exposes `research-write`, work-order and finalization commands; `pyproject.toml` entry point | `tests/runtime/test_cli.py` executes an offline credential-free start command | Demonstration: deterministic CLI work-order creation; certification: — | Public end-to-end CLI proof remains V11-PROOF-001. |
| V11-EVAL-001 | All eight evaluation planes bound to the real runtime path | Evaluation | tested | `swos_runtime/evaluation.py`; thin `autonomous_sut.py` delegation; exact finalized-run subject loading | all eight planes against one deterministic real-runtime subject; missing, mutated, duplicate and partial-plane negative paths | Demonstration: schema-valid eight-plane result bound to one finalized run; certification: — | Public-source independent reproduction remains V11-PROOF-001. |
| V11-EVAL-002 | Complete provenance and zero unresolved blockers at release gate | Evaluation | tested | subject manifest/schema/store/integrity verification; blocker and provenance plane gates; exact-SHA release record | evaluation and release-record positive and tamper/replay tests | Demonstration: deterministic complete run and fail-closed release verifier; certification: — | Exact public release evidence remains V11-REL-001. |
| V11-APPROVAL-001 | Human approval record with separation of duties | Evaluation | tested | runtime evaluation evidence plus one explicit human-owned release record | human approval, rationale, tamper, exact-SHA and cross-run binding tests | Demonstration: deterministic synthetic maintainer identity only; certification: — | The release record is deliberately smaller than the historical approval pack; scholarly store approval rules remain unchanged. |
| V11-PROOF-001 | One independently reproducible public-source project | Public release | demonstrated | `examples/public-proof/project.json`; `swos_runtime/public_proof.py`; real `AutonomousSWOS` path | source-integrity, typed citation relationship, all-plane, replay and tamper tests | Demonstration: two credential-free runs over hash-pinned NIST snapshots produce semantic fingerprint `7773dfa6…`; certification: — | Exact-head PR evidence is required before the demonstration is release evidence. |
| V11-REL-001 | Release evidence and exact-SHA record for the public proof | Public release | tested | `swos_runtime/release_evidence.py`; `swos_runtime/release_record.py`; candidate builder/verifier | complete candidate, exact-SHA and negative-path suite | Demonstration: synthetic maintainer release record; certification: — | The current source-release contract requires one owner record, not package signing. |
| V11-REL-002 | Software Bill of Materials | Public release | tested | deterministic CycloneDX 1.5 generation from package metadata and `requirements-dev.lock` | SBOM content and unlocked-authority rejection tests | Demonstration: deterministic test candidate; certification: — | Final SBOM must be generated from the exact clean release head. |
| V11-REL-003 | Build provenance tied to exact selected SHA | Public release | tested | exact clean-HEAD assertion; build provenance and subject digests | dirty-tree and mismatched-SHA negative tests | Demonstration: isolated temporary repository; certification: — | Final provenance awaits the selected merged SHA. |
| V11-REL-004 | SHA-256 checksums for release artifacts | Public release | tested | deterministic SHA-256 inventory and candidate verification | complete inventory, missing-entry and tamper tests | Demonstration: deterministic test candidate; certification: — | Package signing is an optional future enhancement if SWOS distributes packages or gains multiple maintainers. |
| V11-REL-005 | Conformance report | Public release | tested | candidate conformance report limits claims to passed deterministic profiles | candidate verification tests | Demonstration: deterministic/offline profile only; certification: — | Live-compatible profiles remain unclaimed without manual evidence. |
| V11-REL-006 | Known-limitations statement | Public release | tested | candidate-scoped known-limitations artifact | candidate content and checksum tests | Demonstration: deterministic test candidate; certification: — | Final statement must accompany the exact-head candidate. |

## Verified gap backlog

### Slice 3 — retrieval and citation assurance

1. Implement V11-RERANK-001 as an explicit cross-encoder with deterministic
   ranking fixtures, identity/provenance and fail-closed behavior.
2. Retain and harden V11-RETR-001/002 public adapters with recorded fixture
   provenance and metadata-negative paths.
3. Implement V11-CITE-002 and V11-CITE-003 retraction/licence resolution.
4. Extend V11-CITE-004/005 quotation and support evidence to the canonical typed
   relationships.
5. Add offline CLI coverage for V11-CLI-001 where the retrieval path exposes it.

### Slice 4 — governed stores and audit pack

Implement V11-STORE-001 through V11-STORE-006, then extend V11-AUDIT-001. Reuse
the existing schemas, artifact builders, integrity primitives and deterministic
run fixtures; do not rewrite proved orchestration.

### Slice 5 — evaluation and human approval

Implemented in Spec Kit feature `005`: V11-EVAL-001 and V11-APPROVAL-001, with
V11-EVAL-002 and V11-REVIEW-001/002 reproved against one exact real-runtime run.

### Slice 6 — public proof and release

Implemented in Spec Kit features `006` and `007`: V11-PROOF-001 and deterministic
tooling for V11-REL-001 through V11-REL-006. Exact merged-head evidence and one
real owner release record remain prerequisites for independent `v1.1`
certification; package signing is not a current source-release requirement.

## Reconciliation verdict

PR #41 delivered substantial reusable runtime substrate. Slice 003 closes the
verified cross-encoder, source-owned retraction/licence assurance and offline CLI
test gaps without changing frozen contracts. The next verified implementation
slice is governed durable stores and correction/supersession. The complete
`v1.1` programme is not yet demonstrated or certified.
