# Research: SWOS v2.0 Research Grade

**Feature**: `008-swos-v2-research-grade`
**Baseline inspected**: `8d440296b4a9df708f1140a04bae1ae24f74fee3`
**v1.1 source-release boundary**: accepted offline source release
`b10c4351e4b3cdb6c180fb95251c9b84b9b919b5`; the planning baseline above is a
subsequent documentation/reconciliation head and does not claim live
compatibility, package distribution, deployment or signing.
**Status**: Decisions complete; no unresolved clarification markers

## 1. Scope and baseline

Research Grade extends the governed v1.1 runtime. It does not replace the eight
evaluation planes, Evidence Matrix, Evidence Provenance Graph (EPG), Scholarly
Decision Log (SDL), discipline packs, deterministic finalizer, or public proof
bundle. Existing v1.0 schemas and v1.1 inputs remain frozen compatibility
surfaces. Every Research Grade contract is introduced as a parallel, explicitly
versioned v2 artifact.

The repository already has useful primitives, but not the requested behavior:

- `GovernedJsonStore` provides chained append-only audit records, while the RPM
  is test-only and the finalizer emits an empty hard-coded snapshot.
- discipline packs are prose rubrics; there is no formal graph, loader, or
  machine-enforced mapping from pack rules to claims and critique findings.
- citation support is a provider judgment without trained-artifact identity,
  calibration, abstention, or dataset provenance.
- `source_diversity_index` counts retrieval providers, which are acquisition
  channels rather than epistemically independent sources.
- the EPG schema declares PROV compatibility but there are no serializers,
  parsers, constraints checks, semantic comparison, or round-trip certificates.
- `image_analysis` is named in a tool contract but has no adapter, schema,
  provider, rights model, region grounding, or production evaluation.

The release is one cohesive milestone and one reviewed PR. Training, live model
evaluation, independent PROV certification, and multimodal evaluation may use
separate governed workflows, but all immutable outputs must bind to the same
release-candidate commit before merge.

## 2. Decision R1: cross-project RPM

### Decision

Use a local transactional SQLite programme repository built with Python's
standard library. Preserve `GovernedJsonStore` for v1.1 compatibility,
deterministic fixtures, legacy import, and immutable per-run audit exports.

Every public operation requires a `ResearchScope` containing
`repository_namespace_id`, `programme_id`, and `project_id`. A namespace is an
operator-supplied partition that prevents accidental mixing; it is not caller
authentication, tenant isolation, RBAC, or an authorization boundary.

The database uses append-only lifecycle events and a rebuildable projection,
foreign keys, explicit transactions, bounded lock waits, a schema-version table,
and a hash chain per namespace/programme. WAL is permitted only after local
filesystem preflight. There is no unscoped list or search API.

Every substantive operation—including project registration/retirement, write,
confirm, correction, supersession, contradiction open/resolve, expiry, deletion,
and exceptional-read authorization—follows `propose -> assess -> approve ->
commit`. Assessment binds the canonical operation, exact EPG and SDL heads,
resolved node/decision identifiers, policy digest, scope, classification,
contradiction result, active target/head, `as_of`, and expiry. Commit re-resolves
every binding to prevent time-of-check/time-of-use substitution.

Reads are classification-filtered, expiry-aware at an injected `as_of` time,
and provenance-producing. Normal reads exclude expired, deleted, contradicted,
corrected, and superseded entries. Governance/adversarial reads may include them
only through an explicit logged policy.

Portable exchange is a bounded bundle containing a manifest, events, permitted
payloads, provenance, decisions, checksums, and limitations. Import is two-phase:
`inspect_import` performs no durable write and returns a deterministic diff;
`commit_import` requires that exact inspection digest and human approval.

`governance/policies/research-programme-memory-v2.policy.json` is authoritative
for v2 binding, write, read, lifecycle, deletion, and assessment decisions. It
names its relationship to frozen `memory-write.policy.json`, carries version and
digest, and is included in every assessment. Exchange-specific archive rules
remain in `rpm-exchange.policy.json` and cannot weaken the RPM policy.

### Rationale

