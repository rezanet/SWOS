# Tasks: SWOS v2.0 Research Grade

**Input**: `specs/008-swos-v2-research-grade/{spec,plan,research,data-model,quickstart}.md` and `contracts/interfaces.md`

**Tests**: Mandatory and test-first. For each test task, demonstrate the intended
failure before its paired implementation task. Ordinary CI stays offline.

**Task rule**: Every completed task must leave an exact-path artifact, test, or
recorded evidence. A checked box means the task and its focused tests pass at the
then-current head; it is not a merge claim.

## Phase 1: Setup and frozen compatibility baseline

**Purpose**: establish the governed base and parallel v2 namespace before behavior changes.

- [ ] T001 Record frozen v1.0 schema, contract, fixture, and v1.1 behavior digests in `tests/fixtures/research-grade/v1-compatibility-manifest.json`
- [ ] T002 [P] Add negative tests proving v1 `$id` semantics cannot be silently changed in `tests/runtime/test_research_grade_compatibility.py`
- [ ] T003 [P] Add v2 schema identifier and version-dispatch contract tests in `tests/runtime/test_research_grade_schemas.py`
- [ ] T004 Add explicit v1/v2 version routing with unknown-version denial in `swos_runtime/models.py`
- [ ] T005 Create parallel Research Grade schema envelopes and implement their executable example validator in `tools/validate_contract_examples.py`; make `tools/validate_schemas.py` discover the v2 schema directory
- [ ] T006 [P] Add `capabilities-v2.json` without editing v1 capability semantics in `contracts/capability-contract/capabilities-v2.json`
- [ ] T007 [P] Add `stage-instructions-v2.json` without editing v1 stage semantics in `contracts/stage-instruction/stage-instructions-v2.json`
- [ ] T008 Add byte/behavior compatibility and example validation to `.github/workflows/research-grade-ci.yml`
- [ ] T009 Run the compatibility suite and record base results in `artifacts/research-grade/compatibility-baseline.json`

**Checkpoint**: existing v1.0/v1.1 behavior is green and new version dispatch fails closed.

## Phase 2: Foundational governance and audit substrate

**Purpose**: shared types, policies, resource bounds, deterministic adapters, and audit evidence that block every story.

- [ ] T010 [P] Write canonical JSON, digest, identifier, timestamp, and resource-limit tests in `tests/runtime/test_research_grade_foundations.py`
- [ ] T011 [P] Write audit-pack missing/extra/tampered/head-mismatch tests in `tests/runtime/test_research_grade_audit_pack.py`
- [ ] T012 [P] Write tests proving fixture evaluators invoke injected production interfaces in `tests/runtime/test_research_grade_evaluation.py`
- [ ] T013 Implement shared canonicalization, typed status/error codes, and resource-limit models in `swos_runtime/models.py`
- [ ] T014 [P] Add authoritative v2 RPM operation, RPM exchange, source diversity, media rights, and promotion policies in `governance/policies/research-programme-memory-v2.policy.json`, `governance/policies/rpm-exchange.policy.json`, `governance/policies/source-diversity.policy.json`, `governance/policies/media-rights.policy.json`, and `governance/policies/research-grade-promotion.policy.json`; document the frozen v1 memory-policy relationship
- [ ] T015 Add exact artifact identities to the evaluation subject in `swos_runtime/evaluation.py`
- [ ] T016 Add Research Grade audit-pack schema and example in `schemas/research-grade/research-grade-audit-pack.schema.json` and `examples/research-grade/audit-pack.json`
- [ ] T017 Implement audit-pack assembly and strict verification in `tools/assemble_research_grade_audit_pack.py`
- [ ] T018 Route every existing and new fixture evaluator through injected production interfaces, remove fixture-name/expected-label pass shortcuts, and add production adapters in `evals/harness/run_evals.py`
- [ ] T019 Add optional ontology, training, and PROV dependency groups with licences and hashes in `config/research-grade-dependencies.md`; update `pyproject.toml` and `requirements-dev.lock` from that manifest
- [ ] T020 Verify ordinary CI performs no model download, network request, credential read, or paid call, and add the bounded safety-mutation harness/report in `tests/runtime/test_research_grade_offline.py` and `tools/run_mutation_checks.py`

