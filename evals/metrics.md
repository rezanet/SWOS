# Metric Definitions

Every metric states its direction and its threshold. A metric without a threshold
is a dashboard decoration.

## Retrieval plane

| Metric | Definition | Direction | Default threshold |
|---|---|---|---|
| `context_precision` | Proportion of retrieved context relevant to the question | higher | 0.70 |
| `context_recall` | Proportion of necessary information the retriever found | higher | 0.80 |
| `hit_rate_at_k` | Proportion of queries with a relevant result in top k | higher | 0.90 at k=10 |
| `mrr` | Mean reciprocal rank of first relevant result | higher | 0.60 |
| `ndcg` | Normalised discounted cumulative gain | higher | 0.70 |
| `source_diversity_index` | Distribution across venue, region, language, date, methodology | higher | 0.50 |
| `seminal_source_recall` | Proportion of field-defining works retrieved | higher | 0.80 |
| `counter_position_recall` | Proportion of known opposing positions retrieved | higher | **> 0, blocking** |

`counter_position_recall = 0` blocks. Retrieving only confirming sources is a
failure, not an efficiency.

## Grounding plane

| Metric | Definition | Direction | Default threshold |
|---|---|---|---|
| `faithfulness` | Claim-level consistency of output with retrieved context | higher | 0.95 |
| `unsupported_claim_rate` | Unsupported material claims / total material claims | lower | **0.0 unmarked, blocking** |
| `overclaim_rate` | Claims whose scope exceeds their evidence | lower | 0.02 |
| `evidence_span_coverage` | Citations with a passage-level span / total citations | higher | **1.0, blocking** |

## Citation plane

| Metric | Definition | Direction | Default threshold |
|---|---|---|---|
| `citation_existence_rate` | Citations resolving to a real source | higher | **1.0, blocking** |
| `metadata_correctness` | Field-level metadata match rate | higher | 0.98 |
| `citation_precision` | Cited-and-supporting / cited | higher | 0.95 |
| `citation_recall` | Cited-and-supporting / should-have-been-cited | higher | 0.85 |
| `citation_f1` | Harmonic mean | higher | 0.90 |
| `laundering_detection_rate` | Seeded laundering cases detected | higher | **1.0, blocking** |
| `quotation_accuracy` | Exact-match quotations | higher | **1.0, blocking** |

## Scholarly plane

Scored by discipline rubric. Dimensions: contribution clarity, argument validity,
method rigour, originality, coverage, interpretive plausibility, counterargument
handling, audience fit. Thresholds are set per pack; a pack sets its own weights
and they must sum to 1.0.

Argument quality is multidimensional - logic and cogency, dialectic and
reasonableness, rhetoric and effectiveness - with sub-dimensions including
acceptability, relevance, sufficiency, opponent sensitivity, credibility, clarity
and arrangement. Rubrics score these separately rather than collapsing them.

## Governance plane

| Metric | Direction | Threshold |
|---|---|---|
| `provenance_completeness` | higher | **1.0, blocking** |
| `mandatory_decisions_with_sdl_entry` | higher | **1.0, blocking** |
| `gate_records_complete` | higher | **1.0, blocking** |
| `approval_coverage` | higher | 1.0 where required |
| `data_classification_violations` | lower | **0, blocking** |
| `disclosure_present` | higher | 1.0 where required |

## Regression plane

Every metric above, compared against the previous release baseline. Blocks on any
degradation beyond tolerance, with the subject versions recorded - prompt
contract, schema pack, agent pack, model, retriever and discipline packs.
Regression without version pinning is noise.

## Memory contamination plane

| Metric | Direction | Threshold |
|---|---|---|
| `false_prior_rejection_rate` | higher | **1.0, blocking** |
| `contradiction_detection_rate` | higher | 0.95 |
| `unsupported_write_rejection_rate` | higher | **1.0, blocking** |

## Adversarial plane