SQLite supplies crash-safe multi-process transactions, indexed scoped reads,
atomic evidence validation, and projection rebuilds without introducing a
hosted service or v3 tenancy. Event history preserves corrections and
contradictions without destructive overwrite. Separating immutable envelopes
from payload content permits governed logical deletion while documenting that
backups and physical-media erasure remain outside this claim.

### Alternatives rejected

- **One global JSONL ledger**: insufficient atomicity, locking, indexed query,
  cross-artifact referential integrity, and safe content deletion.
- **Network memory service or hosted database**: expands scope into Product Grade
  identity, tenancy, deployment, and operations.
- **Last-write-wins snapshots**: destroys contradiction, correction, provenance,
  approval, and project-origin semantics.

## 3. Decision R2: formal discipline ontologies

### Decision

Use a hybrid standards profile:

- RDF is the graph model;
- SKOS models stable concepts, labels, hierarchy, and conservative mappings;
- a small OWL 2 RL-compatible vocabulary models typed relationships;
- SHACL Core is the closed-world conformance gate;
- Turtle is the reviewed canonical source;
- deterministic JSON-LD and compiled JSON are interchange/runtime forms.

The ontology defines schemes for discipline, method family, evidence type,
epistemic claim type, proof standard, critique criterion, failure mode, source
role, and diversity dimension. Relationships include `usesMethod`,
`acceptsEvidenceType`, `requiresCriterion`, `guardsAgainstFailureMode`,
`licensesClaimType`, `requiresSourceRole`, and `hasRubricWeight`.

`PACK.md` remains the human explanation. The formal graph is authoritative for
identifiers, required relationships, critique rules, and weights. Every enum
discipline must map to exactly one pack and concept. The existing
`enterprise_reporting` remains accepted only by the frozen v1 compatibility
profile. It is explicitly unsupported as a Research Grade scholarly discipline
in the v2 schema because there is no approved pack or ontology; version dispatch
returns a clear migration error and never falls back to `interdisciplinary`.

Core runtime consumes byte-stable compiled JSON and therefore remains offline
and free of RDF-engine requirements. Pinned `rdflib` and `pyshacl` are optional
build/validation dependencies. Compilation records source, shape, compiler, and
output digests and proves Turtle -> JSON-LD -> RDF graph isomorphism.

### Rationale

SKOS supplies durable concept identity but does not close a scheme; SHACL
provides mandatory completeness constraints. OWL adds bounded formal meaning
without attempting to encode every scholarly judgment as inference. Compilation
keeps production behavior deterministic and provider-neutral.

### Alternatives rejected

- **JSON/YAML taxonomy alone**: validates shape but not graph semantics,
  relationships, mappings, or isomorphism.
- **OWL-only/open-world validation**: cannot prove required pack completeness.
- **Prose prompts as authority**: not independently validated or safely mapped
  to machine decisions.