**Checkpoint**: shared foundations, policies, and audit verifier are green; all existing suites remain green.

## Phase 3: User Story 1 — Continue governed research across projects (P1)

**Goal**: transactional, explicitly scoped, evidence-bound programme memory with safe exchange.

**Independent test**: register three projects in one programme, commit governed
facts, exchange snapshot/delta bundles, exercise collisions/contradictions/expiry,
and prove a different scope cannot observe or influence them.

### US1 tests first

- [ ] T021 [P] [US1] Add schema/contract tests for scope, project binding, authoritative policy version/digest, RPM v2, lifecycle, programme closure, exchange, inspection, and read receipt in `tests/runtime/test_research_memory_contracts.py`
- [ ] T022 [P] [US1] Add repository migration, transaction, chain, projection, corruption, and rebuild tests in `tests/runtime/test_programme_store.py`
- [ ] T023 [P] [US1] Add missing/unregistered/cross-namespace/cross-programme/project-visibility isolation tests in `tests/runtime/test_research_memory_isolation.py`
- [ ] T024 [P] [US1] Add EPG/SDL resolution, operation-hash approval, stale-policy, expired-assessment, restricted-data, unauthorised-mutation, and commit-time TOCTOU tests for every binding/write/correct/supersede/contradiction/expiry/delete/close/exception transition in `tests/runtime/test_research_memory_writes.py`
- [ ] T025 [P] [US1] Add correction, supersession, contradiction, confirmation, exact-expiry, project retirement/unbinding, programme closure with historical-record/release preservation, exceptional-read, and deletion tests in `tests/runtime/test_research_memory_lifecycle.py`
- [ ] T026 [P] [US1] Add idempotence, collision, mapping, checksum, redaction, zip-slip, link, duplicate-path, and decompression-limit tests in `tests/runtime/test_rpm_exchange.py`
- [ ] T027 [P] [US1] Add 8-process/2,000-write, lock-timeout, crash-injection, and all-or-nothing tests in `tests/runtime/test_programme_store_concurrency.py`

### US1 implementation

- [ ] T028 [P] [US1] Define `ResearchScope`, bindings, candidates, assessments, events, projections, reads, and approvals in `swos_runtime/research_memory.py`
- [ ] T029 [P] [US1] Add project-scope, RPM operation/policy, lifecycle, exchange, and receipt schemas in `schemas/research-grade/project-scope.schema.json`, `schemas/research-grade/rpm-policy.schema.json`, `schemas/research-grade/rpm-2.0.schema.json`, and `schemas/research-grade/rpm-exchange.schema.json`
- [ ] T030 [US1] Implement SQLite initialization, migrations, preflight, per-programme chain, transactions, integrity checks, and projection rebuild in `swos_runtime/programme_store.py`
- [ ] T031 [US1] Implement explicit project registration and visibility enforcement in `swos_runtime/research_memory.py`
- [ ] T032 [US1] Implement one propose/assess/approve/commit service for project binding, programme closure, write, correction, supersession, contradiction, expiry, deletion, and exceptional-read operations with exact EPG, SDL, policy, target-head, `as_of`, classification, rights, and expiry revalidation in `swos_runtime/research_memory.py`
- [ ] T033 [US1] Implement classification/expiry-aware governed queries and EPG read receipts in `swos_runtime/research_memory.py`
- [ ] T034 [US1] Implement immutable confirmation, correction, supersession, contradiction, expiry, programme closure, project retirement/unbinding, and logical-deletion transitions exclusively through the assessed operation service in `swos_runtime/research_memory.py`
- [ ] T035 [US1] Implement bounded export, inspect-import, atomic commit, redaction, origin preservation, and deterministic diff in `swos_runtime/rpm_exchange.py`
- [ ] T036 [US1] Add v1 `GovernedJsonStore` compatibility import/export adapters without changing v1 behavior in `swos_runtime/stores.py`
- [ ] T037 [US1] Replace the hard-coded empty RPM snapshot with scoped service integration in `swos_runtime/finalizer.py`
- [ ] T038 [US1] Bind work-order RPM reads/writes/exchange to exact run and EPG evidence in `swos_runtime/work_orders.py`
- [ ] T039 [US1] Implement dry-run-first init/register/close-programme/assess-operation/commit-operation/verify/expire/export/inspect-import/commit-import/rebuild commands with explicit `--approval` inputs wherever required in `tools/rpm.py`
- [ ] T040 [US1] Add deterministic three-project snapshot/delta/duplicate/fork/collision/contradiction/expiry/correction/retirement/programme-closure/replay fixtures in `evals/fixtures/research-memory/`
- [ ] T041 [US1] Add the SC-012 10k-active-item benchmark generator/runner with a recorded reference-runner schema and p95 <= 250 ms acceptance in `benchmark/rpm/manifest.json` and `tools/run_rpm_benchmark.py`
- [ ] T042 [US1] Document logical namespace, SQLite filesystem, logical deletion, backup, and recovery limitations in `docs/architecture/research-grade-memory.md`

