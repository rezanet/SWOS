# T127–T129 Current Readiness

Status: RELEASE BLOCKED / PREPARATION ONLY
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`
Verified: 2026-09-04

## T127

T127 cannot begin its final exact-head approval sequence until T070/T073, T079/T080, T093/T094/T095, T111 and all six portability cases are genuine.

Current research additionally identified a concrete portability implementation gap: the frozen `api_provider_changed` case requires a second `direct_api` adapter different from `openai_api`, while current `swos research-write` exposes only `openai-api` and no `adapters/anthropic-api/` implementation is checked in. See `PORTABILITY-EXECUTION-KIT.md`.

This must be resolved before T127 can ever satisfy the six-case release gate.

After all upstream evidence is complete, T127 must bind one immutable candidate head to:

- ADR + two-maintainer schema approval;
- maintainer + discipline-steward ontology approval;
- two-maintainer + evaluation-owner fixture approval;
- maintainer + portability-owner provider-adapter approval;
- reviewer-criteria approval;
- six recorder-produced portability PASS records;
- hosted CI PASS;
- independent exact-head review;
- zero unresolved review threads.

The deterministic preflight accepts only external JSON records using
`swos.external-evidence-record.v1`, with a full exact-head binding, an explicit
disposition, and an HTTPS immutable external URI. File presence alone is not
accepted as approval, review, or hosted-CI evidence.

Do not request these final approvals while fixture/oracle/corpus content is still changing.

## T128

The audit-pack implementation itself is content-addressed and fail-closed: verification enumerates the directory, rejects missing/extra files and re-hashes every artifact.

The current known mechanical failure is the missing `reports/coverage.json` within the pre-freeze pack.

The preflight keeps deterministic audit-pack verification separate from the
independent external audit certification, which remains `NOT_RUN` until an
external auditor records that decision.

Repository evidence shows the quality process previously generated real coverage with a command equivalent to:

```bash
python -m coverage json -o artifacts/research-grade/coverage.json
```

The Makefile/quality flow also runs coverage before applying the configured minimum and critical-module checks.

Therefore the T128 repair is NOT to add a placeholder `reports/coverage.json`.

At the final exact candidate head:

1. erase prior coverage state;
2. run the authoritative test suites under coverage;
3. generate fresh JSON coverage output;
4. run the existing coverage floor/critical-module validator;
5. stage/copy that exact output into the external audit-pack source layout as `reports/coverage.json`;
6. bind file size and SHA-256 through `assemble_research_grade_audit_pack.py`;
7. include all other genuine exact-head external records;
8. independently verify the resulting pack with `--verify` and `--expected-code-sha`.

If any file or digest changes, rebuild the pack. If review changes repository content, restart the exact-head sequence.

## T129

No technical research can complete T129.

T129 remains an explicit external owner decision after T128 passes. The decision must bind:

- exact candidate commit SHA;
- owner identity;
- explicit merge disposition;
- timestamp;
- confirmation that no-production/no-merge controls remained in force through the decision.

No research note, automation result or builder report counts as T129 approval.

## Readiness summary

- T127: BLOCKED BY UPSTREAM EVIDENCE + SIX PORTABILITY RUNS + SECOND DIRECT-API PATH + HUMAN APPROVALS/REVIEW.
- T128: ASSEMBLER READY; REAL FINAL-HEAD COVERAGE AND EXTERNAL RECORDS ABSENT.
- T129: OWNER-ONLY, NOT YET REQUESTABLE.

This file is a readiness record only. It is not release evidence.
