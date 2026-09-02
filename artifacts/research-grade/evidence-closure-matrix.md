# SWOS Research Grade Evidence Closure Matrix

Assessment date: 2026-09-02
Assessed source head: `1f5135969f04a104d4a99764f921d1743d22710f`
Frozen task authority: `specs/008-swos-v2-research-grade/tasks.md`
Task authority SHA-256: `dd1a9af5627b82464f47416b449f5b8c025e46c163c6773d84767a799dce90ae`

This is a preparation-only closure record. The machine-readable authority is [evidence-closure-matrix.json](evidence-closure-matrix.json); this file is its human-readable review projection. Neither file is release evidence. The 11 tasks below remain open, and no frozen task wording, threshold, ordering, contract, or completion marker was changed.

## Decision boundary

The current decision is `BLOCKED_UNCERTIFIED`. `NOT_RUN`, `BLOCKED`, `RESERVED_EXTERNAL`, missing, stale, or unverified material is a release blocker and never a pass. The following fail-closed checks were run or inspected at the assessed head:

| Verifier | Observed result | Required pass signal |
| --- | --- | --- |
| `build_citation_dataset.py` | Exit 2; no licensed pair source; zero outputs | Frozen permitted corpus, split, annotation, adjudication, leakage, checksum, and licence evidence |
| `run_source_diversity_benchmark.py` | Exit 2; zero packets; all denominators zero/null | All locked packets and confidence-bound thresholds pass |
| `certify_prov_roundtrip.py` | Exit 2; corpus manifest has no cases list | Exact pinned independent oracle certifies every case and format |
| `run_multimodal_evals.py` | Exit 2; all observed counts zero | Rights-cleared, independently reviewed corpus meets every frozen minimum |
| `check_portability_acceptance.py --release` | FAIL; six records missing; G-HOST/G-PORT false | Six recorder-produced PASS records plus hosted/review evidence |
| `assemble_research_grade_audit_pack.py --verify-only` | FAIL closed; `reports/coverage.json` missing | Exact manifest/file set/digest/head verification plus external immutable audit |

## Gate matrix

### T070 — Citation corpus

**Exact frozen acceptance criterion**

 > Implement and execute the bounded corpus workflow to acquire permitted pairs, double-annotate, adjudicate, approve, leakage-check, checksum, and freeze actual train/calibration/locked/OOD splits and `DATA-LICENCE.md` in `benchmark/citation-support/manifest.json` using `tools/build_citation_dataset.py`

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| `benchmark/citation-support/manifest.json` | `NOT_RUN`; zero counts/splits/annotators; release blocked below floor |
| `benchmark/citation-support/SOURCE-LICENCE-MANIFEST.json` | `NOT_RUN`; no sources |
| `benchmark/citation-support/DATA-LICENCE.md` | `NOT_RUN`; no frozen corpus |
| Annotation/adjudication/split/dataset-card preparation documents | Present as preparation |
| `tools/build_citation_dataset.py` | Implemented and fail-closed; refused empty licensed-source state |
| Actual split files, annotations, adjudication, leakage, checksums, and approvals | Missing |

**Exact missing evidence**

- A permitted citation-support pair source and source-level licence/right records.
- At least 6,000 pairs; at least 600 per label, 300 per discipline, 1,500 locked-test pairs, 150 locked pairs per label, 75 locked pairs per discipline, and 300 locked adversarial non-direct pairs.
- Actual train, calibration, locked-test, and OOD files with stable pair identity, claim, span, discipline, label, and source identity.
- Separate double annotations, adjudication decisions, annotator separation, leakage-check output, checksums, and independent approval.
- Completed `DATA-LICENCE.md` bound to every included source and permitted use.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | Yes, after the permitted corpus and independent review arrive |
| Live/provider required? | No |
| Licensed or rights-cleared corpus required? | Yes |
| Independent human review required? | Yes |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No |

**Verification**

`python tools/build_citation_dataset.py --manifest benchmark/citation-support/manifest.json --out-dir <output-directory>` must exit 0 and produce a frozen manifest plus every floor, split, annotation, adjudication, leakage, checksum, and licence artifact. Then `.github/workflows/citation-model-evaluation.yml` must be green on the exact evidence head.

