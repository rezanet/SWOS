# Feature Specification: SWOS v2.0 Research Grade

**Feature Branch**: `codex/swos-v2-research-grade-plan`
**Created**: 2026-08-31
**Status**: Planned
**Input**: Deliver the v2.0 Research Grade roadmap phase: cross-project Research
Programme Memory (RPM), formal discipline ontologies, trained citation-support
classification, measured source-diversity controls, deeper discipline-specific
critique, full PROV round-trip certification, and justified multimodal
image/object analysis with art-history and art-criticism agent promotion.

## Objective

Advance SWOS from the Core/specification `1.0.0` and reference runtime `v1.1`
tracks to one auditable `v2.0` Research Grade milestone. The phase must turn the
existing roadmap promises into production-capable, measurable scholarly controls
without weakening the frozen contract authority, human judgement, fail-closed
behavior, host independence, role separation, or exact-head evidence boundary.

## Commands

The builder must be able to validate the finished feature with one documented,
credential-free repository-native command sequence covering schemas, policies,
unit/contract/integration tests, all eight evaluation planes, model/data and
ontology conformance, PROV certification, multimodal adversarial cases, security,
coverage and exact-head public proof. Provider-backed or paid evaluations must be
separate, opt-in commands whose absence cannot make deterministic CI pass by
implication. Exact command names and expected outputs are defined in `plan.md` and
`quickstart.md` after Phase 0 research.

## Project Structure

This feature extends the current single-repository Python runtime, frozen schemas
and policies, discipline/reviewer packs, evaluation fixtures and command-line
tools. New source, contracts, schemas, corpora, model/ontology manifests,
certificates, tests and documentation must live in their corresponding existing
repository layers. No browser application, CRUD service, authentication system,
tenant database or deployment topology is implied.

## Code and Document Style

Implementation must follow the repository's Python 3.11+, typed fail-closed
interfaces, deterministic JSON, Ruff formatting/linting and immutable-evidence
conventions. Human-readable pack and policy prose remains authoritative at its
declared boundary; machine-readable artifacts use stable identifiers, explicit
versions, canonical serialization and content digests. Documents must distinguish
specified, implemented, tested, demonstrated, certified and human-approved state.

## Testing Strategy

All new behavior is test-first. Each user story requires deterministic unit,
contract, integration, adversarial, mutation, migration and end-to-end evidence
where applicable. Training and live-provider workflows add evidence but do not
replace offline conformance tests. Blocker classes require zero unsafe PASSes;
aggregate metrics cannot hide a blocker or a weak discipline slice. The final
candidate reruns the entire existing v1.1 suite and one bound eight-plane v2.0
subject at the exact reviewed head.

## Boundaries

The milestone owns only Research Grade scholarly assurance. It may add explicit
versioned v2 contracts or compatibility envelopes, but it must not silently alter
historical `1.0.0` or `v1.1` meaning. Product identity, tenants, hosted sync,
production operations, autonomous publication and other v3.0 concerns remain out
of scope. The detailed inclusion, exclusion and compatibility rules appear in
Functional Requirements, Assumptions and Out of Scope below.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Continue governed research across projects (Priority: P1)

As a research programme owner, I can reuse approved research memory across
multiple projects without copying unsupported conclusions, losing provenance,
or allowing one project to overwrite another project's record.

**Why this priority**: Research Grade begins with durable continuity. Every later
capability depends on programme-level evidence, decisions, versions, and review
state remaining trustworthy across project boundaries.

**Independent Test**: Create one programme spanning three isolated project
workspaces, approve and supersede memory in the owning project, exchange it with
the other two projects, and prove that all projects resolve the same active
records, contradictions, provenance, policy limits, and chain head while denied,
expired, or unauthorised writes remain rejected.

**Acceptance Scenarios**:

1. **Given** three projects bound to one research programme, **when** an approved,
   source-grounded item is exchanged, **then** every project reads the same
   programme identity, evidence links, decision link, owner, expiry, policy and
   immutable record digest.
