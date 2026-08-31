# Specification Quality Checklist: SWOS v1.1 Simple Release Record

**Purpose**: Confirm the release simplification is complete, reviewable and
consistent with the SWOS constitution.
**Created**: 2026-08-31
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Requirements describe release outcomes rather than implementation trivia.
- [x] The single-record scope is explicit and bounded.
- [x] Exact-SHA, evidence, human approval and future-signing boundaries are explicit.
- [x] Version tracks `1.0.0`, `v1.1` and `v2.0` are consistent.

## Requirement Completeness

- [x] No unresolved clarification markers remain.
- [x] Every functional requirement has a deterministic acceptance path.
- [x] Missing, tampered and mismatched evidence cases are defined.
- [x] Ordinary PR, offline release and live-compatible profiles are separated.

## Implementation Acceptance

- [x] FR-001 exact clean selected SHA is checked.
- [x] FR-002 and FR-003 record shape, decision, approver, date and rationale are checked.
- [x] FR-004 and FR-005 proof, reproduction and source/citation hashes are checked.
- [x] FR-006 public proof does not create the former approval machinery.
- [x] FR-007 candidate artifact set retains the useful release evidence.
- [x] FR-008 unsigned candidate verification succeeds.
- [x] FR-009 altered or missing bindings fail closed.
- [x] FR-010 conformance profile claims remain bounded.
- [x] FR-011 ordinary workflows remain credential-free and public proof is manual.
- [x] FR-012 optional future signing is documented without being required.

## Review Readiness

- [x] `swos_runtime/release_approval.py` and its release CLI routes are removed.
- [x] No current release command accepts `--allowed-signers` or `--principal`.
- [x] No current release candidate requires `SHA256SUMS.sig`.
- [x] Historical specifications remain available as superseded records.
