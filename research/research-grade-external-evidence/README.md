# Research Grade External-Evidence Research Index

Status: RESEARCH HANDOFF / NOT RELEASE EVIDENCE
Baseline main SHA: `1f5135969f04a104d4a99764f921d1743d22710f`
Branch: `research/research-grade-external-evidence-2026-09-03`

This folder persists external research and preparation recommendations for the frozen Research Grade closure tasks. It must not be treated as task completion, human approval, exact-head review, portability PASS evidence, oracle execution, audit certification, owner approval or release authority.

## T070 citation support

- `T070-CORPUS-ACQUISITION-RESEARCH.md` — legally conservative scholarly source stack, 6,000-pair acquisition design, adversarial strategy, and temporal/OOD split concern.

## T079 diversity

- `T079-DIVERSITY-ACQUISITION-PLAN.md` — 108-candidate packet strategy and open scholarly metadata substrate.
- `T079-VERIFIED-METADATA-SOURCES.md` — verified OpenAlex/Crossref/OpenCitations/DOAJ rights and operational boundaries.
- `T079-PACKET-CONSTRUCTION-SPEC.md` — concrete packet/source-family/claim-exposure/machine-result/human-review data shape and generator invariants.
- `T079-CANDIDATE-PACKET-SET.json` — deterministic 108 candidate packet identities: 12 per discipline, with two tuning and ten locked candidates per discipline.

## T093–T095 PROV

- `T093-PROV-CORPUS-PLAN.md` — W3C fixture/licensing strategy, oracle pinning and performance/resource corpus design.
- `T093-ORACLE-CANDIDATE-2.2.3.md` — current ProvToolbox 2.2.3 tag/Maven candidate and correction of the earlier 2.2.2 assumption.
- `T093-W3C-FIXTURE-INVENTORY.json` — first exact W3C PROV-CONSTRAINTS catalogue tranche with PASS/FAIL expectations, constraint IDs and per-representation acquisition URIs; hashes/licence-notice verification deliberately pending byte acquisition.

## T111 multimodal

- `T111-MULTIMODAL-CORPUS-PLAN.md` — CC0 institutional image/3D source stack and candidate corpus design.
- `T111-VERIFIED-RIGHTS-SOURCES.md` — verified institution-level rights policies and per-asset admission boundary.
- `T111-ASSET-CANDIDATE-INVENTORY.json` — first concrete institutional candidate tranche with 22 object-level rights-verified works across Smithsonian, NGA and AIC; exact asset bytes/digests and human review remain pending.

## Portability

- `PORTABILITY-RUN-PLAN.md` — six frozen portability cases and evidence-recording sequence.
- `PORTABILITY-EXECUTION-KIT.md` — exact evidence recorder path, subscription-host constraints, current OpenAI model verification and the identified missing second direct-API adapter for `api_provider_changed`.
- `PORTABILITY-SECOND-DIRECT-API-HANDOFF.md` — exact implementation handoff for the missing provider-change path, including CLI/factory/transport/retrieval-contamination/credential/provenance tests and real-run acceptance boundary.

## T127–T129 release closure

- `T127-T129-RELEASE-CLOSURE-PLAN.md` — final exact-head approvals, immutable audit pack, and owner decision sequence.
- `T127-T129-CURRENT-READINESS.md` — current blockers, real coverage-generation path for T128, and owner-only T129 boundary.
- `PARALLEL-CLOSURE-RESEARCH.md` — consolidated cross-track summary.

Immediate production-side T070 action remains: builder should create the source-candidate manifest/acquisition workflow, prepare 6,000 UNLABELLED candidate pairs, and stop at the genuine human annotation/adjudication boundary if reviewers are unavailable.

Concrete parallel next steps from this branch are now mechanical rather than exploratory:

1. populate the 108 T079 candidate packets with real metadata/family/claim-exposure records and run the production diversity path, stopping before human review;
2. harvest the remaining W3C PROV catalogue records, acquire permitted exact bytes, verify notices and compute per-representation SHA-256 values;
3. expand the T111 asset candidate inventory toward the >70-work/>115-rendition pre-review target, then acquire and hash exact permitted assets;
4. hand `PORTABILITY-SECOND-DIRECT-API-HANDOFF.md` to the implementation builder and keep `api_provider_changed` NOT_RUN until a genuine second-provider run passes the canonical validator and official recorder.

None of these research files may be promoted to PASS evidence merely because they exist in Git.