**Expected PASS condition**: The permitted corpus is genuinely acquired, independently annotated and adjudicated, leakage-checked, checksummed, frozen, and approved; no field remains `NOT_RUN` or a placeholder.

**Downstream tasks blocked**: `T073`, `T127`, `T128`, `T129`.

### T073 — Locked citation evaluation

**Exact frozen acceptance criterion**

 > Implement locked evaluation with raw predictions retaining exact pair identity/claim/span and per-decision code/config/execution provenance, slice metrics, confidence intervals, gate report, and reproducible packaged 100-pair citation latency measurement proving p95 <=5 seconds on the recorded reference runner in `tools/evaluate_citation_classifier.py`

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| `models/citation-support/v2.0.0/model-card.md` | Present as preparation; not a locked model |
| `artifacts/research-grade/citation-model/model-manifest.json` | Missing |
| `artifacts/research-grade/citation-model/calibration.json` | Missing |
| `benchmark/citation-support/locked_test.jsonl` | Missing because T070 is not frozen |
| Raw predictions, slice metrics, intervals, gate report, latency package | Missing |
| `tools/evaluate_citation_classifier.py` | Implemented but cannot run a valid locked evaluation |

**Exact missing evidence**

- Genuine T070 locked-test inputs and identity bindings.
- Locked model manifest with code, data, configuration, execution, and digest provenance.
- Genuine calibration artifact bound to the locked model and calibration data.
- Raw per-decision predictions preserving exact pair identity, claim, span, and provenance.
- Slice metrics, confidence intervals, gate report, and reproducible 100-pair latency evidence proving p95 <=5 seconds on the recorded reference runner.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | Yes, after T070 and genuine model/calibration inputs exist |
| Live/provider required? | No |
| Licensed or rights-cleared corpus required? | Yes, through T070 |
| Independent human review required? | Yes, for locked evidence/release assurance |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No |

**Verification**

Run `python tools/evaluate_citation_classifier.py --model-manifest artifacts/research-grade/citation-model/model-manifest.json --calibration artifacts/research-grade/citation-model/calibration.json --locked-test benchmark/citation-support/locked_test.jsonl --predictions-out <predictions.jsonl> --report-out <report.json>`. It must exit 0 with exact-identity predictions, provenance, slice metrics, intervals, gate result, and the packaged latency result at or below the frozen p95 threshold. Then run `.github/workflows/citation-model-evaluation.yml` on the exact evidence head.

**Expected PASS condition**: A genuine locked evaluator run produces reproducible, provenance-complete metrics and latency evidence meeting every frozen threshold.

**Downstream tasks blocked**: `T127`, `T128`, `T129`.

### T079 — Discipline-specific diversity packets

**Exact frozen acceptance criterion**

 > Create separate tuning packets plus at least ten locked human-reviewed balanced/concentrated/sparse/narrow/multilingual/historical/method-monoculture/duplicate/fake-diversity packets per discipline in `evals/fixtures/source-diversity/`

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| `evals/fixtures/source-diversity/manifest.json` | `NOT_RUN`; packets empty; 10 required per discipline |
| `evals/fixtures/source-diversity/README.md` | Present as preparation |
| Separate tuning packets for nine supported disciplines | Missing |
| Ten locked packets per discipline in each required category | Missing |
| Source provenance/permission, reviewer separation, and lock records | Missing |

Required categories are `balanced`, `concentrated`, `sparse`, `narrow`, `multilingual`, `historical`, `method_monoculture`, `duplicate`, `fake_diversity`, and `missing_strata`. Supported disciplines are `art_history`, `art_criticism`, `engineering`, `humanities`, `interdisciplinary`, `materials_science`, `philosophy`, `psychology`, and `technical_writing`.

**Exact missing evidence**

- Separate tuning and locked packets for every supported discipline.
- At least ten locked packets per discipline in every required category.
- Independent human review and lock evidence for every packet, with source provenance and any required permission/right basis.
- Reviewer separation proving the builder did not self-review the locked packets.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | Yes, after packet acquisition and review |
| Live/provider required? | No |
| Licensed or rights-cleared corpus required? | Yes, for permitted source material/provenance |
| Independent human review required? | Yes |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No |

**Verification**

