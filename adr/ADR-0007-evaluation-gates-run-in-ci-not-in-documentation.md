# ADR-0007: Evaluation gates run in CI, not in documentation

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

The evaluation categories were correctly identified in the original plans but existed only as prose. Governance theatre - audit that exists but never blocks - is a named risk.

## Decision

The eight planes run as a CI matrix. `not_run` is treated as `fail`. A release requires every required plane to pass, provenance completeness of 1.0, zero open blocker findings, recorded approvals where required, and a complete audit pack. Waivers are permitted with a reason, an approver and an expiry, recorded as an SDL entry.

## Consequences

* Merges that degrade a plane are blocked automatically.
* CI cost rises; the matrix runs eight jobs.
* Thresholds become a governed artefact - changing one requires evaluation-owner approval.
* A release history containing zero blocked releases becomes a warning sign in its own right.

## Alternatives considered

Rejected: advisory scoring with human judgement at release. Rejected because advisory gates are indistinguishable from no gates once a deadline arrives.
