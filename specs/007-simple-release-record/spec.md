# Feature Specification: SWOS v1.1 Simple Release Record

**Feature Branch**: `codex/swos-simplify-release-gate`
**Created**: 2026-08-31
**Status**: Active

## Context

SWOS already has deterministic runtime tests, a provider-free public proof,
independent reproduction, source and citation hashes, an SBOM, build
provenance and known-limitations reporting. The release path added an
unnecessary multi-file approval workflow and a mandatory detached-signature
trust policy. SWOS is currently a public repository with one maintainer and
does not distribute packages. The release contract should therefore preserve
evidence quality while keeping release authority small and legible.

## Objective

Replace the release-specific approval pack, decision ledger, allowed-signers
policy and mandatory OpenSSH verification with one short JSON release record.
The record binds a maintainer's approval to one exact commit, deterministic
test results, public-proof reproduction, proof/source hashes, date and a short
rationale. Candidate verification remains fail-closed when any binding is
missing or inconsistent. Detached signing is documented only as an optional
future enhancement for package distribution or multiple maintainers.

## Commands

The canonical commands are maintained in `contracts/interfaces.md` and
`quickstart.md`:

```powershell
python tools/run_public_proof.py --project examples/public-proof/project.json --out <proof-dir>
python tools/verify_public_proof.py --project examples/public-proof/project.json `
  --primary <proof-dir> --reproduce-at <independent-dir> --out <reproduction.json>
python tools/create_release_record.py --selected-sha <40-hex-sha> `
  --proof <proof-dir> --reproduction <reproduction.json> `
  --approved-by-id <id> --approved-by-name <name> `
  --approved-at <ISO-8601> --rationale <short-rationale> --out <release-record.json>
python tools/build_release_candidate.py --selected-sha <40-hex-sha> `
  --proof <proof-dir> --reproduction <reproduction.json> `
  --release-record <release-record.json> --out <candidate-dir> --built-at <ISO-8601>
python tools/verify_release_candidate.py --candidate <candidate-dir>
```

## Project Structure

The public proof remains under `examples/public-proof/`. The small release
record contract is implemented in `swos_runtime/release_record.py`; candidate
assembly and verification remain in `swos_runtime/release_evidence.py`.
Operator entry points are under `tools/`, deterministic tests are under
`tests/runtime/`, and the manual public-proof workflow is under
`.github/workflows/swos-release-candidate.yml`.

## Code and Document Style

Python changes use the repository Ruff rules, standard-library-only release
record validation and typed fail-closed interfaces. Release JSON is readable,
stable and deliberately small. Documentation distinguishes `specified`,
`implemented`, `tested`, `demonstrated` and `certified` states. The record is
an approval statement, not a cryptographic identity system.

## Testing Strategy

Tests cover valid record creation, exact-SHA mismatch, missing fields, source
hash mismatch, proof/reproduction mismatch, dirty checkout, candidate tamper,
checksum coverage and unsigned candidate verification. Public-proof tests
confirm that proof execution does not create an approval pack. Workflow and
manifest validators remain deterministic and credential-free.

## User Stories & Testing

### User Story 1 - Record one reviewed release (Priority: P1)

As the repository maintainer, I can write one short record after deterministic
tests and public-proof reproduction pass, so the release decision is visible
without a separate approval ceremony.

**Independent Test**: A complete record contains the selected 40-character SHA,
approval identity, date, rationale, required test results, proof fingerprint
and evidence hashes; an incomplete record is rejected.

### User Story 2 - Verify exact evidence (Priority: P1)

As an independent reviewer, I can verify a candidate without credentials,
keys, provider access or hidden service state.

**Independent Test**: The candidate verifier allows a valid unsigned candidate
and denies altered records, proof, reproduction, source hashes, provenance,
checksums or selected-SHA bindings.

### User Story 3 - Keep future signing optional (Priority: P2)

As a future maintainer, I can add package signing later if SWOS distributes
packages or gains multiple maintainers without changing the current source
release contract.

**Independent Test**: The current candidate contains no signature or
allowed-signers requirement, and the documented verifier succeeds without
either artifact.

## Acceptance Scenarios

1. **Given** a passing public proof and independent reproduction, **when** the
   maintainer creates a record for the exact clean `HEAD`, **then** the record
   validates and names the exact SHA, test results, proof fingerprint, source
   hashes, date and approval.
2. **Given** a record for a different SHA, **when** candidate assembly runs,
   **then** assembly fails before writing a candidate.
3. **Given** a complete record and evidence directory, **when** independent
   verification runs, **then** it allows the candidate without a signature or
   allowed-signers file.
4. **Given** a changed proof, reproduction, source hash, record or candidate
   artifact, **when** verification runs, **then** it denies the candidate.
