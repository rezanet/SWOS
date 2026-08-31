# Implementation Plan: SWOS v1.1 Public Proof and Release

> **Historical record:** The release-approval and signing design recorded here
> is superseded by `specs/007-simple-release-record/`. The public-proof and
> evidence implementation remains useful history.

**Branch**: `codex/swos-v1.1-public-proof-release` | **Date**: 2026-08-30
**Spec**: [spec.md](spec.md)

## Summary

Add one hash-pinned NIST public-source project, execute it through the real
provider-free runtime, independently reproduce its semantic outcome, and add a
manual exact-commit release-evidence builder/verifier. Reuse feature `005` for
evaluation and human approval. Use OpenSSH detached signatures through an
external key; never add a signing dependency or private key to SWOS.

## Technical Context

**Language**: Python 3.11+
**Dependencies**: standard library plus existing runtime and JSON Schema stack
**Storage**: immutable files and canonical JSON
**Testing**: `unittest`, Ruff, existing security/coverage validators
**Target**: offline Windows/Linux/macOS; manual GitHub workflow for candidate build
**Constraints**: exact clean Git commit, no PR credentials, frozen Core schemas,
external signing identity, no hidden state.

Version authority remains split deliberately: Core contracts and schemas stay at
`1.0.0`, the reference runtime is `v1.1`, and Research Grade remains `v2.0`.

## Constitution Check

- Evidence precedes release prose through source and candidate manifests.
- Contract authority remains frozen; new release formats are derivative evidence.
- Source, proof, approval, signature and selected-commit mismatches fail closed.
- Public proof and verification are host/provider independent.
- Automation assembles and recommends; humans approve and external identities sign.
- Author, evaluation owner, approver and release signer remain explicit roles.
- One public project proves the path before broader ecosystem claims.
- Every candidate is bound to the exact selected repository head.

## Architecture

```text
examples/public-proof/project.json
        │
        ▼
swos_runtime/public_proof.py ── real AutonomousSWOS run
        │                         + eight-plane evaluation
        ├── proof-a/run
        └── proof-b/run
                 │
                 ▼
tools/verify_public_proof.py ── normalized fingerprint comparison
                 │
                 ▼
swos_runtime/release_evidence.py ── SBOM + provenance + conformance
                 │                   + limitations + SHA256SUMS
                 ▼
external ssh-keygen -Y sign ── SHA256SUMS.sig
                 │
                 ▼
tools/verify_release_candidate.py ── exact trust + approval + signature gate
```

## Project Structure

```text
examples/public-proof/
├── README.md
├── project.json
└── expected-proof.json
swos_runtime/
├── public_proof.py
└── release_evidence.py
tools/
├── run_public_proof.py
├── verify_public_proof.py
├── build_release_candidate.py
└── verify_release_candidate.py
tests/runtime/
├── test_public_proof.py
└── test_release_evidence.py
.github/workflows/swos-release-candidate.yml
specs/006-swos-v1-1-public-proof-release/
```

## Delivery Phases

1. Register feature authority and public source snapshots.
2. Build and test the real-runtime public proof and semantic replay fingerprint.
3. Build and test exact-commit release evidence and deterministic SBOM.
4. Add external OpenSSH signature verification and manual-only workflow.
5. Execute/reproduce the checked-in public proof; reconcile ledger/roadmap.
6. Run exact-head gates and deliver one reviewed PR.

## Requirement Traceability

| Requirements | Planned evidence |
|---|---|
| FR-001, FR-002, FR-003 | Hash-pinned public project, snapshot verifier and credential-free real-runtime tests |
| FR-004, FR-005, FR-006 | Eight-plane proof artifact, normalized fingerprint and independent replay mismatch tests |
| FR-007, FR-008 | Exact clean-head candidate builder and required-artifact verifier |
| FR-009 | CycloneDX generation from `pyproject.toml` and `requirements-dev.lock`, including unlocked-authority rejection |
| FR-010, FR-011 | Evidence-limited conformance and candidate-scoped known-limitations reports |
| FR-012, FR-013 | External OpenSSH `swos-release` signing and explicit allowed-signers verification |
| FR-014 | Feature-005 digest-bound human approval verification remains a separate mandatory gate |
| FR-015 | `workflow_dispatch`-only candidate workflow and ordinary-workflow profile validator |
| FR-016 | Standalone offline candidate-verification command and end-to-end test |

## Release Boundary

This PR can prove the implementation and an unsigned public-proof candidate. It
cannot manufacture repository-owner approval or signature. Actual release allow
requires a subsequent explicit human decision and trusted detached signature for
the merged exact commit; until then the verifier returns `deny`.