2. **Given** two projects propose incompatible positions, **when** their changes
   are reconciled, **then** both positions are preserved as a contradiction and
   no active position is selected without an authorised decision.
3. **Given** a stale, expired, unsigned, provenance-incomplete, classification-
   incompatible, or non-owner write, **when** import or append is attempted,
   **then** the system rejects it without changing the receiving chain head.
4. **Given** a project leaves a programme, **when** its binding is retired,
   **then** future access stops while the historical audit trail remains intact.

---

### User Story 2 - Apply formal discipline knowledge and method critique (Priority: P1)

As a specialist reviewer, I can inspect the formal concepts, evidence standards,
method obligations, and critique findings used for each discipline, instead of
trusting an opaque prose rubric or a one-size-fits-all scholarly score.

**Why this priority**: Formal, testable discipline semantics are required before
specialist capability or modality expands under the proof-before-breadth rule.

**Independent Test**: Validate the formal ontology and compiled runtime profile
for all nine shipped discipline packs, then run one positive and one adversarial
method-critique case per discipline and prove that required moves, prohibited
transfers, terminology mappings, evidence hierarchies, and findings agree with
the authoritative pack.

**Acceptance Scenarios**:

1. **Given** a versioned discipline pack, **when** its ontology is validated and
   compiled, **then** every normative pack concept maps to a stable identifier and
   every runtime concept maps back to one authoritative pack statement.
2. **Given** a psychology causal claim without an adequate design, **when** method
   critique runs, **then** the finding names the missing design warrant and limits
   the licensed conclusion.
3. **Given** an interdisciplinary method transfer, **when** no explicit mapping and
   justification exists, **then** the transfer is blocked rather than inheriting
   the weaker discipline's standard.
4. **Given** a deprecated concept or ontology version, **when** an older project is
   loaded, **then** the migration is explicit, reversible, and does not silently
   change a prior scholarly decision.

---

### User Story 3 - Measure claim support and evidence-base diversity (Priority: P1)

As a citation auditor, I can combine deterministic checks with a trained,
calibrated classifier to distinguish direct support, partial support, context,
contradiction, and non-support at passage level; as a research librarian, I can
measure material source diversity and state coverage limits before synthesis.

**Why this priority**: Citation laundering and concentrated evidence bases are
blocking epistemic risks. A classifier or diversity score that cannot abstain,
explain its evidence, or expose coverage gaps must not influence release.

**Independent Test**: Evaluate a frozen, independently adjudicated, source-held-
out corpus across all nine disciplines and all support labels; then run diverse,
concentrated, incomplete-metadata, counter-position-free, and legitimately
specialised retrieval sets through the same release gates.

**Acceptance Scenarios**:

1. **Given** an exact claim and exact source passage, **when** citation support is
   classified, **then** the result includes the support label, calibrated
   confidence, evidence span, model/data version, and a core-owned release state.
2. **Given** low confidence, missing passages, out-of-distribution input, partial
   support, contradiction, or classifier failure, **when** the result is gated,
   **then** it becomes unresolved or failed and cannot be promoted to PASS.
3. **Given** a source set concentrated by venue, region, language, period,
   methodology, source type, access mode, or stance, **when** diversity is
   measured, **then** the report shows per-dimension completeness, concentration,
   effective categories, composite score, and the exact corrective action.
4. **Given** a field where relevant evidence is legitimately concentrated,
   **when** an authorised discipline profile and rationale are present, **then**
   the limitation is disclosed without manufacturing false balance or discarding
   high-quality evidence.

---

### User Story 4 - Certify provenance interchange (Priority: P1)

As an independent auditor using a different conforming tool, I can export a SWOS
Evidence Provenance Graph, validate it, import it again, and prove that its
entities, activities, agents, bundles, relations, extensions, identifiers,
timestamps, attributes, and meaning survive the round trip.

**Why this priority**: Declared PROV compatibility is not certification. Research
Grade requires independent, reproducible interchange evidence rather than a
schema label.