Run `python tools/run_source_diversity_benchmark.py --fixtures evals/fixtures/source-diversity/manifest.json --out <report.json>`. It must load every required locked packet without `NOT_RUN`, absent strata, or missing-review state. An immutable external review record must independently record dispositions for every packet and bind the packet digests to the reviewed head.

**Expected PASS condition**: Every required discipline/category packet exists, is locked and independently human-reviewed, and is traceable to permitted source/provenance records.

**Downstream tasks blocked**: `T080`, `T127`, `T128`, `T129`.

### T080 — Production-path diversity benchmark

**Exact frozen acceptance criterion**

 > Implement production-path diversity benchmark and confidence-bound report proving 100% seeded fake/missing-strata detection, material-gap recall >=0.90, adequate/narrow false-block <=0.10, and ordering/provider invariance, with numerators, denominators, and intervals bound to the pre-retrieval requirements, in `tools/run_source_diversity_benchmark.py`

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| `tools/run_source_diversity_benchmark.py` | Implemented; production path calls `swos_runtime.source_diversity.measure_source_diversity` |
| `evals/fixtures/source-diversity/manifest.json` | `NOT_RUN`; nine disciplines have 0 of 10 packets |
| Production benchmark report | `NOT_RUN`; denominators zero/null |
| Confidence-bound/invariance report | Missing |

**Exact missing evidence**

- T079's complete independently locked packet corpus.
- Production-path benchmark output over every required packet and seeded failure case.
- Nonzero numerators, denominators, confidence intervals, and explicit bindings to pre-retrieval strata.
- Evidence of 100% seeded fake/missing-strata detection, material-gap recall >=0.90, adequate/narrow false-block <=0.10, and ordering/provider invariance.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | Yes, after T079 |
| Live/provider required? | No |
| Licensed or rights-cleared corpus required? | Yes, through T079 |
| Independent human review required? | Yes, through T079 and release review |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No |

**Verification**

`python tools/run_source_diversity_benchmark.py --fixtures evals/fixtures/source-diversity/manifest.json --out <report.json>` must exit 0 and report digest-bound nonzero denominators, intervals, all thresholds, and ordering/provider invariance.

**Expected PASS condition**: The production path detects all seeded fake/missing strata, meets recall and false-block bounds, and is invariant under source ordering/provider selection for the locked reviewed corpus.

**Downstream tasks blocked**: `T127`, `T128`, `T129`.

### T093 — PROV fixtures and manifest

**Exact frozen acceptance criterion**

 > Add permitted checksummed valid/invalid/large/adversarial fixtures and manifest in `evals/fixtures/provenance/`

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| `evals/fixtures/provenance/manifest.json` | `NOT_RUN`; cases empty |
| `evals/fixtures/provenance/README.md` | Present as preparation |
| Valid, invalid, large, adversarial, and hostile blank-node fixtures | Missing |
| Per-fixture category, URI/right basis, digest, expected outcome, and approval records | Missing |

**Exact missing evidence**

- Permitted checksummed fixture corpus covering valid, invalid, large, adversarial, and hostile blank-node cases.
- Manifest cases with unique IDs, relative paths, lowercase SHA-256 digests, categories, expected outcomes, and permission/right provenance.
- Independent approval that the corpus is permitted and exercises the intended failure paths.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | Yes, after permitted fixture acquisition |
| Live/provider required? | No |
| Licensed or rights-cleared corpus required? | Yes |
| Independent human review required? | No, but independent fixture/oracle approval is required downstream |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No |

**Verification**

The PROV certification command must load the manifest and validate every permitted fixture path and checksum; it must not encounter an empty `cases` list or `NOT_RUN` status when certification is attempted.

**Expected PASS condition**: All required PROV fixture categories are present, permitted, unique, checksummed, and manifest-bound.

**Downstream tasks blocked**: `T094`, `T095`, `T127`, `T128`, `T129`.

### T094 — Independent ProvToolbox oracle

