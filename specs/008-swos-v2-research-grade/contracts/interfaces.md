# Contracts: SWOS v2.0 Research Grade

This document defines builder-facing interfaces. Names are normative design
targets; implementation may refine internal helpers but must preserve observable
semantics, failure behavior, version dispatch, and evidence fields.

## 1. Contract versioning

- Existing `1.0.0` schemas/contracts and v1.1 inputs remain byte-compatible.
- New schema `$id` values use a distinct `2.0.0` path/profile.
- `capabilities-v2.json`, `stage-instructions-v2.json`, research-plan v2, Evidence
  Matrix v2, EPG v2, and RPM v2 are parallel artifacts, not in-place edits.
- A dispatcher selects by explicit version. Missing, unknown, or mismatched
  versions fail closed; no guessed downgrade or upgrade is permitted.
- Every serialized result carries its schema/profile version and governing
  artifact digests.

## 2. Programme-memory Python contract

```python
@dataclass(frozen=True)
class ResearchScope:
    repository_namespace_id: str
    programme_id: str
    project_id: str

@dataclass(frozen=True)
class MemoryReadPolicy:
    max_classification: DataClassification
    include_inactive: bool = False
    review_mode: Literal["normal", "governance", "adversarial"] = "normal"

class ResearchMemoryService(Protocol):
    def register_project(self, scope: ResearchScope, manifest: Mapping) -> Binding: ...
    def assess_write(self, scope: ResearchScope, candidate: MemoryCandidate,
                     *, as_of: datetime) -> MemoryAssessment: ...
    def commit_write(self, scope: ResearchScope, *, assessment_id: str,
                     approval: HumanApproval, as_of: datetime) -> MemoryRecord: ...
    def query(self, scope: ResearchScope, query: MemoryQuery,
              policy: MemoryReadPolicy, *, as_of: datetime) -> MemoryQueryResult: ...
    def correct(self, scope: ResearchScope, target_id: str,
                candidate: MemoryCandidate, approval: HumanApproval) -> MemoryRecord: ...
    def supersede(self, scope: ResearchScope, target_id: str,
                  candidate: MemoryCandidate, approval: HumanApproval) -> MemoryRecord: ...
    def resolve_contradiction(self, scope: ResearchScope, contradiction_id: str,
                              decision: SDLDecision) -> Resolution: ...
    def expire_due(self, scope: ResearchScope, *, as_of: datetime,
                   commit: bool = False) -> ExpiryReport: ...
    def delete_payload(self, scope: ResearchScope, item_id: str,
                       approval: HumanApproval) -> Tombstone: ...
```

Public operations reject missing/unregistered scope, cross-scope references,
classification overflow, invalid IDs, stale heads, unresolved evidence, or
policy denial before mutation. Write transactions atomically persist payload,
event, projection, and audit evidence.

### Exchange contract

```python
def export_bundle(scope: ResearchScope, selection: ExportSelection,
                  approval: HumanApproval, limits: BundleLimits) -> ExportReceipt: ...

def inspect_import(bundle: Path, *, destination: ResearchScope,
                   limits: BundleLimits, as_of: datetime) -> ImportInspection: ...

def commit_import(inspection_id: str, inspection_digest: str,
                  approval: HumanApproval) -> ImportReceipt: ...
```

Archive input never chooses its destination. Reject absolute paths, `..`, links,
devices, duplicate normalized paths, excessive file/item/byte counts,
decompression bombs, malformed JSON/NDJSON, checksum failure, chain failure,
missing evidence, and ID/digest collisions. Same ID plus same canonical digest is
an idempotent no-op; same ID plus different digest fails.

### RPM operator CLI

```text
python tools/rpm.py init --repository PATH --namespace ID
python tools/rpm.py register-project --repository PATH --scope-file FILE
python tools/rpm.py verify --repository PATH --scope-file FILE --json-out FILE
python tools/rpm.py expire --repository PATH --scope-file FILE --as-of TIME [--commit]
python tools/rpm.py export --repository PATH --scope-file FILE --selection FILE --out DIR
python tools/rpm.py inspect-import --repository PATH --bundle DIR --destination FILE --out FILE
python tools/rpm.py commit-import --repository PATH --inspection FILE --approval FILE
python tools/rpm.py rebuild-projection --repository PATH --scope-file FILE --verify-only
```

Dry-run is the default for expiry, import inspection, and projection verification.
All commands emit machine-readable status and use nonzero exit codes for denial,
invalidity, resource limits, or partial operation.

## 3. Discipline ontology and critique contract

