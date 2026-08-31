# Feature Specification: SWOS v1.1 Public Proof and Release

> **Superseded release contract:** This historical specification records the
> original public-proof implementation. Its release-approval and signing
> requirements are replaced by `specs/007-simple-release-record/`; use feature
> `007` for the current source-release contract.

**Feature Branch**: `codex/swos-v1.1-public-proof-release`
**Created**: 2026-08-30
**Status**: Draft

## Context

SWOS v1.1 has deterministic runtime, retrieval, governed-store, evaluation and
human-approval foundations. The final programme slice must demonstrate those
controls on public sources and produce a release candidate that an independent
reviewer can reproduce and verify without provider credentials. Release remains
blocked until a separate human decision and an external signing identity bind
the evidence to one selected repository commit.

## Objective

Prove one credential-free public-source project through the real SWOS runtime,
make its governed outcome independently reproducible, and assemble fail-closed
release evidence bound to an exact clean commit without assuming human approval
or a signing identity.

## Commands

The canonical execution, reproduction, candidate-building and verification
commands are maintained in `quickstart.md` and `examples/public-proof/README.md`.

## Project Structure

The checked-in project and expected outcome live under `examples/public-proof/`;
runtime logic lives under `swos_runtime/`; command-line entry points live under
`tools/`; deterministic evidence lives under `tests/runtime/`; the manual-only
workflow lives under `.github/workflows/`.

## Code and Document Style

Python changes follow repository Ruff rules and typed fail-closed interfaces.
JSON evidence is deterministic and human-readable. Documentation distinguishes
specified, tested, demonstrated and certified states and never upgrades a claim
without matching evidence.

## Testing Strategy

Unit tests cover source integrity, real-runtime execution, independent replay,
candidate assembly, SBOM generation, exact-head binding, checksums, approval and
OpenSSH trust failures. Repository validators, coverage, security checks and
workflow-profile inspection remain deterministic and credential-free.

## User Scenarios & Testing

### User Story 1 - Reproduce a public-source project (Priority: P1)

An independent reviewer runs one checked-in public-source project twice in
separate locations and obtains the same governed outcome and semantic proof
fingerprint.

**Independent Test**: Two provider-free executions use the same hash-pinned
public snapshots, both pass all runtime/evaluation gates, and their normalized
proof fingerprints match while retaining distinct run identities.

**Acceptance Scenarios**:

1. **Given** the canonical public-source project, **When** it is executed offline,
   **Then** it produces an approved finalized run and eight passing planes.
2. **Given** an independent output location, **When** the project is reproduced,
   **Then** the semantic fingerprint matches the first run.
3. **Given** a changed source snapshot or declared digest, **When** verification
   runs, **Then** the proof fails closed.

### User Story 2 - Assemble exact release evidence (Priority: P2)

A release engineer selects an exact commit and assembles a complete candidate
containing the public proof, audit pack, SBOM, build provenance, checksums,
conformance report and known-limitations statement.

**Independent Test**: The candidate builder rejects a dirty checkout, unknown or
mismatched selected commit, incomplete proof, missing approval evidence, or any
missing required output.

**Acceptance Scenarios**:

1. **Given** an exact clean selected commit and verified proof, **When** evidence
   is assembled, **Then** every required artifact is content-addressed.
2. **Given** the locked package metadata, **When** the SBOM is generated, **Then**
   direct and locked development components are represented without network use.
3. **Given** incomplete approval or a failed profile, **When** conformance is
   compiled, **Then** the candidate remains blocked and no compatibility claim is
   upgraded.

### User Story 3 - Sign and independently verify release (Priority: P3)

A release authority signs the checksum file outside SWOS, and a separate verifier
uses an explicitly trusted OpenSSH signer identity to determine whether release
is allowed.

**Independent Test**: An ephemeral test signer proves valid signature handling;
wrong namespace, wrong signer, missing signature, altered evidence and approval
replay all remain denied.

**Acceptance Scenarios**:

1. **Given** a complete candidate and trusted detached signature, **When** the
   verifier runs, **Then** it allows only the exact signed artifact set.
2. **Given** no signing key, **When** assembly runs, **Then** SWOS never invents a
   key or claims a signed release.
3. **Given** a valid signature but no separate human approval, **When** verification
   runs, **Then** release remains denied.

## Edge Cases

- Public source pages change after their checked-in snapshots are recorded.
- Two runs have different generated IDs but equivalent governed content.
- A checksum file omits itself, its signature, or an untracked extra artifact.
- A valid signature uses the wrong namespace or an untrusted principal.
- A selected commit exists but is not the checkout's exact clean `HEAD`.
- Offline, live-compatible and portability profiles have different evidence.