5. **Given** a live-provider or portability profile that was not executed,
   **when** the conformance report is checked, **then** that profile remains
   `not_claimed`.

## Edge Cases

- The release record is missing, malformed, duplicated or contains unknown
  fields.
- The selected SHA is abbreviated, not `HEAD`, or points to a dirty checkout.
- A proof fingerprint or source/citation hash is changed after approval.
- The reproduction report passes but names a different fingerprint.
- An optional future signature artifact is present but is not part of the
  current required artifact set.
- A provider credential is absent or credits are exhausted; deterministic and
  offline profiles remain the only ordinary release evidence.

## Requirements

### Functional Requirements

- **FR-001**: Release assembly MUST require one full 40-character selected
  commit SHA and a clean checkout whose `HEAD` is exactly that SHA.
- **FR-002**: The release record MUST contain `record_version`, `selected_sha`,
  `decision`, `approved_by`, `approved_at`, `rationale`, `tests`, `proof` and
  `evidence` and MUST reject unknown or missing top-level fields.
- **FR-003**: The record MUST require `decision: approve`, a non-empty approver
  ID and name, a timezone-aware ISO 8601 date and a non-empty rationale.
- **FR-004**: The record MUST require passing `deterministic_pr` and
  `offline_public_release` results and MUST bind the proof fingerprint and run
  ID to `proof-result.json`.
- **FR-005**: The record MUST bind SHA-256 digests for the proof result,
  project, reproduction report and every public source snapshot.
- **FR-006**: Public-proof execution MUST remain provider-free and MUST NOT
  create an approval pack, decision ledger or signing policy.
- **FR-007**: Candidate assembly MUST copy the verified proof, reproduction,
  single release record, SBOM, provenance, conformance report, known
  limitations, checksums and release-record gate.
- **FR-008**: Candidate verification MUST allow a valid candidate without
  `SHA256SUMS.sig`, an allowed-signers file or a signing principal.
- **FR-009**: Candidate verification MUST fail closed for changed or missing
  record, proof, reproduction, source hash, provenance, checksum, release-record
  gate or exact-SHA evidence. The gate MUST have the exact documented schema,
  match the candidate SHA, bind `release-record.json`, and contain no reasons.
- **FR-010**: Conformance MUST distinguish deterministic and offline public
  release evidence from unclaimed portability and live-compatible profiles.
- **FR-011**: Ordinary pull requests MUST remain credential-free and MUST NOT
  schedule paid provider calls; public-proof release evidence remains manual.
- **FR-012**: Documentation MUST state that detached signing is optional until
  SWOS distributes packages or gains multiple maintainers, without making it a
  current release prerequisite.

## Key Entities

- **Release Record**: One small JSON statement binding approval and evidence to
  an exact commit.
- **Proof Evidence**: The normalized provider-free run, evaluation and public
  source/citation hashes.
- **Release Candidate**: A checked evidence directory with one record and
  deterministic checksums.
- **Release-Record Gate**: The machine-readable result of verifying that one
  record matches its candidate evidence.

## Boundaries

- The Core/specification track remains `1.0.0`; the reference runtime remains
  `v1.1`; Research Grade remains `v2.0`.
- The record applies to source releases and does not create package identity,
  key management or a multi-maintainer trust model.
- Scholarly SDL, EPG, RPM, provenance, citation and human-approval controls for
  durable research decisions remain in force; this feature simplifies only the
  release-specific record path.
- A passing deterministic proof demonstrates the stated profile. It does not
  certify model quality, live provider compatibility or source freshness.

## Success Criteria

- **SC-001**: A valid exact-SHA record and candidate verify successfully with
  no provider credential, signature, allowed-signers file or hidden service.
- **SC-002**: All record, proof, reproduction, source-hash, candidate-tamper,
  checksum and selected-SHA negative tests deny or fail before release.
- **SC-003**: The candidate contains one release record and no required
  approval-pack, decision-ledger, signature or allowed-signers artifact.
- **SC-004**: The candidate retains source/citation hashes, a concise SBOM,
  build provenance, conformance results and known limitations.
- **SC-005**: Ordinary workflow inspection confirms no provider credentials or
  paid provider calls are scheduled by pull requests.
- **SC-006**: Spec Kit artifacts, manifest validation, schema checks, Ruff and
  deterministic runtime tests pass at the exact implementation head.

## Out of Scope

- Package signing, key generation, key storage, allowed-signers policies or
  cryptographic maintainer identity.
- Live-provider compatibility as an ordinary PR or release-record prerequisite.
- Changes to the frozen Core contracts, scholarly stores, evaluation planes or
  the historical G-Prose95 planning records.