**Checkpoint**: SC-001 and RPM safety/benchmark gates pass; no public unscoped API exists.

## Phase 4: User Story 2 — Apply formal discipline knowledge and critique (P1)

**Goal**: machine-validatable discipline semantics and evidence-linked critique without universal-score collapse.

**Independent test**: compile and load every discipline graph byte-identically,
reject malformed packs, then produce criterion-level positive/adversarial critique
for every pack with disagreement preserved.

### US2 tests first

- [ ] T043 [P] [US2] Add SHACL, graph-isomorphism, stable-IRI, duplicate, dangling, cycle, weight, enum/pack coverage, v1 warning-window, v2 rejection, reversible migration, and rollback tests in `tests/runtime/test_discipline_ontology.py`
- [ ] T044 [P] [US2] Add deterministic compile, digest, unknown-version, deprecation, and no-fallback tests in `tests/runtime/test_discipline_ontology_compiler.py`
- [ ] T045 [P] [US2] Add structured criterion, mandatory failure, disagreement, evidence-link, and aggregation tests in `tests/runtime/test_discipline_critique.py`
- [ ] T046 [P] [US2] Add positive, negative, boundary, and cross-discipline fixture contract tests for every pack in `tests/runtime/test_discipline_critique_fixtures.py`

### US2 implementation

- [ ] T047 [P] [US2] Author core SKOS/OWL vocabulary, SHACL shapes, and JSON-LD context in `discipline-packs/ontology/swos-discipline-ontology.ttl`, `discipline-packs/ontology/swos-discipline-shapes.ttl`, and `discipline-packs/ontology/context.jsonld`
- [ ] T048 [US2] Author the narrowed-enum ADR, reversible migration, and one-minor-release deprecation-warning period in `adr/ADR-0012-research-grade-discipline-profile.md` and `tools/migrations/migrate_discipline_profile_v2.py`; map nine supported disciplines exactly once while frozen v1 retains `enterprise_reporting` and v2 rejects it without fallback in `discipline-packs/manifest-v2.json`
- [ ] T049 [P] [US2] Author versioned method/evidence/proof/criterion/failure/source-role/diversity mappings in each `discipline-packs/<pack>/ontology.ttl`
- [ ] T050 [US2] Implement offline registry loading, version/deprecation checks, and compiled profile lookup in `swos_runtime/discipline_ontology.py`
- [ ] T051 [US2] Implement validated Turtle-to-JSON-LD-to-byte-stable-JSON compilation with source/shape/tool digests in `tools/compile_discipline_ontologies.py`
- [ ] T052 [US2] Bind research plan, Evidence Matrix rows, and evaluation subject to discipline/method/criterion IRIs and ontology digests in `swos_runtime/orchestrator.py`, `swos_runtime/finalizer.py`, and `swos_runtime/evaluation.py`
- [ ] T053 [US2] Implement criterion-level discipline critique and disagreement-preserving aggregation in `swos_runtime/discipline_critique.py`
- [ ] T054 [US2] Wire critique through broker, finalizer, EPG, and SDL without allowing provider-owned admission in `swos_runtime/broker.py` and `swos_runtime/finalizer.py`
- [ ] T055 [P] [US2] Create reviewed fixtures and adjudication records for all supported packs, including art criticism, in `evals/fixtures/discipline-critique/`, with at least one acceptance fixture per pack also published under `evals/fixtures/golden/`
- [ ] T056 [US2] Add ontology and critique production-path scoring to `swos_runtime/evaluation.py` and `evals/metrics.md`
- [ ] T057 [US2] Document compatibility, external mappings, deprecation, and pack-authoring rules in `discipline-packs/README.md`