## Requirements

### Functional Requirements

- **FR-001**: The repository MUST contain one canonical public-source project with
  stable identifiers, public URLs, source versions or access dates, exact snapshot
  text, rights metadata and SHA-256 digests.
- **FR-002**: Project execution MUST use the real SWOS runtime and MUST NOT require
  provider credentials or paid calls.
- **FR-003**: Every source snapshot MUST verify before execution; altered or
  undeclared content MUST fail closed.
- **FR-004**: The public proof MUST produce a finalized run, all eight evaluation
  planes, an approval pack and a normalized semantic fingerprint.
- **FR-005**: Independent reproduction MUST use a separate output location and
  MUST compare normalized governed content rather than volatile run identifiers.
- **FR-006**: A mismatch in outcome, article, sources, evidence relationships,
  evaluation gates or proof fingerprint MUST fail reproduction.
- **FR-007**: Release assembly MUST require a clean checkout at the exact selected
  commit and record repository, runtime, platform and tool identities.
- **FR-008**: The candidate MUST contain the verified public proof, audit pack,
  CycloneDX SBOM, build provenance, conformance report, known-limitations
  statement, release approval evidence and deterministic checksums.
- **FR-009**: The SBOM MUST derive from committed package and lock metadata and MUST
  not claim components absent from those authorities.
- **FR-010**: Conformance MUST distinguish deterministic, offline release,
  portability and live-compatible profiles and MUST claim only passed profiles.
- **FR-011**: Known limitations MUST include unsupported live profiles, public
  snapshot freshness, deterministic-provider limits, reviewer-independence limits
  and the distinction between demonstration and certification.
- **FR-012**: Checksum signing MUST use an external OpenSSH signing identity and a
  fixed `swos-release` namespace; SWOS MUST NOT generate or retain a release key.
- **FR-013**: Verification MUST require an explicit trusted-principal file and
  MUST fail closed for missing, altered, untrusted or incorrectly namespaced
  signatures.
- **FR-014**: A valid signature MUST NOT substitute for the exact human approval
  record and separation-of-duties gate from feature `005`.
- **FR-015**: Ordinary pull requests MUST remain credential-free; candidate
  assembly/signing MUST be manual-only and MUST not become branch protection.
- **FR-016**: Generated release evidence MUST be independently verifiable by one
  documented command and MUST not depend on hidden service state.

### Key Entities

- **Public Source Snapshot**: Versioned public evidence plus exact content digest.
- **Proof Fingerprint**: Normalized governed outcome used for independent replay.
- **Release Candidate**: Exact-commit evidence directory before external signing.
- **SBOM**: CycloneDX inventory derived from committed dependency authorities.
- **Build Provenance**: Selected commit, environment and builder-input identities.
- **Conformance Report**: Passed and unclaimed release profiles with evidence.
- **Signature Trust Policy**: Principal, public key and fixed signing namespace.

## Success Criteria

- **SC-001**: Two independent offline runs reach the same approved outcome and
  identical proof fingerprint in 100% of deterministic tests.
- **SC-002**: 100% of source mutation, digest mismatch and replay mismatch cases
  fail before a public proof can pass.
- **SC-003**: Every required release artifact is present and represented exactly
  once in the checksum inventory.
- **SC-004**: 100% of missing-signature, altered-artifact, wrong-principal,
  wrong-namespace and absent-approval tests deny release.
- **SC-005**: The release candidate records one exact selected commit and rejects
  dirty or mismatched checkouts in all deterministic tests.
- **SC-006**: The conformance report contains no claim without passed evidence.
- **SC-007**: An independent reviewer can verify the candidate offline with one
  documented command and no provider credential.

## Boundaries

- NIST AI RMF 1.0 and its official companion pages are public primary sources;
  checked-in excerpts are snapshots, not claims that upstream pages are immutable.
- Public proof demonstrates SWOS controls; it does not certify empirical model
  quality because the provider path is deterministic and credential-free.
- A real release remains blocked until the repository owner supplies a separate
  human decision and trusted external signature for the exact candidate.
- Core contracts and schemas remain frozen at `1.0.0`; this feature adds release
  evidence formats outside the frozen contract corpus.
- The reference runtime track is `v1.1`; Research Grade remains `v2.0` and is not
  claimed or implemented by this slice.

## Out of Scope

- Paid or live-provider execution as an ordinary merge prerequisite.
- Generating, escrowing or storing private signing keys.
- Publishing a tag, GitHub Release or package before explicit owner approval.
- Claiming NIST endorsement or treating the Playbook as a mandatory checklist.