```python
class DisciplineOntologyRegistry(Protocol):
    def load(self, release_manifest: Path) -> OntologyRelease: ...
    def profile(self, discipline_iri: str) -> DisciplineProfile: ...
    def validate_pack(self, pack_path: Path) -> PackValidationReport: ...

class DisciplineCritic(Protocol):
    def critique(self, *, discipline: DisciplineProfile,
                 research_plan: Mapping, evidence_matrix: Mapping,
                 draft: Mapping) -> DisciplineCritiqueReport: ...
```

Compilation command:

```text
python tools/compile_discipline_ontologies.py \
  --manifest discipline-packs/manifest-v2.json \
  --shapes discipline-packs/ontology/swos-discipline-shapes.ttl \
  --out discipline-packs/compiled/v2 \
  --report artifacts/ontology/compile-report.json
```

Compilation is offline and byte-stable. Validation rejects duplicate notations,
dangling IRIs, invalid weights, forbidden hierarchy cycles, missing mandatory
relations, enum/pack mismatches, graph non-isomorphism, and unknown versions.

Critique output is structured by discipline and criterion. The API has no
single-score pass shortcut. A mandatory criterion failure remains blocking after
aggregation; cross-discipline disagreement remains explicit.

## 4. Citation-support contract

```python
class CitationSupportClassifier(Protocol):
    def classify(self, inputs: Sequence[CitationPair], *,
                 model: VerifiedModelArtifact,
                 calibration: VerifiedCalibration,
                 ontology: OntologyRelease) -> Sequence[CitationSupportDecision]: ...

def admission_eligibility(pair: CitationPair,
                          deterministic_checks: DeterministicCitationChecks,
                          decision: CitationSupportDecision) -> Eligibility: ...
```

Requirements:

- output order matches input order and decisions are batch-size invariant;
- probabilities are finite, within `[0, 1]`, and sum to one within declared
  tolerance;
- model, calibration, dataset, ontology, label-order, and input hashes verify;
- unavailable/corrupt/mismatched artifacts, nonfinite logits, malformed labels,
  OOD inputs, or unsupported ontology versions abstain and block admission;
- `support_level` is null on abstention;
- only core policy can set Evidence Matrix verification state.

Training/evaluation CLI:

```text
python tools/build_citation_dataset.py --manifest FILE --out-dir DIR
python tools/train_citation_classifier.py --config FILE --dataset-manifest FILE --out-dir DIR
python tools/calibrate_citation_classifier.py --model-manifest FILE --calibration-split FILE --out FILE
python tools/evaluate_citation_classifier.py --model-manifest FILE --calibration FILE \
  --locked-test FILE --predictions-out FILE --report-out FILE
```

No command may overwrite an existing immutable artifact directory. Training and
evaluation record exact code SHA, environment, random seeds, hardware profile,
inputs, outputs, and failures. Locked-test labels are not consumed by training or
calibration commands.

## 5. Source-diversity contract

```python
def canonicalize_source_families(sources: Sequence[SourceRecord],
                                 policy: FamilyIdentityPolicy) -> FamilySet: ...

def measure_source_diversity(*, families: FamilySet,
                             admitted_claims: Sequence[EvidenceRow],
                             requirements: DiversityRequirement,
                             policy: DiversityPolicy) -> SourceDiversityReport: ...
```

The implementation is deterministic under input reordering and retrieval-provider
renaming. Adding an edition, mirror, URL, preprint/final variant, or retrieval
channel to an existing family cannot improve diversity. Unknown metadata cannot
improve a score. Every dimension exposes source-count and claim-exposure results;
the gate uses the worse result.

Status rules:

- fewer than 3 families: `fail`;
- 3-4 families: `review_required`;
- 5+ families: evaluate all declared thresholds and mandatory strata;
- a valid narrow-corpus exception changes workflow handling but preserves raw
  failure and final limitation;
- provider count is provenance-only.

## 6. PROV interchange contract

```python
ProvFormat = Literal["prov-json", "prov-n", "prov-o-trig"]

def epg_to_prov(epg: Mapping, *, base_iri: str) -> ProvDocument: ...
def prov_to_epg(document: ProvDocument, *, profile: str) -> Mapping: ...
def serialize_prov(document: ProvDocument, format: ProvFormat) -> bytes: ...
def parse_prov(data: bytes, format: ProvFormat, limits: ResourceLimits) -> ProvDocument: ...
def validate_prov(document: ProvDocument, profile: str) -> ProvValidationReport: ...
def canonical_fingerprint(document: ProvDocument) -> CanonicalFingerprint: ...
def certify_round_trip(epg: Mapping, formats: Sequence[ProvFormat],
                       oracle: OracleConfig,
                       limits: ResourceLimits) -> ProvRoundTripCertificate: ...
```