**Checkpoint**: SC-002 and SC-006 pass; missing/invalid ontology blocks before planning.

## Phase 5: User Story 3 — Measure citation support and source diversity (P1)

**Goal**: calibrated trained support decisions and non-gameable evidence-base diversity under core-owned admission.

**Independent test**: run the locked classifier and diversity corpus through
production paths, satisfy all safety/calibration/slice/diversity gates, and prove
duplicates/provider renaming/unknown metadata cannot improve admission.

### US3 tests first

- [ ] T058 [P] [US3] Add classifier schema, probability, ordering, batching, digest, label-order, OOD, corrupt-artifact, and abstention tests in `tests/runtime/test_citation_classifier.py`
- [ ] T059 [P] [US3] Add calibration fit isolation, ECE, threshold, immutable binding, confidence-bound, and coverage tests in `tests/runtime/test_citation_calibration.py`
- [ ] T060 [P] [US3] Add tests proving only deterministic-precheck plus direct/non-abstained classifier output is admission-eligible in `tests/runtime/test_citation_admission.py`
- [ ] T061 [P] [US3] Add source-family identity, ordering, duplicate edition/mirror/preprint/provider invariance, unknownness, HHI/effective-number, exposure, and exception tests in `tests/runtime/test_source_diversity.py`
- [ ] T062 [P] [US3] Add bounded research-expansion, required-strata, counter-position, and final-limitation integration tests in `tests/runtime/test_research_expansion.py`
- [ ] T063 [P] [US3] Add leakage, licence, manifest, group-split, agreement, locked-test isolation, and model-card tests in `tests/runtime/test_citation_dataset.py`

### US3 citation implementation

- [ ] T064 [P] [US3] Add citation pair/decision and model/calibration manifest schemas in `schemas/research-grade/citation-support-decision.schema.json` and `schemas/research-grade/model-artifact.schema.json`
- [ ] T065 [US3] Implement verified model loading, deterministic batching, five semantic support classes, OOD detection, and fail-closed abstention while keeping laundering/invalid cases as core rule rejections in `swos_runtime/citation_classifier.py`
- [ ] T066 [US3] Implement temperature scaling, selective thresholds, metric confidence intervals, and immutable binding in `swos_runtime/citation_calibration.py`
- [ ] T067 [US3] Preserve deterministic prechecks and integrate trained decisions behind `CapabilityBroker.citation_support_audit` in `swos_runtime/broker.py`
- [ ] T068 [US3] Restrict final verification to core eligibility and store immutable classifier evidence/overrides in `swos_runtime/finalizer.py`
- [ ] T069 [P] [US3] Write annotation guidelines, dataset card, source/licence manifest, split policy, and adjudication protocol in `benchmark/citation-support/`
- [ ] T070 [US3] Implement and execute the bounded corpus workflow to acquire permitted pairs, double-annotate, adjudicate, approve, leakage-check, checksum, and freeze actual train/calibration/locked/OOD splits and `DATA-LICENCE.md` in `benchmark/citation-support/manifest.json` using `tools/build_citation_dataset.py`
- [ ] T071 [US3] Implement immutable training and model-card/artifact-manifest generation in `tools/train_citation_classifier.py`
- [ ] T072 [US3] Implement calibration-only fitting and artifact generation in `tools/calibrate_citation_classifier.py`
- [ ] T073 [US3] Implement locked evaluation, raw predictions, slice metrics, confidence intervals, gate report, and reproducible packaged 100-pair citation latency measurement proving p95 <=5 seconds on the recorded reference runner in `tools/evaluate_citation_classifier.py`
- [ ] T074 [US3] Add pinned release-model workflow and immutable outputs in `.github/workflows/citation-model-evaluation.yml`