| Metric | Direction | Threshold |
|---|---|---|
| `injection_resistance` | higher | **1.0, blocking** |
| `laundering_detection` | higher | **1.0, blocking** |
| `over_association_detection` | higher | 0.90 |
| `false_originality_detection` | higher | 0.90 |
| `red_team_pass_rate` | higher | 0.95 |

## Research Grade ontology and critique

The v2 path records ontology binding completeness, criterion coverage, evidence
link rate, mandatory-failure preservation, machine-proposed versus human review
state, and unresolved disagreement count. These are separate dimensions. A
display summary is never a universal scholarly score and cannot override a
mandatory criterion failure. The release gate requires every selected pack to
have a non-empty ontology digest, complete stable-IRI bindings, and zero silent
cross-discipline standard levelling.

## Research Grade citation and diversity

Citation support is a five-label calibrated decision with fail-closed abstention.
Only deterministic-precheck-passing, non-abstained `directly_supports` decisions
are admission-eligible. Release thresholds are macro-F1 >= 0.85, contradiction
recall >= 0.95, `not_supported` recall >= 0.90, ECE <= 0.05, selective error <=
0.02, coverage >= 0.70, direct precision and its recorded confidence bounds, and
100% rejection of laundering/invalid-citation blockers.

The v2 diversity report scores distinct canonical source families across each
declared dimension. It reports source-count and claim-exposure HHI, effective
categories, normalized balance, metadata unknownness, required-strata coverage,
counter-position status, and corrective queries. The geometric
`research_grade_composite` must be >= 0.50 and no required dimension may fail.
`source_diversity_index` remains a v1 provider scalar for compatibility only;
provider count is diagnostic and never gates Research Grade.

## Research Grade provenance and multimodal evaluation

| Metric | Definition | Direction | Release threshold |
|---|---|---|---|
| `prov_roundtrip_losslessness` | Semantic normal form is preserved through every advertised serializer/parser leg | higher | **1.0, blocking** |
| `prov_independent_oracle_conformance` | Independent processor agrees with the declared EPG/PROV profile and constraints | higher | **1.0, blocking** |
| `selector_binding_validity` | Bounded selectors match the exact asset digest and dimensions | higher | **1.0, blocking** |
| `multimodal_stability` | Repeated deterministic runs produce byte-identical governed results | higher | **1.0 across 3 runs, blocking** |
| `region_hit_rate` | Reviewed target regions detected, macro-averaged across cases | higher | **>= 0.90** |
| `false_region_rate` | Regions asserted outside reviewed targets | lower | **<= 0.02** |
| `cross_modal_precision` | Correct cross-modal support links / asserted links | higher | **>= 0.98** |
| `cross_modal_recall` | Correct cross-modal support links / reviewed required links | higher | **>= 0.90** |
| `cross_modal_f1` | Harmonic mean of cross-modal precision and recall | higher | **>= 0.94** |
| `visual_grounding_coverage` | Interpretations linked to observations and/or textual evidence | higher | **1.0, blocking** |
| `false_originality_detection` | Seeded unsupported originality/attribution cases detected | higher | **1.0 critical; >= 0.95 overall** |
| `over_association_detection` | Seeded over-association cases detected | higher | **1.0 critical; >= 0.95 overall** |
| `reviewed_accessibility_completeness` | Reviewed assets with complete purpose-appropriate alternatives | higher | **1.0, blocking** |
| `adjudicator_alpha` | Agreement on reviewed multimodal judgments | higher | **>= 0.80** |
| `discipline_weighted_score` | Weighted discipline critique score | higher | **>= 0.80; each mandatory dimension >= 0.70** |

Evaluators record numerators, denominators, thresholds and 95% confidence
intervals. A zero denominator is `not_run`, not a passing zero-risk result.
Provider output can supply observations or diagnostic text, but it cannot
verify a citation, establish identity/attribution/originality, grant rights, or
promote a capability. Any existing blocking regression remains a release
failure regardless of multimodal scores.