**Independent Test**: Round-trip the complete conformance corpus and a finalised
SWOS run through each declared supported serialisation and two independent
processors; validate PROV constraints, compare normal forms, and verify stable
canonical digests while malformed, lossy, or resource-exhausting documents fail
closed.

**Acceptance Scenarios**:

1. **Given** a valid EPG with named bundles and SWOS extension relations, **when**
   it is exported and re-imported through every certified profile, **then** the
   semantic normal form and canonical digest are unchanged.
2. **Given** reordered statements or equivalent blank-node identifiers, **when**
   canonical comparison runs, **then** equivalent documents compare equal.
3. **Given** an ordering, typing, uniqueness, impossibility, namespace, bundle, or
   extension-preservation violation, **when** certification runs, **then** it
   reports the precise failure and issues no certificate.
4. **Given** a certificate, **when** any input, converter, profile, test corpus, or
   output changes, **then** the certificate no longer validates.

---

### User Story 5 - Perform justified multimodal object analysis (Priority: P2)

As an art historian or art critic, I can analyse an identified object or
rights-cleared reproduction while keeping observable image features, object
metadata, technical evidence, historical sources, and interpretation distinct
and traceable.

**Why this priority**: The constitution requires the textual and provenance path
to be proven before modalities or agents expand. Art-history and art-criticism
promotion is justified only by a real image/object-analysis tool and passing
false-originality and over-association controls.

**Independent Test**: Run a rights-cleared, stratified image/object corpus through
the media-ingest, region-observation, cross-modal support, discipline-critique,
and release gates; prove that every released interpretation points to identified
visual regions and/or external evidence, mediation is disclosed, and seeded
reproduction artefacts, false attributions, invented details, and unsupported
associations are rejected.

**Acceptance Scenarios**:

1. **Given** an object record and one or more renditions, **when** analysis starts,
   **then** the record distinguishes physical object from surrogate, records
   rights/attribution, identifiers, byte digests, dimensions, transformations,
   capture limits, and whether direct inspection occurred.
2. **Given** a visual observation, **when** it supports an interpretation, **then**
   the observation identifies a reproducible region and the interpretation also
   names its ontology terms, uncertainty, and contextual sources.
3. **Given** a compression artefact, crop, colour-profile change, glare, damage,
   occlusion, low resolution, or absent view, **when** the provider cannot
   distinguish it from an object feature, **then** the system abstains and records
   the limitation.
4. **Given** no usable image or a failed multimodal provider, **when** a text-only
   path remains valid, **then** the text path continues with explicit limits and
   no claim that visual analysis occurred.
5. **Given** art-history or art-criticism promotion criteria are unmet, **when**
   orchestration is configured, **then** both remain packs and no specialist agent
   capability is advertised.

## Acceptance Scenarios

1. **Given** the existing v1.1 public-proof path, **when** v2.0 is enabled, **then**
   v1.1 inputs remain valid and any migration is explicit, versioned and tested.
2. **Given** a deterministic offline CI run, **when** provider credentials,
   model-host access, network access, or paid services are absent, **then** all
   contract, schema, policy, fixture, and orchestration gates still execute.
3. **Given** a candidate Research Grade release, **when** any required plane,
   model, ontology, diversity, PROV, multimodal, human review, or exact-head record
   is missing, **then** release is denied.
4. **Given** the final candidate changes after review or evidence generation,
   **when** release is reconsidered, **then** all exact-head evidence and approval
   must be regenerated for the new head.

### Edge Cases

- Two projects use the same local project label but different canonical origins.
- A programme imports the same event twice, imports a valid prefix, or receives a
  fork whose parent digest is unknown.
- A memory item expires while another project is offline; a superseded item is
  cited by a historical release; or a contradiction has no authorised resolver.
- A discipline term has multiple language labels, multiple inheritance, a cycle,
  a deprecated replacement, or a narrower local term absent from core.
- One discipline lacks enough labelled examples for a reliable classifier slice,
  or a source passage contains multiple claims with mixed support.
