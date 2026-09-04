# Research Grade External-Evidence Research Index

Status: RESEARCH HANDOFF / NOT RELEASE EVIDENCE
Baseline main SHA: `1f5135969f04a104d4a99764f921d1743d22710f`
Branch: `research/research-grade-external-evidence-2026-09-03`

This folder persists external research and preparation recommendations for the frozen Research Grade closure tasks. It must not be treated as task completion, human approval, exact-head review, portability PASS evidence, oracle execution, audit certification, owner approval or release authority.

## T070 citation support

- `T070-CORPUS-ACQUISITION-RESEARCH.md` — legally conservative scholarly source stack, 6,000-pair acquisition design, adversarial strategy, and temporal/OOD split concern.
- `T070-IMPORT-COMPLETED-REVIEWS.py` — fail-closed importer for future human rights reviews, double annotations, and adjudications; it cannot create labels or release evidence.

## T079 diversity

- `T079-DIVERSITY-ACQUISITION-PLAN.md` — 108-candidate packet strategy and open scholarly metadata substrate.
- `T079-VERIFIED-METADATA-SOURCES.md` — verified OpenAlex/Crossref/OpenCitations/DOAJ rights and operational boundaries.
- `T079-PACKET-CONSTRUCTION-SPEC.md` — concrete packet/source-family/claim-exposure/machine-result/human-review data shape and generator invariants.
- `T079-CANDIDATE-PACKET-SET.json` — deterministic 108 candidate packet identities: 12 per discipline, with two tuning and ten locked candidates per discipline.
- `T079-BUILD-REVIEWER-PACKETS.py` and `T080-BUILD-LOCKED-BENCHMARK-INPUT.py` — isolated packet preparation and human-reviewed locked-input validation; the committed packets remain unreviewed.

## T093–T095 PROV

- `T093-PROV-CORPUS-PLAN.md` — W3C fixture/licensing strategy, oracle pinning and performance/resource corpus design.
- `T093-ORACLE-CANDIDATE-2.2.3.md` — current ProvToolbox 2.2.3 tag/Maven candidate and correction of the earlier 2.2.2 assumption.
- `T093-W3C-FIXTURE-INVENTORY.json` — first exact W3C PROV-CONSTRAINTS catalogue tranche with PASS/FAIL expectations, constraint IDs and per-representation acquisition URIs; hashes/licence-notice verification deliberately pending byte acquisition.
- `T094-BUILD-PROVTOOLBOX-PACKAGE.py`, `T094-ORACLE-ADAPTER.py`, and `T094-PROVTOOLBOX-PACKAGE-MANIFEST.json` — pinned 2.2.3 package handoff and safe extraction/adapter checks; independent execution and approval remain pending.
- `T095-GENERATE-RESOURCE-CORPORA.py` and `T095-MEASURE-RESOURCE-CORPORA.py` — deterministic 1k/10k/100k and hostile blank-node corpora with bound source identity, seed, parameters, and CPU/RSS/wall limits. `benchmark/provenance/manifest.json` is generated/not measured, not a PASS.

## T111 multimodal

- `T111-MULTIMODAL-CORPUS-PLAN.md` — CC0 institutional image/3D source stack and candidate corpus design.
- `T111-VERIFIED-RIGHTS-SOURCES.md` — verified institution-level rights policies and per-asset admission boundary.
- `T111-ASSET-CANDIDATE-INVENTORY.json` — first concrete institutional candidate tranche with 22 object-level rights-verified works across Smithsonian, NGA and AIC; exact asset bytes/digests and human review remain pending.
- `T111-PREPARE-REVIEW-CORPUS.py` and `T111-IMPORT-COMPLETED-REVIEWS.py` — exact primary/alternate/derived rendition reconciliation and fail-closed six-leg human-review import. `T111-REVIEW-CANDIDATE-MANIFEST.json` remains a pre-review candidate only.

## Portability

- `PORTABILITY-RUN-PLAN.md` — six frozen portability cases and evidence-recording sequence.
- `PORTABILITY-EXECUTION-KIT.md` — exact evidence recorder path, subscription-host constraints, current OpenAI model verification and the identified missing second direct-API adapter for `api_provider_changed`.
- `PORTABILITY-SECOND-DIRECT-API-HANDOFF.md` — exact implementation handoff for the missing provider-change path, including CLI/factory/transport/retrieval-contamination/credential/provenance tests and real-run acceptance boundary.

## T127–T129 release closure

- `T127-T129-RELEASE-CLOSURE-PLAN.md` — final exact-head approvals, immutable audit pack, and owner decision sequence.
- `T127-T129-CURRENT-READINESS.md` — current blockers, real coverage-generation path for T128, and owner-only T129 boundary.
- `T127-T128-CLOSURE-PREFLIGHT.py` — deterministic closure preflight that separates repository verification from external audit certification and fails closed on missing evidence.
- `PARALLEL-CLOSURE-RESEARCH.md` — consolidated cross-track summary.

Deterministic T070 pre-annotation preparation is complete: the persisted package binds PR #66 exact candidate head `e4cf7afca8cbb6712064e66d8ed001a0e3700e95`, 508 source records, 1,200 claim families, 6,000 UNLABELLED candidate pairs, and 6,000 unique source/claim/quote tuples. Its status remains `READY_FOR_GENUINE_HUMAN_REVIEW_NOT_T070_EVIDENCE` with `release_evidence: false`; the next action is genuine human source-rights review, double annotation, and adjudication. Do not add labels or mark T070 complete from this preparation.

The next evidence actions from this branch are bounded and external rather than exploratory:

1. T070: obtain genuine human source-rights review, two independent annotations per pair, and adjudication through the importer; leave T070 open until all exact bindings and human decisions are present;
2. T079/T080: obtain independent human packet reviews and a real locked benchmark input, then run the source-diversity evaluation;
3. T093–T095: acquire the remaining W3C PROV bytes and licence evidence, independently approve/install the ProvToolbox 2.2.3 oracle, and run the approved resource-limit measurement command;
4. T111: obtain all six required human multimodal review legs over the prepared candidate corpus;
5. T127–T129: record six genuine portability environments, named approvals, exact-head independent review, genuine coverage/audit-pack evidence, and final owner authority. Keep `api_provider_changed` NOT_RUN until a genuine second-provider run passes the canonical validator and official recorder.

None of these research files may be promoted to PASS evidence merely because they exist in Git.
