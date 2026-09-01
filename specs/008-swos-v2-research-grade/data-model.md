# Data Model: SWOS v2.0 Research Grade

All identifiers are nonempty, normalized strings with schema-defined maximum
lengths. All timestamps are RFC 3339 UTC. All hashes are lowercase SHA-256 over
the declared canonicalization profile. Unknown fields fail closed on governed
inputs unless a schema explicitly provides a versioned extension bag.

## 1. Cross-project programme memory

### ResearchScope

| Field | Type | Rule |
|---|---|---|
| `repository_namespace_id` | string | Required partition; not authentication or tenancy |
| `programme_id` | string | Required scholarly continuity boundary |
| `project_id` | string | Required registered origin/consumer project |

Every repository method takes `ResearchScope`; no global default exists.

### ProgrammeProjectBinding

Fields: `binding_id`, scope, project display label, registration manifest digest,
visibility permissions (`programme`, `project`), created/retired timestamps,
approval evidence, EPG/SDL references, and status (`active`, `retired`). A retired
project cannot write or perform normal reads; its historical provenance remains.

### MemoryCandidate and MemoryAssessment

`MemoryCandidate` contains item ID, category, visibility, statement/content
reference, confidence, classification, owner, expiry, source-grounded flag,
supporting EPG nodes, SDL decision reference, and contradiction candidates.

`MemoryAssessment` contains assessment ID/status, scope, RFC 8785 candidate hash,
EPG document/head digest and resolved node IDs, SDL document/head digest and
resolved approved `memory_write` decision, policy ID/version/digest, rights and
classification result, contradiction result, creation/expiry, and deterministic
denial reasons. It is immutable and single-use.

The assessed operation is a discriminated union covering registration,
retirement, programme closure, write, confirm, correction, supersession,
contradiction, expiry, deletion, and exceptional-read authorization. Programme
closure is an assessed terminal transition that preserves all historical records,
release bindings and provenance while rejecting new writes and normal reads for
the closed programme. Every durable transition binds the operation digest,
active target/head, evidence, policy, `as_of`, and expiry and is re-resolved at
commit; there is no lifecycle mutation bypass.

### RPMPolicyRelease

Fields: policy ID/version/digest, effective/deprecated timestamps, relationship
to frozen v1 `memory-write.policy.json`, operation decision tables,
classification/rights ceilings, required EPG/SDL/approval bindings, assessment
TTL, exceptional-read rules, migration guidance, and approval evidence.

### HumanApproval

Fields: approval ID, asserted approver, role, timestamp, assessment/candidate
digests, disposition, rationale, and SDL reference. This is recorded operator
evidence; v2 does not claim identity authentication.

### MemoryEvent

Fields: event ID, scope, monotonic programme sequence, prior event hash, event
hash, event type, item/version IDs, payload reference/digest, provenance and SDL
bindings, actor/approval evidence, event timestamp, canonicalization profile,
and reason.

Event types: `write`, `confirm`, `status_change`, `correct`, `supersede`,
`contradiction_opened`, `contradiction_resolved`, `expire`, `delete`, `close`,
and `import`.

### MemoryProjection

Rebuildable current view with item/version, scope, category, visibility, active
payload reference, status, confidence, classification, owner, timestamps,
expiry, predecessor/successor links, contradiction links, last event/confirmation,
and provenance bindings. It is never evidence independent of its event chain.

Statuses: `active`, `contradicted`, `corrected`, `superseded`, `expired`,
`deleted`. Normal retrieval returns only effective `active` rows and calculates
expiry at query time.

### MemoryReadReceipt

Fields: receipt/activity ID, consuming run/work order, scope, query/filter digest,
policy and classification ceiling, `as_of`, returned item/version IDs, exclusion
counts by reason, exceptional review mode, influence flag, and EPG links.

### RPMExchangeBundle

Logical layout: `manifest.json`, `events.ndjson`, `payloads/`, `provenance/`,
`decisions/`, `checksums.json`, `limitations.json`. Manifest fields include
profile/version, origin scope, time range, lifecycle inclusion policy, source
head, counts, classification ceiling, canonicalization algorithms, file sizes
and digests, rights exclusions, export approval, and export EPG activity.

### ImportInspection