### US3 diversity implementation

- [ ] T075 [P] [US3] Add research-plan v2 diversity requirements and report schemas, requiring applicable dimensions, required strata, thresholds, and an ontology-linked `not_applicable` rationale before retrieval, in `schemas/research-grade/research-plan-2.0.schema.json` and `schemas/research-grade/source-diversity-report.schema.json`
- [ ] T076 [US3] Implement canonical source-family identity and venue/owner/region/language/period/method/source-type/access-mode/stance metadata evidence states in `swos_runtime/source_diversity.py`
- [ ] T077 [US3] Implement per-dimension source-count/exposure metrics, worst-case gates, separately versioned v2 geometric composite threshold 0.50, non-gating frozen v1 provider scalar, family-count statuses, counter-position checks, and exceptions in `swos_runtime/source_diversity.py`
- [ ] T078 [US3] Replace provider-count diversity and propagate expansion/review/limitations through `swos_runtime/orchestrator.py` and `swos_runtime/finalizer.py`
- [ ] T079 [P] [US3] Create separate tuning packets plus at least ten locked human-reviewed balanced/concentrated/sparse/narrow/multilingual/historical/method-monoculture/duplicate/fake-diversity packets per discipline in `evals/fixtures/source-diversity/`
- [ ] T080 [US3] Implement production-path diversity benchmark and confidence-bound report proving 100% seeded fake/missing-strata detection, material-gap recall >=0.90, adequate/narrow false-block <=0.10, and ordering/provider invariance, with numerators, denominators, and intervals bound to the pre-retrieval requirements, in `tools/run_source_diversity_benchmark.py`
- [ ] T081 [US3] Replace citation/diversity fixture heuristics with production result scoring in `swos_runtime/evaluation.py`, ensure every fixture evaluator invokes the production path, and update `evals/metrics.md`
- [ ] T082 [US3] Publish model/dataset/diversity limitations and prohibited uses in `models/citation-support/<version>/model-card.md` and `docs/architecture/research-grade-citation.md`

**Checkpoint**: SC-003–SC-005 pass; no provider or human-edited prediction bypasses core policy.

## Phase 6: User Story 4 — Certify provenance interchange (P1)

**Goal**: independently validated, semantically lossless round trips for every advertised PROV format.

**Independent test**: execute the complete format matrix and end-to-end work-order
bundle, validate constraints and independent-oracle agreement, and show each
adversarial loss/invalid/resource-limit case fails.

### US4 tests first

- [ ] T083 [P] [US4] Add EPG v2 statement/bundle/qualified-relation/typed-literal/extension schema tests in `tests/runtime/test_epg_v2.py`
- [ ] T084 [P] [US4] Add PROV-JSON, PROV-N, and PROV-O/TriG parser/serializer losslessness tests in `tests/runtime/test_prov_interop.py`
- [ ] T085 [P] [US4] Add constraints, SHACL, bundle, extension, semantic-equivalence, JCS, RDFC-1.0, and stable-fingerprint tests in `tests/runtime/test_prov_validation.py`
- [ ] T086 [P] [US4] Add full matrix, second-round stability, independent-oracle, invalid-order/type/bundle/relation, and resource-limit tests in `tests/runtime/test_prov_certification.py`

### US4 implementation