**Exact frozen acceptance criterion**

 > Pin ProvToolbox identity/licence/digest in `benchmark/provenance/oracle-manifest.json` and run that exact independent oracle in `.github/workflows/prov-certification.yml`

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| `benchmark/provenance/oracle-manifest.json` | `NOT_RUN`; version/licence/artifact URI/digest null |
| Approved local oracle artifact | Missing |
| `benchmark/provenance/oracle-execution-kit.md` | To be added by this closure package as preparation only |
| `.github/workflows/prov-certification.yml` | Present manual workflow |
| Immutable oracle execution/certificate records | Missing |

**Exact missing evidence**

- Maintainer-approved ProvToolbox version and distribution identity.
- Pinned licence and licence evidence for that exact artifact.
- Present permitted relative local oracle artifact and lowercase SHA-256 digest.
- Execution command containing `{artifact}`, `{input}`, `{profile}`, `{formats}`, and `{output}` placeholders.
- Successful independent execution for every corpus case, exact input/profile/format/output bindings, and immutable hosted workflow evidence.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | No; the independent oracle artifact and execution are external prerequisites |
| Live/provider required? | No |
| Licensed or rights-cleared corpus required? | Yes, through T093 |
| Independent human review required? | Yes, for oracle approval and exact-head assurance |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No |

**Verification**

Dispatch `.github/workflows/prov-certification.yml` with the approved inputs. The exact command is also `python tools/certify_prov_roundtrip.py --corpus-manifest benchmark/provenance/manifest.json --profile schemas/research-grade/prov-profile.json --formats prov-json prov-n prov-o-trig --oracle-manifest benchmark/provenance/oracle-manifest.json --limits benchmark/provenance/resource-limits.json --artifact-dir <artifact-directory> --certificate-out <certificate.json>`. It must exit 0 with `status: certified` and an execution record for every case.

**Expected PASS condition**: ProvToolbox is independently pinned, licensed, checksummed, executable through the exact workflow, and preserved as immutable evidence bound to the permitted corpus.

**Downstream tasks blocked**: `T127`, `T128`, `T129`.

### T095 — PROV resource and performance corpus

**Exact frozen acceptance criterion**

 > Add explicit parser/canonicalization CPU-memory-time bounds in `benchmark/provenance/resource-limits.json` plus 1k/10k and hostile blank-node performance/resource corpora in `benchmark/provenance/manifest.json`

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| `benchmark/provenance/resource-limits.json` | Present declaration; not certified by measurements |
| `benchmark/provenance/manifest.json` | `NOT_RUN`; all required corpora not_run; raw measurements empty |
| 1k, 10k, and required large/hostile blank-node corpora | Missing |
| Raw measurements and bound report | Missing |

**Exact missing evidence**

- Permitted 1k and 10k corpora plus the frozen large corpus required by the current manifest, including hostile blank-node cases.
- Per-corpus checksums, exact input identity, parser/canonicalization configuration, and environment provenance.
- Raw CPU, memory, and wall-time measurements plus p95/confidence-bound evidence proving declared bounds and fail-closed behavior.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | Yes, after permitted corpora exist |
| Live/provider required? | No |
| Licensed or rights-cleared corpus required? | Yes |
| Independent human review required? | No |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No |

**Verification**

Run the PROV certification command from T094 with the limits manifest and preserve raw resource measurements. `.github/workflows/prov-certification.yml` must be green on the exact evidence head and retain the performance/resource certificate.

**Expected PASS condition**: Declared bounds are exercised by required corpora, measurements are raw and reproducible, and bounded/fail-closed performance is independently verified.

**Downstream tasks blocked**: `T127`, `T128`, `T129`.

### T111 — Rights-cleared multimodal corpus

**Exact frozen acceptance criterion**

 > Build at least 60 distinct objects/works and 96 rights-cleared renditions, at least 80 atomic region-grounding claims across at least 20 assets, 120 cross-modal pairs, 48 discipline tasks across at least 24 works, and 96 adversarial cases, spanning at least six media/material classes, three mediation conditions, and both art disciplines, plus accessibility manifests, per-asset source/right URI/digest/allowed-use/attribution statements, guidelines, and mandatory `DATA-LICENCE.md` in `evals/fixtures/multimodal/`

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| `evals/fixtures/multimodal/manifest.json` | `NOT_RUN`; every observed count is zero; review not_run |
| `evals/fixtures/multimodal/DATA-LICENCE.md` | Present as preparation; no corpus frozen |
| `evals/fixtures/multimodal/README.md` | Present as preparation |
| Objects, renditions, grounding claims, pairs, tasks, adversarial cases | Missing |
| Accessibility, per-asset rights, guidelines, adjudication, provider review, exact-head binding | Missing |
| Existing audit-pack multimodal report | `NOT_RUN`; zero cases and older pre-freeze source head |

