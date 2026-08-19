# SWOS v1.0.0 Backout Record

**Status:** tested by non-destructive dry run  
**Release:** `v1.0.0`  
**Test date:** 2026-08-20

## Backout objective

SWOS v1.0.0 is the first public governed release, so there is no earlier published SWOS version to restore. A backout therefore means **withdrawing v1.0.0 from supported distribution while preserving its Git history, tag provenance, audit records and decision trail**. Deleting history is explicitly not a valid rollback mechanism.

## Triggers

Initiate backout if any of the following is discovered after publication:

- a blocking evaluation regression;
- a critical governance or provenance defect;
- a contract/schema defect that invalidates the 1.0.0 boundary;
- a security incident that makes continued distribution unsafe.

## Procedure

1. Halt active promotion and distribution of v1.0.0.
2. Mark the GitHub Release prominently as **WITHDRAWN — DO NOT USE**. Preserve the tag and commit history as evidence.
3. Open an incident under `governance/incident-and-correction.md`.
4. Record the withdrawal as a new SDL `release` entry with `decision: rollback`; do not overwrite the original approval.
5. If the defect can be corrected without breaking the frozen contract/schema boundary, prepare v1.0.1 through the full release gate.
6. If the fix requires a breaking schema/contract change, follow the major-version migration and ADR requirements rather than silently mutating v1.0.0.
7. Re-gate any in-flight work against the replacement supported release.
8. Close the incident only when a regression fixture exists for the failure mode.

## Recovery points

- release-audit base: `bcf096fe87585121729d80e32e672ba772eb06f5`
- immediately preceding main commit: `aaef186e0c4f241203c4c11c0d31b76c2fda3885`
- original package publication commit: `d9256688c6b5707c739596b23f0a9fb0023a8e1b`

All recovery points are immutable Git commits retained in repository history.

## Non-destructive dry-run test

The backout plan was tested without mutating public release state:

1. The release-audit base and its parent were resolved from GitHub commit history.
2. A repository comparison from the original publication commit to the audit base confirmed that the only post-publication changes before release records were CI/DCO files; no contract or schema file changed.
3. The first-release condition was tested explicitly: because no prior supported release exists, the safe rollback target is **no supported release**, not an invented predecessor.
4. The procedure preserves the tag, commits, provenance bundle and SDL history, satisfying the rule that rollback must not erase evidence.

**Test result:** PASS — a withdrawal can be executed without deleting history or misrepresenting a prior release.

## Ownership

Backout authority: governance owner / repository owner.  
Correction releases remain subject to the normal SWOS release gate.