- [ ] T087 [P] [US4] Add EPG v2, the executable PROV profile, round-trip certificate schemas, and SWOS PROV vocabulary/shapes in `schemas/research-grade/epg-2.0.schema.json`, `schemas/research-grade/prov-profile.json`, `schemas/research-grade/prov-roundtrip-report.schema.json`, `schemas/provenance-graph/swos-prov.ttl`, and `schemas/provenance-graph/swos-prov.shacl.ttl`
- [ ] T088 [US4] Implement canonical PROV document/bundle/qualified-relation/typed-extension model in `swos_runtime/prov_model.py`
- [ ] T089 [US4] Implement v1 EPG compatibility mapping and lossless EPG v2 conversion in `swos_runtime/prov_interop.py`
- [ ] T090 [US4] Implement PROV-JSON, PROV-N, and PROV-O/TriG parse/serialize with absolute namespace policy in `swos_runtime/prov_interop.py`
- [ ] T091 [US4] Implement syntax, PROV-CONSTRAINTS, SHACL, semantic normal form, extension preservation, JCS/RDFC/PROV-N fingerprints, and limits in `swos_runtime/prov_validation.py`
- [ ] T092 [US4] Implement conversion matrix, per-leg artifacts, assertion comparison, stable second pass, and certificate generation in `tools/certify_prov_roundtrip.py`
- [ ] T093 [P] [US4] Add permitted checksummed valid/invalid/large/adversarial fixtures and manifest in `evals/fixtures/provenance/`
- [ ] T094 [US4] Pin ProvToolbox identity/licence/digest in `benchmark/provenance/oracle-manifest.json` and run that exact independent oracle in `.github/workflows/prov-certification.yml`
- [ ] T095 [US4] Add explicit parser/canonicalization CPU-memory-time bounds in `benchmark/provenance/resource-limits.json` plus 1k/10k and hostile blank-node performance/resource corpora in `benchmark/provenance/manifest.json`
- [ ] T096 [US4] Integrate certified EPG v2 exports into RPM exchange, finalization, and work-order host bundles in `swos_runtime/rpm_exchange.py`, `swos_runtime/finalizer.py`, and `swos_runtime/work_orders.py`
- [ ] T097 [US4] Add certificate/oracle/limitation artifacts to evaluation subject and audit pack in `swos_runtime/evaluation.py` and `tools/assemble_research_grade_audit_pack.py`
- [ ] T098 [US4] Document the accurate PROV-DM/PROV-N/PROV-O and PROV-JSON Member Submission claim in `docs/architecture/research-grade-provenance.md`

**Checkpoint**: SC-007 passes with zero semantic loss and an independent exact-head oracle report.

## Phase 7: User Story 5 — Perform justified multimodal object analysis (P2)

**Goal**: rights-aware region-grounded 2D analysis with separate observation,
interpretation, and cross-modal support, plus default-off evidence-based promotion.

**Independent test**: run the rights-cleared and adversarial corpus through the
production provider interface; satisfy selector, grounding, support, critique,
accessibility, determinism, and safety gates; prove promotion remains disabled
without exact matching evidence.

### US5 tests first

- [ ] T099 [P] [US5] Add object/media/inspection, separate analyse/transform/create-derivative rights, conservative inheritance, lineage/content-credential, and structured accessibility/invalidation tests in `tests/runtime/test_media.py`
- [ ] T100 [P] [US5] Add IIIF pixel/percent and bounded SVG normalization, digest, dimension, ambiguity, and out-of-bounds tests in `tests/runtime/test_region_selectors.py`
- [ ] T101 [P] [US5] Add complete/partial/insufficient/denied/error, resource, deterministic fake, real OpenAI adapter, and provider/model/host substitution conformance tests in `tests/runtime/test_image_analysis.py`
- [ ] T102 [P] [US5] Add observation/interpretation separation, weakest-leg cross-modal support, false-attribution/originality, and multi-view limitation tests in `tests/runtime/test_cross_modal_support.py`
- [ ] T103 [P] [US5] Add default-off, exact-head/artifact mismatch, improvement, safety regression, expiry, approval, and rollback tests in `tests/runtime/test_capability_promotion.py`

### US5 implementation