**Exact missing evidence**

- Rights-cleared acquisition meeting all object/work, rendition, class, mediation, and discipline minima.
- Required grounding claims, cross-modal pairs, discipline tasks, and adversarial cases with stable identity.
- Per-asset source URI, rights URI, byte digest, allowed actions, attribution statement, and licence statement.
- Accessibility manifests, guidelines, human adjudication, independent provider review, and exact-head binding.
- Evidence excluding copyrighted scraping, synthetic human judgments, and unlicensed use.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | No; rights-cleared acquisition and independent review are external prerequisites |
| Live/provider required? | No, except an approved provider/execution is needed for evaluation evidence |
| Licensed or rights-cleared corpus required? | Yes |
| Independent human review required? | Yes |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No |

**Verification**

Run `python tools/run_multimodal_evals.py --manifest evals/fixtures/multimodal/manifest.json --artifact-dir <artifact-directory> --provider <approved-provider>`. It must exit 0 with every frozen count and stratum satisfied, raw cases and per-asset rights records present, and required gates passing. Immutable human/provider review records must independently approve rights, accessibility, annotations, adversarial cases, and asset digests.

**Expected PASS condition**: The complete multimodal corpus is genuinely rights-cleared, accessible, independently reviewed, digest-bound, and evaluated against every frozen minimum and adversarial requirement.

**Downstream tasks blocked**: `T127`, `T128`, `T129`.

### T127 — Portability, approvals, CI, and exact-head review

**Exact frozen acceptance criterion**

 > Obtain ADR-plus-two-maintainer schema approval, maintainer-plus-discipline-steward ontology approval, two-maintainer-plus-evaluation-owner fixture approval, maintainer-plus-portability-owner provider-adapter approval, reviewer-criteria approval, six-case `tools/check_portability_acceptance.py --release` PASS evidence, green hosted CI, and independent review on the frozen head; resolve every thread and store identities/dispositions only as immutable external PR/workflow artifacts

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| ADR plus two named maintainer schema approvals | Missing external record |
| Maintainer plus discipline-steward ontology approval | Missing external record |
| Two-maintainer plus evaluation-owner fixture approval | Missing external record |
| Maintainer plus portability-owner adapter approval | Missing external record |
| Reviewer-criteria approval | Missing external record |
| Six recorder-produced case evidence files | Missing; evidence directory has only `.gitkeep` |
| `tools/check_portability_acceptance.py --release` | FAIL; G-HOST/G-PORT false |
| Hosted CI, independent frozen-head review, resolved threads | Missing for this closure |

The six frozen cases are `openai_api`, `codex_chatgpt_subscription`, `claude_code_subscription`, `replay_host_bundle`, `api_provider_changed`, and `model_changed_same_provider`. Subscription cases must prove forbidden-key and zero-paid-call constraints; changed-provider/model cases must prove the required semantic comparison.

**Exact missing evidence**

- Named approval dispositions and identities only in immutable external records.
- Six recorder-produced PASS files from canonical work orders.
- Required credential/subscription environments and proof of key/payment constraints.
- Green hosted CI on the frozen evidence head.
- Independent frozen-head review with every thread resolved and no post-review content change.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | No, not for the complete gate |
| Live/provider required? | Yes, for the direct/subscription/provider/model cases |
| Licensed or rights-cleared corpus required? | Yes, inherited from the preceding evidence gates |
| Independent human review required? | Yes |
| Named maintainer/steward approval required? | Yes |
| Owner approval required? | No; owner approval is T129 |

**Verification**

`python tools/check_portability_acceptance.py --definitions-only` must continue to pass. For each case, run `python tools/validate_autonomous_run.py --canonical <run-directory>` and then `python tools/record_portability_acceptance.py <case-id> <run-directory>`. Finally `python tools/check_portability_acceptance.py --release` must exit 0 with six PASS records and `G-HOST`/`G-PORT` true. Hosted CI and immutable review records must be green and clean on the same head.

