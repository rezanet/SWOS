# Implementation Plan: SWOS v2.0 Research Grade

**Branch**: `codex/swos-v2-research-grade-plan` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Approved planning feature at `specs/008-swos-v2-research-grade/`

## Summary

Deliver Research Grade as a versioned, provider-neutral extension from the
`1.0.0` specification and `v1.1` runtime to `v2.0` Research Grade. The release
adds scoped transactional cross-project programme
memory; formal discipline ontologies and structured critique; a trained,
calibrated, abstaining citation-support classifier subordinate to deterministic
admission; source-family and claim-exposure diversity controls; executable PROV
semantic round-trip certification; and rights-aware 2D image/object analysis with
evidence-gated agent promotion.

The work is one milestone, one review, and one merge. It does not silently change
frozen v1.0/v1.1 contracts, claim v3 tenant security, or promote live capabilities
without immutable exact-head evaluation and human approval.

## Technical Context

**Language/Version**: Python 3.11+; JSON Schema; Turtle, JSON-LD, TriG/N-Quads; Markdown

**Primary Dependencies**: Python standard library and existing runtime; optional
pinned `rdflib`/`pyshacl` for ontology build validation; existing optional
Sentence Transformers stack for classifier training; pinned Python `prov` for
in-process interchange; pinned/checksummed ProvToolbox independent release oracle

**Storage**: SQLite local transactional programme store; append-only event chains;
rebuildable projections; immutable JSON/NDJSON audit and exchange artifacts;
large model weights in immutable digest-addressed release storage

**Testing**: `unittest`, current schema/contract/evaluation harnesses, Ruff,
coverage/security/portability checks, deterministic injected classifier/provider
fixtures, property/adversarial/crash/concurrency tests, held-out human-reviewed
benchmarks, independent PROV oracle, exact-head audit-pack verification

**Target Platform**: local/provider-neutral Python runtime on Windows and Linux;
ordinary CI offline and credential-free; optional governed release jobs may use
pinned containers/artifacts and authorized providers

**Project Type**: Python library/CLI with schemas, contracts, governance policies,
discipline packs, evaluation corpus, benchmarks, and release evidence

**Performance Goals**: common indexed RPM query p95 <= 250 ms at 100k items on
the recorded reference runner; feature-spec lookup goal over 10k items; inspected
10k-item import <= 60 seconds; packaged 100-pair citation batch p95 <= 5 seconds;
10k-statement PROV certification <= 60 seconds with bounded memory; deterministic
outputs across repeated runs; zero semantic loss for certified PROV corpus

**Constraints**: fail closed; all public RPM calls scoped; no authenticated-tenancy
claim; no ordinary-CI network/model download/secret/paid call; bounded archive,
RDF, selector, model, and provider resources; core owns verification; rights and
classification ceilings never weaken; exact-head evidence and independent review
required

**Scale/Scope**: 2 namespaces, 4 programmes, 10 projects/programme and 100k-item
RPM benchmark; nine discipline profiles; >=6,000 adjudicated citation pairs at
release floor with >=1,500 locked-test pairs; at least ten locked reviewed
diversity packets per discipline; 1k/10k/100k PROV statement benchmarks; >=60
distinct objects/works, >=96 renditions, and the multimodal gates in research.md

## Constitution Check

*GATE: must pass before implementation and be rechecked after design and before merge.*

| Gate | Design response | Status |
|---|---|---|
| Core policy owns scholarly verification | Classifier, retriever, image provider, and discipline critic return evidence/diagnostics; deterministic core admits or blocks | PASS |
| Fail closed under uncertainty | Missing scope, evidence, rights, ontology, model, calibration, PROV oracle, or selector yields denial/abstention/NOT_RUN, never fabricated pass | PASS |
| Preserve v1 contracts | New v2 schemas/contracts plus explicit dispatcher and compatibility suite; no in-place `$id` redefinition | PASS |
| Provider/host neutrality | Protocols and immutable manifests isolate SQLite, model, RDF, PROV, and image-provider choices | PASS |
| Human authority remains explicit | RPM commits, exceptions, overrides, promotion, and release require separate approval/SDL evidence | PASS |
| Evidence is reproducible | Canonical hashes, exact source SHA, tool/model/oracle/corpus identities, raw predictions, and immutable audit pack | PASS |
| Evaluation exercises production | Fixture-name heuristics removed; all feature evaluators call public production paths | PASS |
| Existing eight planes remain blocking | Full v1.1 and eight-plane regression run is part of exact-head release gate | PASS |
| No scope creep into Product Grade | Logical namespace only; no identity, RBAC, hosted tenant service, production deployment, or autonomous attribution | PASS |
| One cohesive governed delivery | One Spec Kit feature, implementation PR, exact-head review, and merge; workflows feed one audit pack | PASS |