- A diversity dimension is inapplicable, unknown, intentionally narrow, or has a
  sample too small for a stable normalised score.
- PROV input contains unknown extension attributes, nested bundles, equivalent
  blank nodes, clock-skewed events, duplicate identifiers, or a canonicalisation
  denial-of-service shape.
- A IIIF manifest changes after retrieval, a local image has EXIF orientation, a
  rendition embeds an invalid provenance claim, or rights permit viewing but not
  redistribution.
- One visual region supports an observation but not the proposed iconographic or
  causal interpretation; multiple views disagree; the object is a replica.
- A live provider passes while the deterministic conformance implementation fails,
  or a model improves aggregate accuracy while degrading a blocker class.

## Requirements *(mandatory)*

### Functional Requirements

#### Programme memory

- **FR-001**: SWOS MUST maintain one canonical research-programme identity across
  multiple explicitly bound projects without treating a host account, tenant, or
  filesystem path as scholarly identity.
- **FR-002**: Every durable programme-memory write MUST retain source grounding,
  EPG references, an SDL decision, human approval, owner, confidence, expiry,
  policy classification, correction path, project origin, parent digest, and
  immutable record digest.
- **FR-003**: Cross-project exchange MUST support deterministic snapshot and
  incremental forms, idempotent import, chain verification, classification and
  rights ceilings, and explicit source/receiver identities.
- **FR-004**: Concurrent, contradictory, stale, expired, unauthorised, or
  provenance-incomplete changes MUST fail closed or enter explicit review; they
  MUST NOT be resolved by last-write-wins.
- **FR-005**: Retirement, supersession, correction, project unbinding and
  programme closure MUST preserve historical records and the releases that used
  them.

#### Formal ontologies and critique

- **FR-006**: SWOS MUST provide a versioned formal ontology for each of the nine
  authoritative discipline packs, with stable identifiers for concepts, evidence
  classes, methods, claims, critique obligations, failure modes and mappings.
- **FR-007**: Ontology sources MUST be machine-validatable and MUST compile to a
  deterministic, offline runtime profile whose digest is recorded in every use.
- **FR-008**: Every normative discipline-pack requirement MUST map to the formal
  ontology and every runtime ontology term MUST map back to an authoritative
  source or explicit versioned extension.
- **FR-009**: Ontology releases MUST define compatibility, deprecation,
  replacement, migration, namespace and cycle rules; prior decisions MUST retain
  the ontology version under which they were made.
- **FR-010**: Cross-discipline mappings MUST preserve each discipline's evidence
  standard, identify terminology collisions and require explicit justification
  for method transfer.
- **FR-011**: Discipline critique MUST emit structured, evidence-linked findings
  for required moves, missing warrants, method limits, counterevidence,
  uncertainty, ontology terms, severity, remediation and reviewer authority.
- **FR-012**: SWOS MUST NOT collapse discipline critique into one universal score
  or allow a model/provider to waive a discipline's blocking requirement.

#### Citation support and diversity

- **FR-013**: Citation support MUST combine deterministic existence, metadata,
  rights, quote and span checks with a trained passage-level classifier.
- **FR-014**: The classifier MUST distinguish `directly_supports`,
  `partially_supports`, `context_only`, `contradicts`, and `not_supported`, plus a
  core-owned unresolved state for invalid, unavailable, uncertain, or
  out-of-distribution cases.
- **FR-015**: Every classification MUST record exact claim/span inputs, label,
  calibrated confidence, uncertainty/abstention reason, model artifact digest,
  training/evaluation data manifest, code/config version and execution
  provenance.
- **FR-016**: Core policy MUST own the final verification state; only direct
  support above the approved calibrated threshold and after all deterministic
  checks may contribute to automatic PASS.
- **FR-017**: Training and evaluation data MUST be licensed, source-provenanced,
  independently annotated, adjudicated, split without source/document leakage,
  and reported by label and discipline.
- **FR-018**: Source diversity MUST be measured at minimum across venue/publisher,
  geography, language, time period, methodology, source type, access mode and
  stance whenever each dimension is material to the research plan.