Fields: inspection ID/digest, source bundle digest, exact receiving
`destination_scope`, externally supplied destination mapping, limits,
schema/checksum/chain/PROV/SDL/rights/classification results, collision results,
deterministic diff, warnings, created/expiry timestamps, and commit eligibility.
Commit accepts the destination scope explicitly, re-resolves that registered and
non-closed receiver and the inspection digest at commit time, and is atomic only
when they match; it requires an approval over this digest and destination.

### RPM state transitions

```text
candidate -> assessed_denied
candidate -> assessed_allow -> approved -> active
active -> confirmed -> active
active -> contradiction_opened -> contradicted
contradicted -> contradiction_resolved -> active | superseded | resolved_by_scope
active -> corrected -> successor(active)
active -> superseded -> successor(active)
active -> expired
active|expired|contradicted -> deleted
```

Invalid transitions, inactive targets, cross-scope links, stale heads, expired
assessments, or mismatched approvals fail without a partial event.

## 2. Discipline ontology and critique

### OntologyRelease

Fields: ontology ID/version IRI, semantic version, source/shape/context/compiled
digests, compiler/tool versions, issued/deprecated timestamps, compatibility and
migration references, supported packs, external mappings, and approval evidence.

### DisciplineConcept

SKOS concept with stable IRI, concept scheme, preferred/alternate labels,
notation, definition, broader/related concepts, conservative external mappings,
status, and provenance.

### DisciplineProfile

Fields: discipline concept IRI, pack ID/version/digest, method and evidence-type
IRIs, proof standards, required critique criteria, guarded failure modes, source
roles, diversity dimensions/strata, rubric weights, cross-discipline mappings,
and ontology release digest. Each enum discipline maps exactly once.

### CritiqueFinding

Fields: finding ID, work/run, discipline/pack/ontology identifiers and digests,
criterion and failure-mode IRIs, finding type, severity, targeted claims/evidence,
observations, reasoning, counter-position/limitation, remediation, confidence,
review state, reviewer evidence, EPG links, and SDL links.

Finding states: `machine_proposed`, `human_confirmed`, `human_revised`,
`dismissed`, `blocking`. A machine result never impersonates human confirmation.

### DisciplineCritiqueReport

Contains report ID, subject/evidence digests, one or more discipline sections,
criterion results, mandatory failures, unresolved disagreements, limitations,
aggregate display summaries, approvals, and provenance. A display summary cannot
override a mandatory criterion or replace the per-discipline record.

## 3. Citation-support classification

### CitationPair

Fields: pair ID, atomic claim, exact quote, bounded context, source/work/passage
IDs and digests, selectors/locators, discipline/method/source-role IRIs, rights
and licence disposition, transformations, annotation provenance, split group,
and canonical input digest.

### CitationAnnotation

Fields: pair ID, annotator pseudonymous ID/role, label, rationale/span, timestamp,
guideline version, confidence, flags, adjudication state, and supersession link.

### DatasetManifest

Fields: dataset ID/version/digest, source and licence records, pair/class/pack
counts, transformations, exclusions, split-group algorithm, split digests,
annotator roles, agreement results, adjudication record, temporal/OOD holdouts,
known limitations, and approval.

### ModelArtifactManifest

Fields: model ID/version, architecture/base revision, immutable artifact URI,
weights SHA-256/size/licence, dataset manifest digest, training config/code/source
SHA, environment lock digest, output label order, runtime/backend versions,
model-card digest, intended use, prohibited use, and known limitations.

### CalibrationArtifact

Fields: calibration ID, model/dataset/split digests, temperature and numerical
precision, class/discipline thresholds, selective policy, ECE and coverage
metrics, fitting code/environment digest, and approval. It is immutable and valid
only for its bound model and label order.

### CitationSupportDecision

Fields: candidate index, immutable `pair_id`, exact `atomic_claim` and exact
`evidence_span` copied from the input pair, independent claim/span digests,
status (`classified`, `abstained`, `rule_rejected`, `error`), support label or
null, ordered class probabilities, predicted probability, abstention reason,
threshold, calibration/model/dataset/ontology identities and digests, canonical
input digest, runtime/backend versions, deterministic precheck results,
timestamps, and EPG activity. The exact pair bytes and their digests remain
resolvable from the immutable audit pack; a candidate index or aggregate input
digest alone is not sufficient provenance.