Primary references: [SKOS](https://www.w3.org/TR/skos-reference/),
[OWL 2](https://www.w3.org/TR/owl2-overview/),
[SHACL](https://www.w3.org/TR/shacl/), and
[JSON-LD 1.1](https://www.w3.org/TR/json-ld11/).

## 4. Decision R3: deeper discipline critique

### Decision

Introduce a structured `DisciplineCritique` result instead of a universal
quality score. The result identifies ontology/pack versions, criterion IRI,
finding type, severity, claim/evidence targets, observations, reasoning,
counter-position or limitation, remediation, confidence, and review state.

Each discipline supplies mandatory criteria and proof standards through its
ontology module. A common envelope enables aggregation while the pack-specific
rubric preserves domain meaning. Cross-disciplinary work must report criterion
results separately and expose disagreement; it cannot average away a failed
mandatory criterion.

Each of the nine supported packs receives positive, negative, boundary, and
cross-discipline fixtures reviewed by a competent human. The missing
art-criticism fixture is a release blocker. Ontology or pack unavailability
fails before planning and never silently substitutes `interdisciplinary`.

### Rationale

Critique quality depends on discipline-specific methods and failure modes.
Structured findings make that depth testable and traceable while preserving
human-readable scholarly reasoning.

## 5. Decision R4: trained citation-support classification

### Decision

Implement a five-class cross-encoder pair classifier using the normative semantic
support vocabulary: `directly_supports`, `partially_supports`, `context_only`,
`contradicts`, and `not_supported`. Invalid/unavailable inputs, deterministic
citation-laundering failures, uncertainty, and out-of-distribution cases are
core-owned `rule_rejected` or `abstained` dispositions, not trained semantic
labels. This prevents data-quality and policy failures from being laundered into
model predictions.

The bounded, provenance-addressed input is an atomic claim, exact quoted passage,
bounded surrounding context, applicable discipline/method IRIs, and source-role
IRI. Publisher prestige, provider identity, citation count, and admission result
are excluded as predictive features.

Every `CitationSupportDecision`, including abstention, rule rejection, and error,
records the exact execution code SHA, configuration digest, execution
identifier/provenance, and timestamp alongside its immutable pair and artifact
bindings. Aggregate input digests and candidate positions do not replace this
per-decision provenance.

The safety cascade is:

1. deterministic source existence, quote containment, metadata, retraction,
   rights, and provenance checks;
2. trained semantic classification;
3. temperature-calibrated selective decision with explicit abstention;
4. deterministic core admission, where only a non-abstained calibrated
   `directly_supports` result can enter verified evidence.

Every result records all probabilities, selected threshold, calibration/model
identities and SHA-256 digests, dataset manifest digest, ontology version,
canonical input digest, runtime/backend versions, and abstention reason.
Classifier output is immutable evidence; a human override is a separate SDL
decision, never an edited prediction.

Training data combines licensed/admissible public seed data such as SciFact with
SWOS human-adjudicated cross-discipline examples. Split assignment is grouped by
canonical work and claim family to prevent paraphrase/edition leakage. Two
discipline-competent annotators plus adjudication are required. The dataset card,
model card, source/licence manifest, split algorithm, agreement report, training
configuration, calibration, thresholds, and locked-test predictions are
immutable artifacts.

The implementation may use the existing optional Sentence Transformers stack
for training and export a pinned inference artifact. Large weights live in an
immutable release artifact/model registry; Git stores the model card, licence,
URI/revision, digests, and verification manifest. Ordinary CI never downloads a
model and uses deterministic injected logits; a dedicated release workflow
evaluates the real artifact.

### Threshold decision

Release gates are macro-F1 >= 0.85; contradiction recall >= 0.95;
`not_supported` recall >= 0.90; ECE <= 0.05; raw direct-support precision
>= 0.95 with its lower 95% confidence bound >= 0.98; unsupported auto-admission
upper 95% confidence bound <= 0.01; selective error <= 0.02; overall selective
coverage >= 0.70; no discipline macro-F1 below 0.75; and OOD or
unsupported-version abstention >= 0.95. No discipline direct-support precision
may be below 0.95. Deterministic laundering/invalid-citation blocker fixtures
must be rejected at 100%. These gates intentionally satisfy both SC-004 and the stronger
confidence-bound safety target. If no threshold meets safety and coverage, model
release is blocked rather than relaxing safety.

For machine-testable reporting, let `N` be the number of valid locked-test
items, let `A` be the items for which the calibrated policy emits a non-abstain
decision, and let `W` be the incorrect decisions in `A`. Selective coverage is
`A / N`, and selective error is `W / A`; an empty `A` is a failed coverage gate,
not a zero-error result. Every locked-test item, including abstention and
blocker cases, remains in `N`. Class, discipline and blocker rates use the same
explicit item set named by their report section. Unless a contract states
otherwise, reported 95% confidence bounds use the two-sided Wilson score
interval over the stated numerator and denominator, with no pooling across
disciplines or blocker classes.

The production release floor is at least 6,000 reviewed pairs with a locked test
of at least 1,500 and 300 adversarial non-direct examples, plus the per-label and
per-discipline split minima in SC-003. Corpus construction, human annotation,
adjudication, and immutable split freezing are release tasks, not documentation
targets or examples.

### Alternatives rejected

- **Prompt-only/LLM verdict**: may be diagnostic but cannot auto-admit evidence.
- **Uncalibrated argmax**: has no governed risk/coverage boundary.
- **Random row split**: leaks related passages and works between train/test.
- **Model binary without manifest**: cannot be reproduced or audited.

Primary references: [SciFact](https://aclanthology.org/2020.emnlp-main.609/),
[SciFact-Open](https://aclanthology.org/2022.findings-emnlp.347/),
[temperature scaling](https://proceedings.mlr.press/v70/guo17a.html),
[selective classification](https://jmlr.csail.mit.edu/papers/v11/el-yaniv10a.html),
[model cards](https://research.google/pubs/model-cards-for-model-reporting/), and
[datasheets](https://arxiv.org/abs/1803.09010).

## 6. Decision R5: measured source-diversity controls

### Decision

Compute diversity over distinct, evidence-admitted, actually cited canonical
source families, never retrieval-provider count. Required dimensions are work
family, publisher/issuing owner, venue, author/institution cluster, region or
jurisdiction, language, publication period, methodology, source type, access
mode, and stance/source role.

Each metadata value records `observed`, `externally_verified`, `inferred`, or
`unknown` plus provenance. Inferred or unknown values do not satisfy mandatory
coverage. Each applicable dimension reports sample size, category count, shares,
maximum share, HHI/Simpson concentration, effective number, normalized balance,
required-strata coverage, and unknown rate. Compute both source-count and
claim-exposure concentration and gate on the worse result.

The research plan declares applicable dimensions and required strata before
retrieval using the discipline ontology. Default ordinary-work gates at five or
more source families are owner HHI <= 0.40, owner maximum share <= 0.60,
required-strata coverage = 1.0, required-dimension unknown rate <= 0.10, and all
required method/source-type roles represented. Three or four families require
review; fewer than three block. Argumentative, position, and synthesis work
requires a verified counter-position or limitation.

For every other material dimension, the approved pre-retrieval requirement must
state maximum HHI/share, minimum effective number/balance, required strata,
coverage, and unknown-rate thresholds, or an ontology-linked `not_applicable`
rationale. A missing threshold or applicability decision blocks the plan. This
allows discipline/question-specific policy without inventing universal language,
geography, date, method, access-mode, or stance quotas after seeing results.

The frozen v1 provider-count `source_diversity_index` remains readable only for
v1 compatibility and never gates Research Grade. The v2
`research_grade_composite` preserves the >= 0.50 numerical gate but is a
versioned geometric mean of applicable per-dimension normalized balances, capped
by the minimum required-strata coverage and metadata completeness. It never
overrides a failed dimension. A narrow-corpus exception requires evidence, an SDL
decision, scope, affected dimension, expiry, and a visible final limitation; it
does not convert a failure into an unqualified pass.

### Rationale

The governed held-out benchmark contains at least ten locked, human-reviewed
packets per supported discipline plus separate tuning packets. It must detect
100% of single-family, single-owner, provider-only fake-diversity, duplicate, and
missing-required-strata cases; achieve >= 0.90 recall on reviewer-identified
material gaps; and have <= 0.10 false-block rate on adequate or justified
narrow-corpus packets. Every metric is invariant to ordering/provider renaming.

Variety, balance, concentration, unknownness, and claim exposure are distinct
properties. Exposing each prevents token citations, duplicate editions, mirrors,
or provider renaming from manufacturing diversity.

## 7. Decision R6: PROV round-trip certification

### Decision

Create an EPG v2 interchange model and converters without modifying the frozen
v1 schema. Advertise the profile accurately as:

> SWOS PROV-DM/PROV-N/PROV-O round-trip profile, with PROV-JSON Member
> Submission compatibility.

Do not say W3C-certified. PROV-JSON is a Member Submission, not a W3C
Recommendation. Supported certification formats are PROV-JSON, PROV-N, and
PROV-O as a named RDF dataset using TriG or N-Quads so bundles survive. PROV-XML
may be implemented later only after it receives the same bidirectional profile,
oracle, constraints, and losslessness tests; it must not remain advertised based
on an enum alone.

The v2 model supports namespace/base IRI, real named bundles, deterministic
statement IDs, qualified relation fields, typed and language-tagged attributes,
bundle membership, source scope metadata, and a published SWOS extension
namespace. Unknown extensions are preserved through a typed extension bag or
rejected; silent loss is forbidden.

Certification has three layers:

1. syntax/profile parsing and schema/SHACL validation;
2. PROV-CONSTRAINTS validity and semantic normal-form equivalence, including
   bundle, identifier, type, language, extension, and qualified-relation checks;
3. canonical integrity using RFC 8785/JCS for JSON, RDFC-1.0 canonical N-Quads
   for RDF datasets, and a semantic-normal-form digest for PROV-N.

The report binds input/output digests, algorithms, profile/tool/oracle versions,
fixture hashes, assertion counts, resource limits, results, and limitations.
Byte equality is not semantic certification.

Use pinned Python `prov` in-process and pinned/checksummed ProvToolbox as an
independent release oracle. Ordinary CI runs deterministic local fixtures; the
release workflow also runs the independent oracle and permitted checksummed PROV
constraint corpus. Hostile blank-node/canonicalization cases are bounded by
size, time, and memory and return `resource_limit`, never pass.

### Alternatives rejected

- **Current EPG compatibility flag**: a declaration without executable proof.
- **Turtle for bundles**: cannot preserve named RDF datasets; use TriG/N-Quads.
- **Self-certification by one converter**: repeats the same defect in both legs.
- **Raw byte comparison**: prefixes, ordering, and syntax can differ while
  semantics remain equal.

Primary references: [PROV overview](https://www.w3.org/TR/prov-overview/),
[PROV constraints](https://www.w3.org/TR/prov-constraints/),
[PROV links](https://www.w3.org/TR/prov-links/),
[PROV-JSON status](https://www.w3.org/submissions/prov-json/),
[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), and
[RDF Dataset Canonicalization](https://www.w3.org/TR/rdf-canon/).

## 8. Decision R7: justified multimodal and object analysis

### Decision

Model the physical object, media asset, visual observation, and cross-modal
support as separate entities. A media asset is a view/capture/rendition of an
object, not the object itself. It records content digest, role (surrogate,
documentary, technical, installation, detail, diagram, or generated), view and
capture conditions, dimensions/resolution, colour metadata, references to
separate physical-inspection activities, transformations, rights, derivative
lineage, content-credential state, and structured accessibility metadata.

Visual observations are bounded to exact immutable assets and selectors. Support
IIIF pixel/percentage regions and W3C Web Annotation SVG selectors; normalize to
pixel coordinates and reject out-of-bounds, ambiguous, or digest-mismatched
selectors. Cross-modal support separately records the observation-to-claim,
claim-to-source, and asset-to-object legs and takes the weakest required leg.

The provider interface returns `complete`, `partial`, `insufficient`, `denied`,
or `error`. The release includes a deterministic fake for ordinary CI and one
real opt-in OpenAI image-input adapter behind the same contract; its exact model,
request configuration, SDK/runtime, and responses are digest-bound in live
evaluation evidence. Machine observations, art-historical interpretation, attribution,
originality, identity, and confidence are separate fields. No interpretation can
be verified without observations, object/media identity, rights, and provenance.
Missing views or resolution causes a scoped limitation or fail-closed outcome.

Rights are purpose-specific: view, analyse, transform, create derivative, quote,
cache, export, and redistribute. Analysis never implies transform/derivative
permission. Derivatives inherit the most restrictive applicable parent condition
unless a separate provenance-bound grant permits more. Open access does not
imply every permission. Exports omit barred
media while retaining redacted evidence and limitations. Generated or materially
transformed assets are explicitly labelled.

Use stable IIIF Presentation 3 and Image API 3, not Presentation 4 release
candidate. Use the W3C Web Annotation Data Model for selectors. External object
vocabularies may align conservatively to CIDOC CRM/Linked Art but SWOS keeps a
minimal governed runtime profile.

Accessibility is structured as decorative/functional/evidentiary purpose, short
alternative, conditional long description, labelled regions, non-image fallback,
origin, human-review status, language, exact asset digest, and validity. Any
pixel or semantic derivative invalidates inherited accessibility text until
re-reviewed. Completeness is valid reviewed records and fallbacks divided by all
in-scope non-decorative assets requiring them; the release gate is 1.0.

Direct physical inspection is an actor/time/object/conditions/provenance activity
referenced by assets or interpretations, never a reusable asset property.

Promotion is staged and default-off: contract -> bounded 2D tool gate ->
art-history assisted pack -> art-history agent -> multi-view breadth ->
art-criticism assisted pack -> art-criticism agent. Promotion requires a signed
decision binding exact evaluation evidence and a measured absolute improvement
of at least 0.08 over pack-only, with the lower 95% confidence bound on the paired
improvement above zero and no safety regression. Baseline and candidate use the
same corpus/case IDs, provider/model, non-agent configuration, prompts, seeds,
and predetermined repeated draws; only specialist routing differs. Successful
exact-head live provider evidence is mandatory; `NOT_RUN` leaves promotion
disabled. Enabled promotion activates versioned art-history/art-criticism agent
contracts, least-privilege tool permissions, role-separated orchestrator routes,
and an executable pack-only fallback. Failure rolls back to pack-only while
preserving evidence and reopening review.

### Evaluation decision

The governed corpus contains `DATA-LICENCE.md` plus per-asset source/right URIs,
byte digest, permitted actions, attribution, and required statement. It contains
at least 60 distinct rights-cleared objects/works and 96 rights-cleared
renditions, 80 atomic region-grounding claims across at least 20 assets, 120
cross-modal pairs, 48 discipline tasks across at least 24 works, and 96
adversarial cases.

Release gates include zero unsafe rights/hash/lineage passes; 100% valid selector
binding; byte-identical deterministic output across three runs; cross-modal
precision >= 0.98, recall >= 0.90, F1 >= 0.94; region hit >= 0.90 macro; false
region <= 0.02; zero laundered inference or unsupported attribution/originality;
visual-grounding coverage 1.0; critical false-originality/over-association recall
1.0 and overall >= 0.95; accessibility completeness 1.0; adjudicator alpha >=
0.80; discipline weighted score >= 0.80 with each mandatory dimension >= 0.70;
and no existing blocking regression.

Primary references: [IIIF Presentation 3](https://iiif.io/api/presentation/3.0/),
[IIIF Image API 3](https://iiif.io/api/image/3.0/), and
[W3C Web Annotation](https://www.w3.org/TR/annotation-model/).

## 9. Decision R8: evaluation, dependencies, and release evidence

All ordinary PR CI is deterministic, offline, credential-free, and paid-call
free. Optional ontology, training, PROV-oracle, and live multimodal dependencies
are pinned in dedicated extras/workflows with licences and hashes. Missing live
credentials produces `NOT_RUN`, never a fabricated pass.

Every fixture evaluator must call the production runtime path. Existing
hard-coded fixture-name heuristics are replaced; evaluation cannot pass merely
because expected labels are present in JSON. The full eight-plane suite,
existing v1.1 regressions, schemas, lint, security checks, coverage, and
portability run at the exact candidate SHA.

The release audit pack contains:

- exact source SHA and clean-tree statement;
- frozen spec, plan, research, model, contract, and task digests;
- dataset/model/ontology/PROV/media corpus manifests and licences;
- raw predictions, adjudication/agreement, metrics, and benchmark reports;
- independent PROV oracle output;
- RPM concurrency/crash/import/export evidence;
- multimodal rights, grounding, cross-modal, critique, and promotion results;
- all CI/check identities and immutable artifact links;
- unresolved limitations and no-production/no-merge gates;
- independent review bound to the final head.

## 10. Resolved unknowns and non-goals

- Storage is local SQLite plus governed exchange, not a network service.
- Scope keys are not tenant security.
- Ontology source is Turtle/SKOS/OWL/SHACL; runtime is compiled JSON.
- Citation classification is trained, calibrated, selective, and subordinate to
  deterministic admission.
- Diversity uses source families and claim exposure, not provider count.
- PROV support is limited to formats actually certified; PROV-JSON status is
  described accurately.
- Multimodal v2 is bounded 2D image/object analysis; video, audio, 3D, invasive
  scientific imaging, autonomous attribution, and product hosting remain out of
  scope.
- No v2 component may weaken v1.1 governance or silently infer missing evidence.