- **FR-019**: Diversity reporting MUST expose metadata completeness, category
  counts, normalised diversity, effective categories, concentration/dominance,
  sample size, applicability, thresholds, limitations and corrective queries for
  each dimension; missing metadata MUST NOT count as diversity.
- **FR-020**: Diversity controls MUST preserve source quality, seminal sources,
  contradictory evidence and legitimate field concentration; exceptions require
  an SDL rationale and a bounded coverage claim, not manufactured balance.
- **FR-021**: Zero counter-position recall for an argumentative question and any
  undisclosed material coverage failure MUST block a comprehensive synthesis.

#### PROV certification

- **FR-022**: Every serialisation advertised as supported MUST have a bidirectional
  mapping to the SWOS EPG, named profile/version, conformance corpus and
  independently reproducible certificate.
- **FR-023**: Round-trip comparison MUST use semantic normal forms and canonical
  digests rather than byte order, while preserving identifiers, attributes,
  types, bundles, relations and declared SWOS extension semantics.
- **FR-024**: Certification MUST validate applicable W3C PROV constraints and RDF
  canonicalisation requirements and MUST test interchange with at least two
  independent processors.
- **FR-025**: Certificates MUST bind exact source and output digests, tool/profile
  versions, conformance fixtures, results, limitations, timestamp and exact code
  revision; a changed input MUST invalidate the certificate.
- **FR-026**: Malformed, lossy, ambiguous, unsupported, oversized, cyclic or
  resource-exhausting provenance inputs MUST fail closed without issuing a
  partial certificate.

#### Multimodal and object analysis

- **FR-027**: Media ingest MUST distinguish physical object, capture, rendition,
  derivative and region, preserving identifiers, rights, attribution, provider,
  byte digest, dimensions, format, colour/capture metadata, transformations,
  access method, references to separately provenance-bound object-inspection
  activities, accessibility state and known mediation limits.
- **FR-028**: The image/object-analysis contract MUST separate machine observations
  from interpretations and require every observation to name a reproducible
  target region, confidence, modality, model/tool version and provenance.
- **FR-029**: Every visual interpretation MUST link to one or more observations,
  relevant ontology concepts, uncertainty and any required historical,
  technical, provenance or textual evidence; an image match alone MUST NOT prove
  identity, attribution, date, intention, influence or originality.
- **FR-030**: Rights to view, analyse, transform, create a derivative, quote,
  cache, export and redistribute MUST be evaluated separately; analysis MUST NOT
  imply transformation/derivative permission, and unavailable rights MUST
  restrict processing/storage/output without being silently bypassed.
- **FR-031**: SWOS MUST recognise supported interoperable image/manifests and
  embedded authenticity and accessibility metadata when present, preserve their
  status and digest,
  and treat absence or validity as evidence about media provenance only, not as
  proof of the depicted object's identity or an interpretation's truth.
- **FR-032**: Multimodal failure, insufficient resolution, missing views,
  uncertain regions or absent images MUST produce an abstention or an explicitly
  limited text-only path, never a synthetic visual PASS.
- **FR-033**: Art-history and art-criticism packs MAY be promoted to agents only
  after their unique image/object tool contract, role separation, adversarial
  gates, agent contract/tool permissions, role-separated runtime routing,
  executable pack-only rollback path and exact-head promotion certificate all
  pass; otherwise they MUST remain packs.

#### Delivery, compatibility and governance

- **FR-034**: Every new behavior MUST be developed test-first with deterministic,
  credential-free contract, unit, integration, adversarial, migration and
  end-to-end coverage; live provider evaluations MUST be separate and opt-in.
- **FR-035**: The complete v2.0 candidate MUST run all eight existing evaluation
  planes against one exact finalised runtime subject and add capability-specific
  metrics without weakening existing thresholds.
- **FR-036**: Existing v1.0 contracts/schemas and v1.1 inputs MUST remain accepted,
  or any incompatible boundary MUST use an explicit versioned contract, migration
  record, compatibility tests and ADR.