The support label is exactly one of `directly_supports`, `partially_supports`,
`context_only`, `contradicts`, or `not_supported`. It is null for abstention,
rule rejection, and error. Laundering or invalid citation is recorded in the
deterministic disposition/reason fields, not represented as a trained class.

Only `classified + directly_supports + all deterministic checks passed` is
eligible for core verification. Eligibility is not itself admission; the
finalizer remains authoritative.

## 4. Source diversity

### SourceFamily

Canonical scholarly work/source identity containing family ID, titles/identifiers,
edition/version members, publisher/owner, venue, author/institution cluster,
region/jurisdiction, language, period, methodology, source type, access mode,
stance/source role, and de-duplication provenance. Mirrors, URLs,
preprints/final versions, and
retrieval providers are members/provenance, not new families.

Every dimension value is a `MetadataValue` with value, evidence status
(`observed`, `externally_verified`, `inferred`, `unknown`), provenance, and
confidence. Unknown or inferred values cannot satisfy mandatory strata.

### DiversityRequirement

Fields: requirement ID, research question/work type, discipline/ontology digest,
applicable dimensions, required strata, minimum family count, concentration and
unknownness limits, counter-position requirement, declaration timestamp, and
approval. Every material dimension has approved maximum HHI/share, minimum
effective-number/balance, coverage and unknown-rate thresholds or an
ontology-linked `not_applicable` rationale. It is frozen before retrieval begins.

### DiversityDimensionReport

Fields: dimension IRI, applicability, sample size, category count/counts/shares,
maximum share, HHI, effective number, normalized balance, required-strata
coverage, unknown/inferred rates, source-count metrics, claim-exposure metrics,
governing worst-case result, threshold, status, and explanations.

### SourceDiversityReport

Fields: report ID, input/source-family/evidence-matrix digests, requirement and
ontology digests, per-dimension reports, duplicate/unknown exclusions, verified
counter-positions, frozen non-gating v1 provider scalar, versioned v2 geometric
composite and formula inputs, overall status (`pass`,
`review_required`, `fail`), exceptions, limitations, and EPG/SDL references.

### DiversityException

Fields: exception ID, affected dimension, bounded-corpus evidence, reason,
approver assertion, approval timestamp, expiry/review date, SDL/EPG bindings, and
required final limitation. It changes workflow disposition, not raw metrics.

## 5. PROV interchange and certification

### EPGv2Document

Fields: document/profile versions, absolute base IRI, namespaces, source scope,
entities, activities, agents, qualified relations, named bundles containing real
statements, typed/language attributes, SWOS extension assertions, and integrity
metadata. IDs are deterministic and bundle-local references are explicit.

### ProvDocument

Canonical internal representation independent of syntax. Known PROV-DM
constructs are typed; SWOS/unknown extension assertions are a lossless typed
multiset. Unsupported constructs fail rather than disappear.

### CanonicalFingerprint

Fields: representation/profile, algorithm and version, semantic normal-form
digest, canonical-byte digest where applicable, assertion/bundle counts, and
resource-limit configuration.

### ProvValidationReport

Fields: syntactic/profile results, PROV-CONSTRAINTS result, SHACL result for RDF,
violations, implementation identity, input digest, elapsed/resources, and status
(`valid`, `invalid`, `unsupported`, `resource_limit`, `error`).

### ProvRoundTripCertificate

Fields: certificate/profile version, source SHA, input EPG/profile/digest,
conversion path, per-leg input/output/fingerprint/tool details, validation
reports, semantic-equivalence and assertion preservation results, independent
oracle result/artifact digest, fixture/corpus hashes, limits, limitations,
timestamp, and final status (`certified`, `failed`, `not_run`). `certified`
requires every mandatory format and oracle leg.

## 6. Multimodal and object analysis

### ObjectRecord

Fields: object ID/type, canonical label, creator/maker assertions, date/culture,
materials/technique/dimensions, collection/current location, external identifiers,
identity confidence, source/rights/provenance, and competing attributions. Object
identity assertions are distinct from visual observations.

### MediaAssetRecord

