# SWOS Constitution

This constitution governs roadmap milestones and other changes that can alter
SWOS's scholarly assurance boundary. It complements the frozen contracts and
schemas; it does not replace them. The long-form philosophical rationale is
recorded in [`VISION.md`](../../VISION.md), while this document states the
engineering obligations that make that vision reviewable.

## Core Principles

### I. Evidence before prose

SWOS MUST establish a research plan, evidence matrix, citation audit and
argument structure before drafting or releasing prose. A fluent result with
thin evidence is a risk signal, not a quality signal.

### II. Contract authority

Frozen contracts, schemas and explicit governance policies are authoritative at
their boundaries. Prompts, examples, implementation convenience and agent
preferences MUST NOT silently redefine them. A changed public contract requires
an explicit versioned decision and compatible tests.

### III. Fail-closed assurance

When evidence, provenance, validation, provider output, permissions or required
metadata are absent or invalid, the system MUST abstain, retain the source, or
fail the gate. It MUST NOT turn an unknown into a PASS by implication.

### IV. Host independence

Core scholarly contracts MUST remain independent of a host, model, retriever,
vendor, subscription or transport. Adapters may vary; the evidence, argument,
citation, review, governance and audit obligations may not.

### V. Human approval

Human responsibility for final scholarly judgement and release is mandatory.
For a source release, one explicit maintainer-owned release record is the
approval authority. Automation may prepare evidence and recommendations, but
it MUST NOT be described as autonomous publication or be the sole approver of a
release.

### VI. Separation of duties

Acquisition, synthesis, verification, governance review and release approval
MUST remain distinguishable roles. A single automated step MUST NOT both create
and certify the evidence on which its own release depends.

### VII. Proof before breadth

SWOS MUST prove one complete, reproducible, auditable path before expanding
scope, agents, disciplines, modalities or product surfaces. Capabilities with
false-originality or over-association risks wait until the evaluation planes
that detect those risks are operational.

### VIII. Exact-head evidence

Every completion, compatibility, release or merge claim MUST identify the exact
commit or immutable artifact it describes. Stale, partial, inferred or
report-only evidence MUST be labelled as such and MUST NOT stand in for
exact-head proof.

## Spec Kit applicability

Spec Kit is required for roadmap milestones, architecture, governance controls,
frozen contracts or schemas, public interfaces and release gates. It is not
required for routine bug fixes, dependency maintenance that preserves
contracts, formatting changes or editorial corrections. Applicable work MUST
retain mutually consistent specification, plan, task and requirements-checklist
artifacts under `specs/`.

## Required development controls

- Tests MUST be written for new behavior and run with the repository-native
  commands before a delivery claim.
- Ordinary pull requests and pushes MUST use deterministic, offline-safe checks;
  provider credentials and paid calls belong only to explicit live workflows.
- Live compatibility claims MUST record the selected exact SHA, fail closed on
  missing credentials/provider failure/missing evidence, and remain outside
  ordinary branch-protection requirements. They are never implied by a source
  release record.
- Source releases MUST retain exact-SHA evidence, deterministic tests,
  public-proof reproduction, source/citation hashes, concise SBOM/provenance
  and known limitations. A single release record MUST contain the exact SHA,
  test/proof results, date, approval identity and rationale. Detached signing
  is optional until SWOS distributes packages or gains multiple maintainers.
- Documentation authority, status, version and supersession MUST be recorded in
  `docs/document-manifest.json` and pass its schema and semantic validator.
- Unrelated dirty work and historical records MUST be preserved. History MUST
  not be rewritten to make a gate appear cleaner.

## Governance

This constitution is a living, versioned governance artifact. Amendments require
a reviewed Spec Kit change when they alter the engineering boundary, a rationale
in the accompanying plan, updated validation evidence, and reciprocal manifest
metadata. Existing contracts and release evidence remain historical records;
they are not retroactively rewritten.

**Version**: 1.1.0 | **Ratified**: 2026-08-29 | **Last Amended**: 2026-08-31