- **FR-037**: Acquisition, annotation/training, inference, scholarly review,
  certification and human release approval MUST remain distinguishable roles;
  no component may create and solely certify its own release evidence.
- **FR-038**: Release MUST fail closed unless the exact candidate head has a
  complete audit pack binding RPM, ontology, classifier/data, diversity, critique,
  PROV, multimodal, evaluation, security, dependency and human-review evidence.
- **FR-039**: Core scholarly contracts MUST remain host/model/retriever/vendor
  independent, and deterministic checks MUST not require provider credentials,
  paid calls or unpinned network state.
- **FR-040**: Enterprise identity, tenant isolation, product observability,
  incident automation, compliance dashboards, deployment topology and other
  v3.0 Product Grade concerns MUST remain out of scope except for interfaces that
  preserve future compatibility without claiming those capabilities.

### Key Entities

- **Research Programme**: Canonical scholarly continuity boundary shared by
  explicitly bound projects; owns policies, active chain heads and closure state.
- **Project Binding**: Versioned relationship between a project origin and a
  programme, including access/classification/rights ceilings and retirement.
- **RPM Event/Item**: Immutable governed memory record plus append/supersede/
  contradict/expire/correct semantics and exact provenance.
- **Exchange Bundle**: Deterministic snapshot or delta with origin, receiver,
  record range, chain proof, manifest and policy limits.
- **Discipline Ontology Release**: Versioned concept scheme, axioms, constraints,
  pack mappings, compatibility statement, compiled profile and content digest.
- **Critique Profile/Finding**: Discipline-specific obligations and a structured,
  evidence-linked assessment of method, warrant, limitation and remediation.
- **Citation Pair/Assessment**: Atomic claim, exact source span, deterministic
  checks, trained support label, calibration evidence and core decision.
- **Classifier Artifact/Data Manifest/Model Card**: Reproducible training and
  inference identity, licensed data lineage, metrics, limitations and digest.
- **Diversity Profile/Report**: Material dimensions, per-dimension thresholds,
  measurements, exceptions, coverage claims and corrective retrieval actions.
- **PROV Profile/Certificate**: Declared mapping and immutable evidence that an EPG
  round-trips through a serialisation and independent processors without loss.
- **Physical Object/Media Asset/Rendition/Region**: Separated object and surrogate
  identities, rights, capture/derivation metadata, hashes and target selectors.
- **Visual Observation/Interpretation**: Region-grounded perceptual statement and
  separately justified scholarly inference with ontology/evidence links.
- **Agent Promotion Record**: Exact-head evidence and human decision enabling or
  revoking the art-history or art-criticism specialist role.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A three-project exchange suite completes snapshot, delta, duplicate,
  fork, contradiction, expiry, correction, retirement and replay scenarios with
  100% active-state and record-digest agreement and zero unauthorised mutations.
- **SC-002**: All nine discipline ontologies pass structural/semantic constraints;
  100% of normative pack statements and runtime terms have bidirectional mappings,
  and recompilation produces byte-identical runtime profiles.
- **SC-003**: The adjudicated citation corpus contains at least 6,000 claim-span
  pairs, at least 600 examples per support label and at least 300 examples per
  discipline. Its locked test contains at least 1,500 pairs, 150 per label, 75 per
  discipline and 300 adversarial non-direct cases. Every item has two independent
  annotations plus adjudication, and no canonical work, source/document family or
  claim family overlaps train, calibration, locked test, temporal or OOD splits.
- **SC-004**: On the frozen held-out citation test set, direct-support precision is
  at least 0.95, contradiction recall at least 0.95, macro-F1 at least 0.85,
  expected calibration error at most 0.05, and selective error at most 0.02 while
  retaining at least 0.70 coverage; every seeded laundering/blocker case is
  rejected, and no discipline has macro-F1 below 0.75.
