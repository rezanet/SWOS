# Builder Dispatch: Implement SWOS v2.0 Research Grade

You are the implementation builder for the dedicated Spec Kit feature
`008-swos-v2-research-grade` in the SWOS repository.

## Objective

Implement the complete v2.0 Research Grade milestone exactly as specified in the
feature package. Deliver one cohesive, tested, evidence-backed implementation PR
that is ready for independent review. Do not merge, deploy, enable production
capabilities, or represent a partial phase as Research Grade completion.

The milestone includes:

1. cross-project Research Programme Memory (RPM);
2. formal discipline ontologies and deeper discipline-specific critique;
3. trained, calibrated, abstaining citation-support classification;
4. measured, non-gameable source-diversity controls;
5. independently validated PROV semantic round-trip certification; and
6. justified, rights-aware multimodal image/object analysis with default-off
   specialist-agent promotion.

## Authoritative inputs

Before editing, read these files completely in this order:

1. `AGENTS.md` and `CONTRIBUTING.md`;
2. `specs/008-swos-v2-research-grade/spec.md`;
3. `specs/008-swos-v2-research-grade/research.md`;
4. `specs/008-swos-v2-research-grade/data-model.md`;
5. `specs/008-swos-v2-research-grade/contracts/interfaces.md`;
6. `specs/008-swos-v2-research-grade/plan.md`;
7. `specs/008-swos-v2-research-grade/tasks.md`;
8. `specs/008-swos-v2-research-grade/quickstart.md`; and
9. `specs/008-swos-v2-research-grade/checklists/requirements.md`.

The specification is normative for scope and acceptance. `research.md` records
resolved technical decisions. `data-model.md` and `contracts/interfaces.md`
define builder-facing semantics. `plan.md` owns sequencing and gates.
`tasks.md` is the executable 129-task work breakdown. Do not invent a competing
plan or silently change a threshold. If artifacts conflict, stop that slice,
identify the exact conflict, and propose a reviewed planning amendment.

Use the repository's Spec Kit implementation workflow. Treat the planning PR and
its final reviewed commit as immutable input. Start implementation only from an
up-to-date `origin/main` that contains the approved feature package, unless the
owner explicitly dispatches an isolated implementation branch from the reviewed
planning head.

Within the planning corpus, the builder may change only task execution status
markers from `[ ]` to `[x]`, and only after the task's implementation and evidence
are real. Task wording, identifiers, ordering, scope, requirements, thresholds,
contracts, decisions, and gates remain frozen. Any other planning change requires
a separate reviewed amendment before implementation depends on it.

## Required startup audit

Resolve the repository root from the active Git checkout and work from that live
clone, not a historical copy. On the maintainer's Windows workstation the
canonical clone is normally `C:\GitHub\SWOS`; Linux, CI, and other authorized
clones use their actual checkout root. Create an isolated branch/worktree using
the `codex/` branch prefix. Before any edit, record:

- exact `origin/main` and implementation heads;
- clean/dirty worktree state and ownership of any unrelated changes;
- planning feature and final review commit digests;
- complete proposed diff scope;
- open PRs/branches that may overlap shared files;
- frozen v1.0/v1.1 schema, contract, fixture, and behavior baselines; and
- available credentials, external processors, licensed corpora, human reviewers,
  and role-specific approvers without exposing secrets.

Do not overwrite, reset, clean, or absorb unrelated work. Do not duplicate work
already present: inspect exact files and extend only what is missing.

## Implementation method

Follow `tasks.md` in dependency order. Phase 1 and Phase 2 block every user story.
For every behavior:

1. write the contract/unit/adversarial test first;
2. run it and confirm it fails for the intended reason;
3. implement the smallest governed production path;
4. run focused tests and all affected regressions;
5. make the fixture evaluator call the production interface;
6. record exact artifact, policy, dependency, model, corpus, and source identities;
7. update the task checkbox only when its implementation and evidence are real;
8. commit logical slices with DCO sign-off using `git commit -s`.

Never satisfy an evaluator by branching on fixture names, copying expected
labels, weakening thresholds, accepting unverified evidence, or fabricating a
live/provider/human result. Ordinary CI must remain deterministic, offline,
credential-free, download-free, and paid-call-free.

## Architectural invariants

- Preserve frozen v1.0 contracts/schemas and v1.1 behavior. Add explicit v2
  artifacts, dispatch, ADRs, migrations, warning periods, and compatibility tests.
- Core policy alone owns Evidence Matrix verification and final PASS. Models,
  retrievers, critics, and image providers return evidence or diagnostics only.
- Fail closed for missing scope, policy, rights, classification, evidence,
  ontology, model, calibration, oracle, selector, approval, or resource capacity.
- Keep all scholarly contracts host/model/retriever/provider-neutral. Real
  adapters sit behind versioned protocols and capability declarations.
- Bind all release evidence to the exact candidate SHA. Any head change
  invalidates affected CI, benchmarks, certificates, review, and promotion proof.
- Preserve classification and purpose-specific rights ceilings through storage,
  exchange, inference, export, and public proof.
- Do not claim authenticated multitenancy, physical erasure, W3C certification,
  autonomous attribution, or production readiness beyond the exact evidence.

## Story gates

### US1: cross-project RPM

Implement the local transactional SQLite programme repository, scoped hash-chain
events, rebuildable projections, explicit project registration, authoritative v2
RPM policy, evidence-bound assess/approve/commit protocol for every substantive
operation, governed reads/receipts, lifecycle transitions, safe deletion, and
two-phase bounded exchange. There must be no unscoped public API or lifecycle
mutation bypass. Prove namespace/programme/project isolation, TOCTOU resistance,
crash atomicity, concurrency, tamper detection, deterministic replay, hostile
archive rejection, and the recorded performance goals.