Fields: asset ID, object ID, role (`surrogate`, `documentary`, `technical`,
`installation`, `detail`, `diagram`, `generated`), MIME/size/dimensions, byte
SHA-256, acquisition URI, IIIF manifest/canvas/annotation references, view and
capture conditions, colour profile, inspection-activity references, mediation
limits, transformations/derivatives, parent digest, content-credential state,
structured accessibility record, and purpose-specific rights.

Rights actions: `view`, `analyse`, `transform`, `create_derivative`, `quote`,
`cache`, `export`, `redistribute`.
Each has `allowed`, `denied`, or `unknown`, evidence, jurisdiction/scope, and
expiry. Unknown is never treated as allowed. Analysis does not imply transform or
derivative permission. A derivative inherits every applicable restriction from
its parents unless a separately provenance-bound grant permits the action.

### ObjectInspectionActivity

Fields: inspection ID, object ID, actor/role, timestamp, location, access method,
conditions, instruments, observed scope, limitations, notes/evidence digest, and
EPG/SDL provenance. Assets and interpretations may reference the activity; they
must not copy its direct-inspection claim onto unrelated analysts or runs.

### AccessibilityRecord

Fields: asset/digest, purpose (`decorative`, `functional`, `evidentiary`), short
alternative, long description when required, region labels, non-image/text-only
fallback, authoring origin (`human`, `machine_assisted`), reviewer/status,
language, created/reviewed timestamps, and invalidation reason. A changed asset,
crop, colour transform, or semantically material derivative invalidates the
record until human re-review. Completeness counts valid reviewed records and
fallbacks over all in-scope non-decorative assets requiring them.

### RegionSelector

Fields: selector type (`iiif_pixel`, `iiif_percent`, `svg`), original selector,
normalized pixel geometry, asset digest/dimensions, coordinate transform,
validation status, and optional human label. Out-of-bounds or non-deterministic
normalization is invalid.

### VisualObservation

Fields: observation ID, exact asset and digest, selectors, observation vocabulary,
literal description, machine/human origin, provider/model/config digests,
confidence/uncertainty, view limitations, review state, and EPG activity. It must
describe visible evidence and cannot encode an unsupported attribution as fact.

### VisualInterpretation

Fields: interpretation ID/type, target object, supporting observation IDs,
discipline/criterion IRIs, contextual textual sources, inference chain,
alternative interpretations, confidence, limitations, reviewer state, and
EPG/SDL bindings.

### CrossModalSupport

Fields: support ID, claim, object/asset/observation/text-source IDs, support status
for asset-to-object, observation-to-claim, and source-to-claim legs, weakest-leg
result, contradiction/limitation, and provenance. A missing required leg blocks
verified support.

### ImageAnalysisRequest and Result

Request fields: work/run, scope, object/assets, permitted operations, target
questions, discipline/ontology, rights policy, resource bounds, provider policy,
and canonical digest.

Result fields: status (`complete`, `partial`, `insufficient`, `denied`, `error`),
request/provider/model/config digests, observations, interpretations, unresolved
questions, per-asset rights and quality outcomes, limitations, timing/resources,
and EPG links. `partial` and `insufficient` never become silent success.

### CapabilityPromotionDecision

Fields: capability/pack/agent, stage, default-enabled flag, exact source SHA,
contract and evaluation digests, paired case IDs, identical non-agent artifact
digests, provider/model/config/prompt/seed/draw identities, baseline/candidate
paired metrics, absolute improvement, paired confidence interval, safety
regressions, mandatory live-result identity, human approval, effective/expiry
dates, rollback trigger, and SDL/EPG evidence. Invalid, unmatched, `NOT_RUN`, or
expired evidence means `disabled`.

## 7. Release audit entities

### ResearchGradeEvaluationSubject

Extends the current exact-subject convention with source SHA, dependency locks,
v2 schema/contract digests, ontology release, classifier/model/calibration,
dataset split, diversity policy/corpus, PROV profile/oracle/corpus, RPM policy and
benchmark, media corpus/provider, and all governed configuration digests.

### ResearchGradeAuditPack

Immutable manifest over all test, metric, benchmark, licence, review, CI,
certificate, limitations, and human-approval artifacts. Verification recomputes
every digest, rejects missing/extra required artifacts, and proves each artifact
binds to the exact candidate head. A head change invalidates the pack.