Mandatory matrix:

```text
EPG -> PROV-JSON -> EPG
EPG -> PROV-N -> EPG
EPG -> PROV-O/TriG -> EPG
PROV-JSON -> PROV-N -> PROV-O/TriG -> PROV-JSON
PROV-O/TriG -> PROV-JSON -> PROV-N -> PROV-O/TriG
```

Each leg proves parse success, applicable constraints validity, semantic normal
form equality, named-bundle correspondence, unchanged extension assertion
multiset, typed/language literal preservation, stable second-round fingerprint,
and independent-oracle acceptance. Unsupported fields are rejected or preserved,
never omitted.

Certification CLI:

```text
python tools/certify_prov_roundtrip.py --epg FILE --profile FILE \
  --formats prov-json prov-n prov-o-trig --oracle-manifest FILE \
  --limits FILE --artifact-dir DIR --certificate-out FILE
```

Exit status is nonzero for `failed`, `not_run`, invalid, unsupported, or
resource-limit results. The independent oracle is mandatory for a release
certificate and optional only for the fast PR fixture suite.

## 7. Multimodal/image-analysis contract

```python
class ImageAnalysisProvider(Protocol):
    def analyze(self, request: ImageAnalysisRequest) -> ImageAnalysisResult: ...

def validate_media_asset(asset: MediaAssetRecord,
                         policy: MediaRightsPolicy) -> AssetValidation: ...
def normalize_selector(selector: RegionSelector,
                       asset: MediaAssetRecord) -> RegionSelector: ...
def evaluate_cross_modal_support(claim: AtomicClaim,
                                 observations: Sequence[VisualObservation],
                                 textual_evidence: Sequence[EvidenceRow]) -> CrossModalSupport: ...
```

Provider requests include only assets and actions allowed by purpose-specific
rights. Adapters cannot set verified claim state. Results preserve machine
observation separately from interpretation and attribution. `partial`,
`insufficient`, `denied`, and `error` propagate as limitations/blocks according
to policy; they are not coerced to empty success.

Supported selectors:

- IIIF Image API 3 `x,y,w,h` and `pct:x,y,w,h`;
- W3C Web Annotation `SvgSelector` within bounded complexity.

Every selector binds exact asset digest and dimensions. Coordinate conversion is
deterministic; invalid, out-of-bounds, ambiguous, or oversized selectors fail.

### Capability promotion contract

```python
def assess_promotion(*, capability: str, pack: str, stage: PromotionStage,
                     baseline: EvaluationSubject,
                     candidate: EvaluationSubject,
                     policy: PromotionPolicy) -> PromotionAssessment: ...

def commit_promotion(assessment: PromotionAssessment,
                     approval: HumanApproval) -> CapabilityPromotionDecision: ...
```

Promotion remains default-off until exact-head evidence proves all blocking
rights, provenance, region, cross-modal, critique, accessibility, deterministic,
and regression gates plus >= 0.08 absolute improvement over pack-only. Any
artifact/head mismatch disables promotion. Rollback preserves evidence and
returns to pack-only.

## 8. Evaluation adapter contract

Every Research Grade fixture invokes production code through the same public
interfaces. Evaluators must not branch on fixture name or copy expected results.

```python
def evaluate_research_grade(subject: ResearchGradeEvaluationSubject,
                            fixtures: FixtureManifest,
                            artifact_dir: Path) -> ResearchGradeEvaluationReport: ...
```

The report contains raw case results, metric numerators/denominators and confidence
intervals, exact artifact identities, deterministic stability draws, resource
use, limitations, and gate decisions. Missing live capability is `NOT_RUN` and
blocks only gates that require it; it is never counted as pass.

## 9. Error and audit contract

All public interfaces return/raise typed errors with stable codes. At minimum:

`invalid_input`, `unknown_version`, `scope_required`, `scope_denied`,
`evidence_unresolved`, `approval_mismatch`, `policy_denied`, `stale_assessment`,
`classification_denied`, `rights_denied`, `contradiction_requires_review`,
`integrity_failure`, `collision`, `unsupported`, `resource_limit`, `not_run`, and
`internal_error`.

Errors must not reveal cross-scope existence. Durable failures produce audit
evidence where safe and never leave partial state. Secrets, raw restricted
content, model credentials, or barred media never enter logs or audit bundles.
