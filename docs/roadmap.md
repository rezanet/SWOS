# SWOS Programme Roadmap and Phase 1 Implementation Plan

**Authority:** canonical programme plan for the SWOS roadmap

**Core/specification:** `1.0.0`

**Reference runtime:** `v1.1`

**Research Grade:** `v2.0`

This document is the implementation authority for the programme sequence. The
three supplied roadmap/writing-skills files are research inputs only; they do
not override the constitution, frozen contracts, schemas, governance policies
or this plan. Their hashes and derived documents are recorded in
[`docs/document-manifest.json`](document-manifest.json).

## Programme thesis

SWOS solves an epistemic-control problem rather than a prose-generation
problem. A finished governed work must let an independent reviewer answer:

1. What supports each claim?
2. Where did the evidence and transformation come from?
3. Why was each judgement made, including uncertainty and dissent?
4. Who approved release against which exact head and evidence?

The delivery sequence is **Proof → Portability → Ecosystem → Standardisation**.
Each stage earns the next; breadth is not evidence of correctness.

## Version tracks

| Track | Version | Scope |
|---|---:|---|
| Core/specification | `1.0.0` | Frozen contracts, schemas, evaluation and governance baseline |
| Reference runtime | `v1.1` | Minimal implementation of one complete governed research-writing path |
| Research Grade | `v2.0` | Cross-project research memory, measured classifiers, multimodal and deeper discipline capability |

These are separate promises. Runtime work must not silently revise the Core
specification, and a Research Grade experiment is not a Core guarantee.

## Foundation slice — programme control plane

The foundation slice establishes the documents, validation and workflow controls
needed before the remaining runtime work. It includes:

- brownfield Spec Kit adoption and a constitution;
- the canonical philosophical [`VISION.md`](../VISION.md) and concise README
  pointer;
- this authoritative Phase 1 plan;
- a machine-validated documentation authority/supersession manifest;
- deterministic ordinary PR checks separated from manual live compatibility;
- status vocabulary that distinguishes specified, implemented, tested,
  demonstrated and certified; and
- preservation of historical G-Prose95 planning records.

The foundation does not reimplement PR #41's runtime, portability matrix,
capability contracts, adapters or existing validators. It inventories those
artifacts and reconciles their status instead.

### Foundation dependencies

| Dependency | Why it is required | Output |
|---|---|---|
| Exact `origin/main` baseline | Prevents duplicate runtime work and stale claims | Recorded base SHA and isolated branch |
| Core/specification `1.0.0` | Defines the stable contract boundary | Version-track policy |
| PR #41 reference runtime | Supplies the existing v1.1 implementation substrate | Verified capability inventory |
| Existing deterministic CI | Preserves branch-protection contexts | Ordinary PR profile |
| Existing documentation corpus | Provides authority and history to classify | Complete manifest |

### Foundation gates

The foundation is ready for review only when:

- Spec Kit artifacts contain no template placeholders and agree on scope,
  requirements, tasks and verification;
- `VISION.md`, README, architecture derivative and roadmap use the three version
  tracks consistently;
- manifest schema, coverage and negative-path tests pass for the declared corpus;
- PR-triggered workflows contain no provider credential or paid-call path;
- manual live workflows record an exact selected SHA and fail closed on missing
  credentials, provider failure or missing evidence; and
- the exact-head repository status names what PR #41 implemented without calling
  the full v1.1 programme complete.

## Phase 1 — reference runtime proof

Phase 1 is a dependency-ordered sequence. Each slice receives its own Spec Kit
feature directory and reviewed PR. A slice is not complete because its code
exists; it needs the required tests, artefacts and exact-head evidence.

### 1. Reconcile the runtime contract

**Status:** complete in Spec Kit feature `002`; capability ledger merged.

**Depends on:** foundation slice.

**Outputs:** a capability ledger mapping every v1.1 requirement to existing
runtime code, tests, demonstrations and certification gaps; only verified gaps
become implementation tasks.

**Gate:** no duplicated PR #41 capability and no unverified completion claim.

**Done when:** each capability is labelled `specified`, `implemented`, `tested`,
`demonstrated` or `certified`, with an exact artefact or an explicit blocker.

### 2. Retrieval and citation assurance

**Status:** implementation in Spec Kit feature `003`; exact-head PR evidence required.

**Depends on:** runtime reconciliation.