Post-design recheck: PASS. Complexity is justified in the final section and does
not violate the constitutional boundary.

## Project Structure

### Documentation (this feature)

```text
specs/008-swos-v2-research-grade/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── interfaces.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source code and governed artifacts (repository root)

```text
swos_runtime/
├── research_memory.py
├── programme_store.py
├── rpm_exchange.py
├── discipline_ontology.py
├── discipline_critique.py
├── citation_classifier.py
├── citation_calibration.py
├── source_diversity.py
├── prov_model.py
├── prov_interop.py
├── prov_validation.py
├── media.py
├── image_analysis.py
├── image_analysis_openai.py
├── models.py
├── broker.py
├── orchestrator.py
├── finalizer.py
├── work_orders.py
└── evaluation.py

schemas/research-grade/
├── project-scope.schema.json
├── rpm-2.0.schema.json
├── rpm-exchange.schema.json
├── discipline-critique.schema.json
├── citation-support-decision.schema.json
├── source-diversity-report.schema.json
├── epg-2.0.schema.json
├── prov-roundtrip-report.schema.json
├── object-record.schema.json
├── media-asset.schema.json
├── object-inspection.schema.json
├── accessibility-record.schema.json
├── visual-observation.schema.json
├── cross-modal-support.schema.json
├── image-analysis-result.schema.json
├── specialist-agent.schema.json
├── capability-promotion.schema.json
└── research-grade-audit-pack.schema.json

contracts/capability-contract/capabilities-v2.json
contracts/stage-instruction/stage-instructions-v2.json
governance/policies/
├── research-programme-memory-v2.policy.json
├── rpm-exchange.policy.json
├── source-diversity.policy.json
├── media-rights.policy.json
└── research-grade-promotion.policy.json

discipline-packs/
├── manifest-v2.json
├── ontology/
│   ├── swos-discipline-ontology.ttl
│   ├── swos-discipline-shapes.ttl
│   └── context.jsonld
├── compiled/v2/
└── <pack>/ontology.ttl

benchmark/
├── rpm/
├── citation-support/
├── source-diversity/
└── provenance/
models/citation-support/<version>/
agents/research-grade/
├── art-history.agent.json
└── art-criticism.agent.json
evals/fixtures/
├── provenance/
├── source-diversity/
├── discipline-critique/
└── multimodal/
tools/
├── rpm.py
├── compile_discipline_ontologies.py
├── build_citation_dataset.py
├── train_citation_classifier.py
├── calibrate_citation_classifier.py
├── evaluate_citation_classifier.py
├── run_source_diversity_benchmark.py
├── certify_prov_roundtrip.py
├── run_rpm_benchmark.py
├── run_multimodal_evals.py
└── assemble_research_grade_audit_pack.py
tests/runtime/
tests/fixtures/research-grade/
.github/workflows/
├── research-grade-ci.yml
├── citation-model-evaluation.yml
├── prov-certification.yml
└── multimodal-evaluation.yml
```

**Structure Decision**: extend the existing single Python runtime and governed
artifact layout. Keep concerns in small modules and parallel v2 contracts. No new
service, UI, deployment repository, or competing canonical evidence source.

## Delivery Strategy and Dependency Graph

```text
P0 planning/review
  -> P1 compatibility + audit foundations
      -> P2 RPM (US1)
      -> P3 ontology core (US2)
           -> P4 discipline critique (US2)
           -> P5 diversity requirements (US3)
           -> P6 classifier ontology binding (US3)
      -> P7 PROV interchange/certification (US4)
           -> RPM exchange certification
      -> P8 object/media/rights/selectors (US5)
           -> image provider + cross-modal support
           -> critique integration + promotion
  -> P9 full eight-plane integration, benchmarks, audit pack
  -> P10 exact-head CI + independent review + merge decision