**Expected PASS condition**: Every named approval, six-case portability record, hosted check, and independent exact-head review is externally verifiable and all gates pass.

**Downstream tasks blocked**: `T128`, `T129`.

### T128 — External immutable audit pack

**Exact frozen acceptance criterion**

> Finalize and independently verify an external immutable audit pack combining the committed pre-freeze manifest with exact-head CI/review/approval records; if review changes repository content, repeat T126-T128 for the new head without committing post-freeze records to the branch

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| Committed pre-freeze audit-pack manifest | Present but binds an older pre-freeze head |
| Manifest-listed artifact set | Not verifiable; `reports/coverage.json` is missing |
| `tools/assemble_research_grade_audit_pack.py` | Present and fail-closed; exact file set/size/digest/head checks |
| Exact-head CI/review/approval/portability records | Missing |
| External immutable pack and independent verification | Missing |

**Exact missing evidence**

- The legitimate source for `reports/coverage.json`, followed by a reassembled manifest whose entries exactly match the resulting pack. No placeholder file is acceptable.
- Exact-head pack built from the committed pre-freeze manifest and all required evidence artifacts.
- Immutable hosted CI, review, named approval, and six-case portability records bound to that head.
- Independent external verification without repository mutation.
- Prescribed T126-T128 repeat if review changes repository content.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | The mechanical pack can be assembled locally once its legitimate source artifacts exist |
| Live/provider required? | No for assembly; inherited external runs remain required |
| Licensed or rights-cleared corpus required? | Yes, inherited from the pack inputs |
| Independent human review required? | Yes |
| Named maintainer/steward approval required? | Yes, through exact-head pack inputs |
| Owner approval required? | No; owner approval is T129 |

**Verification**

`python tools/assemble_research_grade_audit_pack.py --verify-only` must exit 0 with the exact artifact set, sizes, digests, count, and recorded head. An independent verifier must then confirm the immutable external pack and all exact-head records without repository mutation.

**Expected PASS condition**: The pre-freeze manifest is legitimately complete, the exact-head pack verifies, all external records are immutably bound, and independent verification passes. Any review-induced head change restarts the prescribed final sequence.

**Downstream tasks blocked**: `T129`.

### T129 — Owner merge approval

**Exact frozen acceptance criterion**

> Obtain explicit owner merge approval as an external PR decision while retaining named no-production/no-merge gates; do not create a commit after final exact-head review

**Required artifacts and current status**

| Artifact | Current status |
| --- | --- |
| Final exact-head PR, green checks, resolved review threads | Not eligible; preceding gates open |
| Completed external immutable audit pack | Missing |
| Explicit owner merge approval | `RESERVED_EXTERNAL`; no identity/disposition |
| Named no-production/no-merge gates | Must remain in force |
| Post-review commit prohibition | Not yet at final review |

**Exact missing evidence**

- Completion of T070, T073, T079, T080, T093, T094, T095, T111, T127, and T128.
- Explicit owner merge approval recorded externally on the final exact-head PR.
- Named no-production and no-merge controls retained until that decision, with no commit after final review.

**External requirements**

| Question | Answer |
| --- | --- |
| Can evidence be generated locally? | No |
| Live/provider required? | Yes, through preceding portability/research evidence |
| Licensed or rights-cleared corpus required? | Yes, through preceding evidence gates |
| Independent human review required? | Yes, through T127/T128 |
| Named maintainer/steward approval required? | Yes, through preceding gates |
| Owner approval required? | Yes |

**Verification**

The final exact-head PR must contain the complete external evidence set, green required checks, clean independent review, resolved threads, and the owner's explicit external merge decision. No commit may be created after final exact-head review.

**Expected PASS condition**: The owner decides on merge only after all preceding gates are complete while named no-production/no-merge controls remain enforced.

**Downstream tasks blocked**: none.

## Resumption rule

The next evidence-bearing action is external acquisition, review, approval, or execution—not architecture work. When a valid evidence packet arrives, bind it to its exact digest and head, rerun the prescribed verifier, update this matrix and the corresponding manifest/report, and preserve the fail-closed result if any required field remains absent. Do not mark a task complete from preparation alone.