**Outputs:** cross-encoder reranking reference path; public scholarly retrieval;
citation metadata; retraction and licence checks; quotation verification; and
claim-support classification.

**Gate:** deterministic fixtures prove ranking, metadata, rights and fail-closed
support decisions; live compatibility is a separate explicit profile.

**Done when:** a reviewer can reproduce retrieval-to-support decisions from
recorded inputs, model/retriever identity and exact evidence.

### 3. Governed stores and audit pack

**Status:** planned; begins only after feature `003` merges.

**Depends on:** retrieval and citation assurance.

**Outputs:** file-backed EPG, SDL, RPM, Evidence Matrix and Argument Graph;
correction and supersession records; hash chaining; deterministic audit
verification.

**Gate:** malformed, missing, reordered or tampered records fail closed.

**Done when:** one complete run produces and independently verifies the complete
audit pack without hidden state.

### 4. Evaluation and human approval

**Status:** planned; blocked on governed stores.

**Depends on:** governed stores and audit pack.

**Outputs:** all eight evaluation planes bound to the real runtime, complete
provenance, zero unresolved blockers, separated review evidence and a human
approval record.

**Gate:** no plane is contract-only when the runtime path is claimed, and no
automated component can approve its own output.

**Done when:** a reproducible run passes deterministic gates and is explicitly
approved by the responsible human reviewer.

### 5. Public proof and release

**Status:** planned; blocked on evaluation and human approval.

**Depends on:** evaluation and human approval.

**Outputs:** one independently reproducible public-source project, audit pack,
SBOM, build provenance, signed checksums, conformance report and known-
limitations statement.

**Gate:** exact selected SHA, complete evidence and release approval are present;
live provider evidence is never an ordinary merge prerequisite.

**Done when:** an independent reviewer can rerun the public proof and reach the
same governed outcome or see a recorded, bounded failure.

## What is deliberately deferred

The following remain outside the foundation and early Phase 1 slices:

- ecosystem SDK expansion and broad host integrations;
- multimodal scholarly reasoning before its evidence and evaluation controls;
- enterprise identity, RBAC/ABAC, tenancy, service management and dashboards;
- hosted SaaS/product surfaces;
- novelty estimation, programme-scale gap detection, theory building, analogy
  discovery and automated peer-review response drafting before their required
  evidence history and evaluation planes exist; and
- any claim that v1.1 is complete before all Phase 1 gates pass.

SWOS refuses to become a chatbot, giant prompt, SaaS platform, autonomous
publisher, central memory service or enterprise identity platform. Those are
boundary decisions, not temporary omissions.

## Quality and release profiles

### Deterministic PR profile

Runs on ordinary pull requests and protected pushes. It may use checked-in
fixtures, local files, schemas and deterministic validators. It MUST NOT read
provider credentials or call paid providers. Portability runs in
`--definitions-only` mode. These are the ordinary merge checks.

### Offline release profile

Runs explicitly when a release candidate needs complete local evidence without a
provider. It validates the frozen contracts, all required artefacts, provenance,
audit pack and deterministic portability definitions. It cannot claim live
compatibility.

### Live-compatible release profile

Runs only through `workflow_dispatch` against a user-selected exact SHA. It
requires credentials, records the resolved SHA, fails closed on absent credits,
provider errors or missing evidence, and uploads the evidence as a non-required
artifact. A compatibility claim is valid only for the profile that passed.

## Spec Kit rule

Spec Kit is mandatory for roadmap milestones, architecture, governance controls,
frozen contracts/schemas, public interfaces and release gates. Routine fixes,
editorial corrections, formatting and dependency maintenance that preserve
contracts are exempt. Every applicable slice keeps its specification, plan,
tasks and requirements checklist together under `specs/`; the historical
`tasks/plan.md` and `tasks/todo.md` remain preserved records.

## Definitions of done

| State | Meaning |
|---|---|
| `specified` | Requirement and acceptance evidence are written and reviewed. |
| `implemented` | Code or configuration exists at the exact head. |
| `tested` | Automated deterministic tests pass for the behavior. |
| `demonstrated` | A complete run or reproducible operator scenario produced the expected artefacts. |
| `certified` | An authorized reviewer independently accepted the exact evidence for the stated profile. |

No later state may be inferred from an earlier one. A live result does not
certify deterministic correctness, and a passing unit test does not demonstrate
or certify a complete scholarly run.