### US2: ontology and critique

Implement reviewed Turtle SKOS/OWL sources, SHACL constraints, JSON-LD context,
deterministic compiled runtime profiles, stable IRI mappings, compatibility and
deprecation behavior, and the required ADR/migration for the v2 discipline
profile. Implement structured criterion-level critique for all nine supported
packs. Preserve per-discipline standards, mandatory failures, disagreements,
evidence links, reviewer authority, and no silent `interdisciplinary` fallback.

### US3: citation support and diversity

Create, license, double-annotate, adjudicate, approve, leakage-check, checksum,
and freeze the actual >=6,000-pair citation corpus and locked/OOD splits. Train
the five semantic support labels, calibrate only on the calibration split, define
selective thresholds, package immutable model/data/calibration cards/manifests,
and satisfy all locked safety, precision, recall, calibration, coverage,
confidence-bound, discipline-slice, and blocker gates.

Keep invalid, laundering, unavailable, uncertain, and OOD results as core-owned
rule rejection or abstention—not trained semantic labels. Only a non-abstained
`directly_supports` decision that also passes every deterministic check may be
eligible for core admission.

Replace Research Grade provider-count diversity with canonical source-family and
claim-exposure measurement. Preserve the frozen v1 scalar as non-gating. Require
approved per-material-dimension thresholds or `not_applicable` rationales,
metadata provenance/completeness, duplicate invariance, counter-positions,
bounded exceptions, locked human-reviewed packets, and benchmark gates.

### US4: PROV certification

Add EPG v2 without rewriting v1. Implement lossless conversion among EPG,
PROV-JSON, PROV-N, and PROV-O/TriG; real bundles and qualified relations;
applicable PROV-CONSTRAINTS and SHACL validation; semantic normal forms; JCS,
RDFC-1.0, and semantic PROV-N fingerprints; bounded hostile-input behavior; and
the full conversion matrix. Require both pinned Python `prov` and a separately
pinned/checksummed ProvToolbox oracle. Advertise only formats that pass the full
independent exact-head certificate. Describe PROV-JSON as a Member Submission and
never claim W3C certification.

### US5: multimodal and object analysis

Separate object, media asset, physical inspection activity, accessibility record,
region selector, visual observation, interpretation, and cross-modal support.
Enforce distinct view/analyse/transform/create-derivative/quote/cache/export/
redistribute rights and conservative derivative inheritance. Implement IIIF 3,
bounded digest-bound selectors, structured accessibility and invalidation, one
real opt-in OpenAI image-input adapter plus deterministic fake, explicit partial/
insufficient/denied/error behavior, and observation-versus-inference guardrails.

Create the governed multimodal `DATA-LICENCE.md`, >=60 distinct objects/works,
>=96 renditions, region/cross-modal/discipline/adversarial cases, per-asset rights
records, human adjudication, and all specified safety/quality metrics. Specialist
agents remain disabled unless versioned contracts, least-privilege tools,
role-separated routing, executable pack fallback, successful exact-head live
evidence, identical paired evaluation subjects, >=0.08 improvement, positive
lower 95% confidence bound, and every safety/regression gate pass.

## External and human gates

Do not substitute simulation for a required external or human result. If a model,
licensed corpus, live image provider, independent PROV oracle, discipline steward,
evaluation owner, portability owner, two-maintainer schema/fixture quorum, or
owner decision is unavailable:

- continue all safe independent work;
- record `NOT_RUN` or the exact named blocker;
- keep the affected capability disabled;
- do not lower or bypass the gate; and
- hand off the smallest bounded next action needed from the responsible person.

Never put credentials, restricted content, barred media, or secrets in config,
logs, artifacts, chat, commits, PRs, or memory.

## Verification and PR delivery

Run the commands in `quickstart.md` plus every repository-required schema,
contract, runtime, prose, eight-plane evaluation, Ruff, coverage, security,
dependency, portability, offline, deterministic-stability, manifest, benchmark,
and audit-pack check. Preserve raw outputs and metric calculations where the plan
requires immutable evidence.

Before opening the implementation PR:

1. freeze one release-candidate SHA;
2. ensure the worktree and complete intended diff are understood;
3. assemble and independently verify the Research Grade audit pack;
4. map every FR-001..FR-040 and SC-001..SC-012 to exact artifacts;
5. record limitations and named no-merge/no-production gates;
6. push one cohesive signed-off implementation branch; and
7. open one ready-for-review PR linking this feature and all exact-head evidence.

Then obtain every repository role-specific review quorum named in the plan plus a
fresh independent review of the exact final head. Store hosted CI, approvals,
review records, and the final combined audit pack as immutable external PR/
workflow artifacts bound to that head; do not commit post-freeze evidence back to
the reviewed branch. Resolve every actionable thread. If review causes any
repository change, create a new candidate, rerun invalidated evidence, and repeat
the exact-head external review cycle. Stop with the PR open and reviewed. Do not
merge or deploy without a separate, explicit owner instruction.

## Required final handoff

Return:

- implementation branch, PR URL, base SHA, and final head SHA;
- concise delivered-scope summary by US1–US5;
- exact files/contracts/schemas/policies/models/corpora created or changed;
- task completion count and any unchecked task with reason;
- exact local and hosted checks with result and immutable evidence links;
- benchmark, classifier, diversity, critique, PROV, RPM, and multimodal results;
- review identities, required quorums, thread resolution count, and final review
  head;
- compatibility, security, rights, classification, and limitation statement;
- named no-merge/no-production blockers; and
- the precise next owner action.

Do not claim completion from code presence, partial tests, old artifacts, a stale
review, a bot acknowledgement, or a green subset of checks.