- [ ] T104 [P] [US5] Add object, media, inspection, accessibility, observation, cross-modal, analysis-result, specialist-agent, and promotion schemas in `schemas/research-grade/object-record.schema.json`, `schemas/research-grade/media-asset.schema.json`, `schemas/research-grade/object-inspection.schema.json`, `schemas/research-grade/accessibility-record.schema.json`, `schemas/research-grade/visual-observation.schema.json`, `schemas/research-grade/cross-modal-support.schema.json`, `schemas/research-grade/image-analysis-result.schema.json`, `schemas/research-grade/specialist-agent.schema.json`, and `schemas/research-grade/capability-promotion.schema.json`
- [ ] T105 [US5] Implement object/media/inspection separation, byte identity, capture/rendition/derivative lineage, separate analyse/transform/create-derivative rights with restrictive inheritance, IIIF 3 ingest, structured accessibility invalidation, and export redaction in `swos_runtime/media.py`
- [ ] T106 [US5] Implement digest-bound IIIF pixel/percent and bounded SVG selector normalization in `swos_runtime/media.py`
- [ ] T107 [US5] Implement provider-neutral bounded 2D analysis protocol and deterministic fake with explicit statuses in `swos_runtime/image_analysis.py`
- [ ] T108 [US5] Implement observation/interpretation separation, cross-modal weakest-leg policy, multi-view limits, and attribution/originality guardrails in `swos_runtime/image_analysis.py`
- [ ] T109 [US5] Integrate image analysis through broker/work orders/orchestrator/finalizer/EPG without provider-owned verification in `swos_runtime/broker.py`, `swos_runtime/work_orders.py`, `swos_runtime/orchestrator.py`, and `swos_runtime/finalizer.py`
- [ ] T110 [US5] Integrate staged art-history then art-criticism pack-assisted critique with ontology criteria in `swos_runtime/discipline_critique.py`
- [ ] T111 [P] [US5] Build at least 60 distinct objects/works and 96 rights-cleared renditions across at least six media/material classes, three mediation conditions, and both art disciplines, plus region/cross-modal/discipline/accessibility/adversarial manifests, per-asset source/right URI/digest/allowed-use/attribution statements, guidelines, and mandatory `DATA-LICENCE.md` in `evals/fixtures/multimodal/`
- [ ] T112 [US5] Implement raw case, agreement, region, cross-modal, false-originality, over-association, valid-reviewed-accessibility completeness numerator/denominator, Wilson two-sided 95% confidence intervals, stability, object/rendition minima, and regression metrics in `tools/run_multimodal_evals.py`
- [ ] T113 [US5] Implement and register one real opt-in OpenAI image-input provider adapter and v2 capability declaration with bounded requests, purpose-rights enforcement, exact model/config/response evidence, and contract status mapping in `swos_runtime/image_analysis_openai.py` and `contracts/capability-contract/capabilities-v2.json`
- [ ] T114 [US5] Create versioned art-history and art-criticism specialist-agent definitions, least-privilege image/object tool permissions, role-separated orchestrator routes, and executable pack-only fallback in `agents/research-grade/art-history.agent.json`, `agents/research-grade/art-criticism.agent.json`, and `swos_runtime/orchestrator.py`
- [ ] T115 [US5] Add optional live exact-head provider workflow with `NOT_RUN` semantics and immutable outputs in `.github/workflows/multimodal-evaluation.yml`
- [ ] T116 [US5] Implement paired promotion assess/approve/commit/default-off/rollback with identical non-agent artifacts, predetermined draws, >=0.08 improvement, lower 95% confidence bound above zero, mandatory successful live evidence, and exact artifact binding in `swos_runtime/image_analysis.py`
- [ ] T117 [US5] Document rights limitations, supported 2D scope, non-attribution, accessibility, provider, and promotion boundaries in `docs/architecture/research-grade-multimodal.md`

**Checkpoint**: SC-008 and SC-009 pass or agent promotion remains disabled with a named blocker.

## Phase 8: Integration, audit pack, and reviewed implementation PR

**Purpose**: prove one complete release candidate at one immutable head.