```

US1 and ontology authoring may start after P1. PROV core and media entity work may
also proceed after P1 in separate files. Classifier calibration, diversity policy,
discipline critique, and multimodal promotion depend on the formal ontology.
RPM portable exchange cannot certify until EPG v2/PROV validation exists. The
final release candidate waits for every story and cross-story integration gate.

## Phase 0: Planning and Approval

Deliver this complete feature set—spec, research decisions, data model, contracts,
implementation plan, tasks, quality checklist—and obtain review of the planning
PR. Implementation must use this feature directory as the sole planning
authority. Any material boundary/threshold change updates all affected artifacts
and receives review before code relies on it.

**Exit gate**: no clarification markers; Spec Kit validator green; requirement,
story, and task coverage complete; planning PR exact-head reviewed.

## Phase 1: Compatibility and Shared Foundations

1. Snapshot hashes and behavior of frozen v1.0 schemas/contracts and v1.1 inputs.
2. Add explicit version dispatch and parallel v2 contract/schema skeletons.
3. Add canonicalization, typed failures, resource limits, policy/result envelopes,
   and exact evaluation-subject extensions.
4. Add release audit-pack schema, assembler, verifier, and artifact provenance.
5. Replace heuristic fixture-name evaluation with injected production interfaces.
6. Add dependency extras/locks and licence/digest manifests; keep ordinary CI
   offline.

**Exit gate**: all existing suites unchanged; v1 byte/behavior compatibility;
unknown versions fail closed; empty/mismatched audit packs fail; no network or
credential access in ordinary CI.

## Phase 2: US1 — Cross-project Research Programme Memory

1. Define v2 scope, binding, candidate, assessment, event, projection, receipt,
   exchange, inspection, and policy schemas.
2. Build the SQLite repository with migrations, scoped hash chains, foreign keys,
   atomic event/projection transactions, preflight, bounded locking, integrity
   verification, and deterministic rebuild.
3. Build the authoritative v2 RPM policy plus registration and staged
   evidence-bound operation service. Route every project binding, write,
   lifecycle, deletion, expiry, and exceptional-read authorization through one
   assessed/approved commit protocol; resolve EPG/SDL and revalidate at commit.
4. Build classification/expiry-aware governed reads and EPG read receipts.
5. Build correction, supersession, contradiction, confirmation, expiry, deletion,
   and review-mode lifecycle semantics.
6. Build safe export, inspect, commit, redaction, collision, idempotence, path, and
   resource-limit behavior.
7. Connect finalizer/work-order run snapshots to real scoped RPM, while preserving
   v1.1 compatibility.
8. Add operator CLI, benchmark corpus, concurrency/crash/tamper/security tests,
   and immutable benchmark report.

**Exit gate**: three-project exchange suite; isolation and TOCTOU adversarial suite;
2,000 concurrent writes with no loss/duplication; crash all-or-nothing; projection
rebuild equivalence; hostile import rejection; documented logical-deletion and
logical-namespace limitations.

## Phase 3: US2 — Formal Ontologies and Discipline Critique

1. Define the core SKOS/OWL vocabulary, SHACL shapes, JSON-LD context, manifest,
   compatibility/deprecation policy, and deterministic compiler.
2. Author the required ADR, reversible migration and one-minor-release
   deprecation-warning path, then map
   the nine supported disciplines exactly once, explicitly retain
   `enterprise_reporting` only in frozen v1 compatibility, reject it in the v2
   scholarly profile, and create one versioned ontology module per supported pack.
3. Validate required labels, identifiers, methods, evidence types, proof standards,
   criteria, failure modes, source roles, diversity dimensions, weights, and cycles.
4. Prove Turtle/JSON-LD graph isomorphism and compile byte-stable runtime JSON.
5. Bind research plans, claims, Evidence Matrix rows, critiques, source diversity,
   and evaluation subjects to ontology IRIs and digests.
6. Implement per-discipline structured critique and disagreement-preserving
   aggregation; no universal-score shortcut.
7. Create reviewed positive/negative/boundary/cross-discipline fixtures for every
   pack and produce agreement/adjudication evidence.

**Exit gate**: all enum values map exactly once; all packs and malformed fixtures
behave as specified; compiled outputs repeat byte-for-byte; every normative pack
rule is machine-traced; no unknown-version fallback; all discipline critique
blocking fixtures detected.

## Phase 4: US3 — Citation Classification and Source Diversity

### Citation-support workstream

1. Add pair, annotation, dataset, model, calibration, decision, and evaluation
   schemas plus provider-neutral protocols and deterministic fake backend.
2. Write annotation guidelines and execute the governed corpus-production process
   to create, double-annotate, adjudicate, approve, checksum, and freeze the
   licensed/source-provenanced group-split train/calibration/locked/OOD datasets.
3. Train candidates using frozen configurations; select without locked-test use.
4. Fit temperature scaling on calibration only; freeze selective thresholds and
   bind model/dataset/ontology/label order.
5. Verify artifact digest/licence/model card and implement deterministic batched
   inference, OOD/invalid-artifact abstention, and immutable decisions.
6. Integrate behind broker and finalizer while retaining all deterministic
   prechecks and core-owned admission.
7. Replace citation heuristic fixtures with production-bound tests and publish raw
   locked predictions, confidence intervals, slice metrics, and limitations.

### Diversity workstream

1. Add pre-retrieval requirement declaration and metadata provenance states.
2. Canonicalize source families across URLs, editions, mirrors, preprint/published
   variants, and retrieval channels.
3. Compute per-dimension source-count and claim-exposure concentration, effective
   number, balance, required coverage, and unknownness; gate on worst case. Keep
   the frozen v1 provider scalar non-gating and enforce a separately versioned v2
   geometric composite >= 0.50 without allowing it to mask a failed dimension.
4. Implement family-count gates, counter-position requirement, research expansion,
   explicit narrow-corpus exception, and final limitation propagation.
5. Replace provider-count metric and heuristic fixtures with production-bound
   benchmark packets across all disciplines.

**Exit gate**: annotation/licence/leakage/agreement gates; classifier safety,
calibration, abstention, coverage, and slice thresholds; 100% critical adversarial
detection; diversity duplicate/provider/unknown invariants; held-out diversity
recall/false-block thresholds; no provider judgment can auto-admit evidence.

## Phase 5: US4 — PROV Round-trip Certification

1. Define EPG v2, SWOS PROV extension vocabulary/shapes, supported-format profile,
   resource limits, report/certificate schema, and namespace policy.
2. Implement the canonical internal model, v1-to-v2 compatibility mapping, and
   lossless EPG converters.
3. Implement parsers/serializers for PROV-JSON, PROV-N, and PROV-O/TriG.
4. Implement syntax/profile, PROV-CONSTRAINTS, SHACL, bundle, identifier,
   qualified-relation, typed-value, language-tag, and extension validation.
5. Implement semantic normal form plus JCS, RDFC-1.0, and semantic PROV-N
   fingerprints under resource limits.
6. Run the full conversion matrix, invalid/adversarial fixtures, stable second
   round trips, and large graph/resource benchmarks.
7. Pin and run independent ProvToolbox/conformance oracle; preserve raw outputs,
   versions/digests, implementation agreement, and limitations.
8. Integrate certified provenance into RPM exchange, work-order host bundles,
   finalization, evaluation subject, and audit pack.

**Exit gate**: 100% mandatory corpus and end-to-end work-order path semantically
equivalent; zero lost assertions; every advertised format independently accepted;
hostile cases fail bounded; certificate exact-head complete; no W3C certification
overclaim.

## Phase 6: US5 — Justified Multimodal and Image/Object Analysis

1. Add object, media asset, inspection activity, structured accessibility,
   purpose-rights, selector, observation, interpretation, cross-modal, specialist
   agent, provider result, promotion, and corpus schemas/policies.
2. Implement ingest validation, object/asset distinction, digest/derivative
   lineage, IIIF 3 parsing, selector normalization, accessibility, and export
   redaction.
3. Implement bounded provider-neutral 2D image analysis with deterministic fake,
   one real opt-in OpenAI adapter, and explicit
   complete/partial/insufficient/denied/error behavior.
4. Implement observation-versus-interpretation separation, weakest-leg cross-modal
   support, multi-view limitation, attribution/originality guardrails, and EPG.
5. Integrate art-history then art-criticism critique in staged pack-assisted mode.
6. Build the governed `DATA-LICENCE.md`, at least 60 distinct objects/works and 96
   renditions, region/cross-modal/discipline/adversarial cases, annotation
   guidelines, adjudication, accessibility, and stability evaluation.
7. Implement versioned specialist-agent contracts, least-privilege tools,
   role-separated routes, and executable pack fallback; then implement default-off
   paired promotion assessment/commit/rollback and prove >=0.08 improvement, a
   lower 95% confidence bound above zero, successful live evidence, and all
   safety/regression gates before enablement.

**Exit gate**: zero unsafe rights/hash/lineage/attribution passes; selector,
grounding, cross-modal, accessibility, critique, agreement, determinism, and
regression thresholds; live evidence where required; promotion artifact bound to
exact candidate or capability remains disabled.

## Phase 7: Cross-story Integration and Release Candidate

1. Run all eight existing planes plus new Research Grade evaluators through
   production paths and remove remaining heuristic shortcuts.
2. Run compatibility, schema, ontology, runtime, RPM, classifier, diversity,
   critique, PROV, multimodal, security, portability, lint, coverage, benchmark,
   and deterministic stability suites.
3. Verify classification, rights, evidence, and ontology identities survive RPM,
   Evidence Matrix, EPG, PROV, critique, work-order export, and public proof.
4. Assemble the immutable audit pack and verify every FR/SC artifact pointer.
5. Freeze the head; obtain all hosted exact-head checks and independent review;
   resolve every actionable thread and rerun invalidated evidence.

**No-merge gate**: any failing/missing/NOT_RUN mandatory gate; unreviewed head;
unresolved blocker/thread; silent v1 drift; hidden model/media/oracle dependency;
or absent limitations prevents merge. Deployment/production remain separately
authorized and are not part of this plan.

## Testing Strategy

### Test order

For every task slice: write the failing contract/unit/adversarial test, verify the
failure is for the intended behavior, implement the smallest production path,
then run focused and relevant regression suites. Fixture evaluators must invoke
that path. Tests that merely validate expected fixture labels are prohibited.

### Required layers

- schema/contract/example and version-dispatch tests;
- unit/property tests for canonicalization, metrics, selectors, state machines;
- repository transaction, concurrency, crash, corruption, and migration tests;
- cross-module integration from planning through finalization/export;
- adversarial poisoning, traversal, collision, leakage, rights, OOD, malformed
  model/RDF/media, resource-exhaustion, and semantic-loss tests;
- human-reviewed locked benchmarks with agreement and confidence intervals;
- exact-head live/release workflows for model, oracle, and multimodal provider;
- full v1.1/eight-plane regressions and reproducibility across repeated runs.

### Benchmark gates

Benchmark reports are generated artifacts with runner CPU/OS/Python/dependency,
corpus/config/source SHA, raw measurements, summary calculation, thresholds, and
limitations. Prose-only performance claims do not satisfy a gate.

## Security, Privacy, Rights, and Failure Boundaries

- No secrets or raw restricted data in config, logs, fixtures, audit packs, PRs,
  or memory exchange.
- SQLite logical deletion does not claim backup or physical-media erasure.
- Namespace keys prevent accidental mixing but do not authenticate users/tenants.
- Model and dataset licences must authorize their exact use and distribution.
- Media rights are action-specific; unknown is denied; exports retain redaction
  evidence without barred bytes.
- Archive, RDF canonicalization, SVG selectors, model input/batches, images, and
  provider calls have explicit limits/timeouts.
- Cross-scope errors do not disclose whether another scope contains an ID.
- Human identity is asserted evidence in v2, not authenticated product identity.
- Any uncertainty about support, diversity, provenance, rights, object identity,
  or attribution results in abstention, review, limitation, or rejection.

## Requirement Traceability

| Requirements | Design location | Primary implementation/evidence |
|---|---|---|
| FR-001, FR-002, FR-003, FR-004, FR-005 | Phase 2; data model §1; contracts §2 | `research_memory.py`, `programme_store.py`, `rpm_exchange.py`; scoped lifecycle/exchange suites |
| FR-006, FR-007, FR-008, FR-009, FR-010 | Phase 3; research R2; data model §2 | ontology sources/shapes/compiler/manifest; pack and isomorphism reports |
| FR-011, FR-012 | Phase 3; research R3; contracts §3 | `discipline_critique.py`; nine-pack reviewed fixture report |
| FR-013, FR-014, FR-015, FR-016, FR-017 | Phase 4 citation workstream; research R4; contracts §4 | classifier/calibration/dataset/model manifests; locked predictions and metrics |
| FR-018, FR-019, FR-020, FR-021 | Phase 4 diversity workstream; research R5; contracts §5 | `source_diversity.py`, policy/benchmark; expansion and exception evidence |
| FR-022, FR-023, FR-024, FR-025, FR-026 | Phase 5; research R6; contracts §6 | EPG v2/interchange/validation/certifier; oracle/corpus certificates |
| FR-027, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033 | Phase 6; research R7; data model §6; contracts §7 | media/image modules, rights/promotion policies, corpus/adjudication report |
| FR-034–FR-035 | Phases 1–7; Testing Strategy | test-first task ordering; full exact-head eight-plane report |
| FR-036 | Phase 1 compatibility shell | frozen artifact digest and v1.1 behavior regression report |
| FR-037 | Phases 2–7 audit bindings | EPG/SDL, model, rights, review, and audit-pack manifests |
| FR-038 | Phase 7 release gate | exact-head CI, immutable audit pack, independent review |
| FR-039 | Technical Context; contracts §§2–8 | protocols, injected adapters, offline CI and portability results |
| FR-040 | Constitution and Boundaries | scope tests and explicit v3 non-goals/limitations |
| SC-001 | Phase 2 exit | three-project snapshot/delta/collision/contradiction/expiry suite |
| SC-002 | Phase 3 exit | all ontology graphs/shapes/isomorphism and negative fixtures |
| SC-003–SC-004 | Phase 4 citation exit | corpus manifest/agreement and locked classifier report |
| SC-005 | Phase 4 diversity exit | metadata completeness and metric benchmark report |
| SC-006 | Phase 3 exit | nine-discipline positive/adversarial critique report |
| SC-007 | Phase 5 exit | full PROV matrix and end-to-end work-order certificate |
| SC-008–SC-009 | Phase 6 exit | rights-cleared corpus, multimodal results, promotion decision/default-off proof |
| SC-010 | Phase 7 | exact-head offline CI/eight-plane/compatibility report |
| SC-011 | Phase 7 | one verified audit pack with requirement index and limitations |
| SC-012 | Phases 2 and 5 benchmarks | recorded reference-runner RPM/PROV performance reports |

## Reviewed PR Strategy

The implementation PR must:

1. link this feature and identify approved plan/spec digests;
2. contain the complete cohesive v2 diff, not partial production enablement;
3. identify generated, trained, third-party, and human-reviewed artifacts;
4. list exact test/workflow commands and immutable evidence links;
5. name all no-merge/no-production gates and limitations;
6. freeze a release-candidate head before final external review;
7. satisfy repository role quorums on that exact head: ADR plus two maintainers
   and a deprecation plan for schema changes; one maintainer plus one discipline
   steward for packs/ontologies; two maintainers plus the evaluation owner for
   fixtures; one maintainer plus the portability owner for the real provider
   adapter; and one maintainer plus the evaluation owner for reviewer criteria;
   record approvals as immutable evidence, resolve every thread, and rerun
   affected evidence after any change;
8. merge only after green exact-head CI and explicit owner approval.

The planning PR itself receives review before implementation starts. A bot quota,
unavailable reviewer, missing workflow, or stale review remains a real blocker;
the builder must not report “reviewed” without current evidence.

## Complexity Tracking

| Complexity | Why needed | Simpler alternative rejected because |
|---|---|---|
| SQLite event repository plus projections | Atomic scoped cross-project writes, indexed reads, crash/concurrency integrity, lifecycle and safe deletion | Extending JSONL alone cannot provide atomic cross-artifact validation or multi-process safety |
| SKOS + small OWL + SHACL + compiled JSON | Stable semantics, closed validation, mappings, and deterministic runtime | Prose/JSON taxonomy alone cannot validate graph meaning; OWL alone cannot close completeness |
| Trained classifier plus calibration/abstention | Measured support with governed safety/coverage bounds | Prompt verdict or argmax cannot establish reproducible admission risk |
| Multi-dimensional diversity reports | Prevent duplicate/provider/token-citation gaming and expose applicability/unknownness | One scalar hides concentration and can manufacture balance |
| Internal and independent PROV implementations | Certification must detect converter-specific loss | Self-round-trip can reproduce the same bug on both legs |
| Separate object/media/observation/interpretation models | Rights, identity, capture, visible evidence, and inference have different provenance | One image record launders asset/object identity and observation/inference |

These are bounded within the existing Python/artifact architecture. No new hosted
service, UI, deployment plane, or product identity system is introduced.