- **SC-005**: Every material diversity dimension reports at least 0.90 metadata
  completeness; the existing composite threshold of 0.50 and counter-position
  recall above zero are enforced; 100% of seeded concentration and concealed-
  coverage cases are detected, while all authorised narrow-field cases retain
  their sources and disclose their bounds.
- **SC-006**: Positive and adversarial critique fixtures pass for all nine
  disciplines with 100% detection of each pack's blocking required move and zero
  silent cross-discipline standard levelling in the conformance corpus.
- **SC-007**: 100% of the PROV conformance corpus and at least one complete
  finalised SWOS run round-trip through every certified serialisation with equal
  semantic normal-form digests in two independent processors; 100% of invalid and
  lossy fixtures are rejected and no certificate survives input mutation.
- **SC-008**: The multimodal evaluation corpus contains at least 60 distinct
  rights-cleared objects/works and at least 96 rights-cleared renditions across at
  least six media/material classes, three mediation
  conditions and both art disciplines; visual-anchor precision is at least 0.95,
  seeded invented-detail and reproduction-artefact cases have zero unsafe PASSes,
  and over-association/false-originality detection is at least 0.95.
- **SC-009**: Agent promotion remains disabled until every multimodal blocker,
  separation-of-duties check and rollback rehearsal passes on the same exact
  candidate head; disabling the promotion restores the pack-only path without
  data loss or contract change.
- **SC-010**: Deterministic v2.0 CI, including all existing v1.1 suites, schemas,
  policies, eight evaluation planes, security checks and new conformance suites,
  passes without network or credentials and maintains at least 80% branch-aware
  executable coverage with no regression of an existing blocking metric.
- **SC-011**: A reviewer can verify from one exact-head audit pack, without hidden
  service state, which programme memory, ontology, model/data, diversity profile,
  critique findings, provenance profiles, media inputs, evaluation results and
  human decision produced the candidate.
- **SC-012**: On a documented reference CPU, local programme lookup over 10,000
  active items completes within 250 ms p95, a 100-pair citation batch within 5 s
  p95 using the packaged inference artifact, and provenance certification of a
  10,000-statement document within 60 s and bounded memory; limit violations fail
  explicitly rather than hanging or degrading assurance.

## Assumptions

- The current `origin/main` v1.1 runtime and simplified exact-SHA release record
  are the implementation baseline; completed v1.1 work is extended, not repeated.
- The nine checked-in discipline packs remain the human-readable authorities.
  Formal ontologies make their semantics executable but do not silently amend
  their scholarly requirements.
- Cross-project means multiple explicitly registered project origins within one
  research programme. It does not introduce user accounts, enterprise tenants,
  hosted synchronisation, or unrestricted network replication.
- Human maintainers own programme-memory decisions, gold-label adjudication,
  ontology approval, specialist promotion and final release approval.
- Public or appropriately licensed research and media can be assembled for the
  training and evaluation corpora. Items without adequate rights may contribute
  identifiers/metadata and permitted excerpts but not redistributed content.
- Aggregate model metrics never override blocker-class, discipline-floor,
  calibration, abstention, or adversarial requirements.
- A valid embedded media provenance credential is a useful provenance signal but
  is neither mandatory nor sufficient evidence of depicted identity or scholarly
  interpretation.
- v2.0 ships as one cohesive governed milestone and one final implementation
  review/merge. Work may be developed in dependency-ordered internal phases, but
  partial phases must not be represented as Research Grade completion.

## Out of Scope

- Product Grade identity, RBAC/ABAC, tenant isolation, hosted sync services,
  dashboards, drift monitoring services, incident automation, compliance
  reporting, cost controls and production deployment topology.
- Autonomous publication, removal of human scholarly judgement, or automatic RPM
  writes from model reflection.
- General-purpose computer vision, biometric identification, facial recognition,
  authenticity/attribution claims based only on pixels, or training on media
  without documented rights.
- Promotion of the other seven discipline packs to independent agents.
- Weakening or retroactively rewriting frozen v1 evidence, contracts, release
  records, historical provenance or completed audit packs.