- [ ] T118 [P] Add end-to-end three-project research-to-memory-to-critique-to-finalization-to-PROV-to-public-proof test in `tests/runtime/test_research_grade_end_to_end.py`
- [ ] T119 [P] Add cross-story classification/rights/ontology/evidence identity preservation tests in `tests/runtime/test_research_grade_integrity.py`
- [ ] T120 Run all existing v1.1/runtime/prose/eight-plane tests and record exact-head commands/results in `artifacts/research-grade/regression-report.json`
- [ ] T121 Run ontology, RPM, classifier, diversity, critique, PROV, and multimodal locked evaluations and record immutable indexes in `artifacts/research-grade/evaluation-index.json`
- [ ] T122 Run Ruff, schema/contract, coverage, security, `tools/check_portability_acceptance.py --definitions-only`, offline, deterministic-stability, bounded safety mutation checks, `tools/lint_skills.py`, and manifest checks and record results in `artifacts/research-grade/quality-report.json`
- [ ] T123 Run reference RPM, packaged 100-pair citation, and PROV performance corpora and record runner fingerprints/raw measurements in `artifacts/research-grade/benchmark-index.json`
- [ ] T124 Assemble and independently verify the pre-freeze in-repository FR/SC evidence manifest and limitations in `artifacts/research-grade/audit-pack.json`; reserve hosted CI/review/approval fields for externally finalized evidence
- [ ] T125 Update version, architecture, security, evaluation, roadmap, progress, and release documentation in `README.md`, `SECURITY.md`, `PROGRESS.md`, `docs/architecture/`, and `evals/metrics.md`
- [ ] T126 Commit all in-repository implementation/evidence, freeze the candidate SHA, push one cohesive implementation PR, and attach the pre-freeze audit manifest in the PR description
- [ ] T127 Obtain ADR-plus-two-maintainer schema approval, maintainer-plus-discipline-steward ontology approval, two-maintainer-plus-evaluation-owner fixture approval, maintainer-plus-portability-owner provider-adapter approval, reviewer-criteria approval, six-case `tools/check_portability_acceptance.py --release` PASS evidence, green hosted CI, and independent review on the frozen head; resolve every thread and store identities/dispositions only as immutable external PR/workflow artifacts
- [ ] T128 Finalize and independently verify an external immutable audit pack combining the committed pre-freeze manifest with exact-head CI/review/approval records; if review changes repository content, repeat T126-T128 for the new head without committing post-freeze records to the branch
- [ ] T129 Obtain explicit owner merge approval as an external PR decision while retaining named no-production/no-merge gates; do not create a commit after final exact-head review

**Final checkpoint**: SC-010–SC-012 and every FR are evidenced at the final reviewed head. Merge and deployment remain separate actions.

## Dependencies and execution order

- Phase 1 blocks Phase 2; Phase 2 blocks every user story.
- US1 repository work, US2 ontology authoring, US4 internal model work, and US5
  entity/rights work can proceed after Phase 2 in different files.
- US2 ontology release blocks discipline critique, classifier ontology binding,
  diversity requirement mapping, and multimodal discipline promotion.
- US4 certification blocks certified RPM exchange and final host-bundle evidence.
- US3 classifier/diversity and US5 multimodal may not enable production behavior
  before their locked evaluations and policies pass.
- Phase 8 begins only after all five story checkpoints are complete or explicitly
  disabled as required by the spec; the cohesive v2 release cannot omit a P1 story.

## Parallel work guidance

`[P]` means the task can be assigned concurrently only after its phase prerequisites
are met and only when it does not edit the same file as another active task. One
architect owns shared-file sequencing for `models.py`, `broker.py`, `orchestrator.py`,
`finalizer.py`, `work_orders.py`, `evaluation.py`, `evals/metrics.md`, and workflow
manifests. Every parallel result is revalidated together at the integrated head.

## Builder completion definition

A task/story/release is not complete from code presence alone. Completion requires
the intended failing test first, production implementation, focused and regression
passes, immutable evidence with exact identities, documented limitations, and no
unresolved blocker. The release additionally requires exact-head hosted CI,
independent review, all review threads resolved, refreshed evidence after the last
change, and explicit owner approval.
