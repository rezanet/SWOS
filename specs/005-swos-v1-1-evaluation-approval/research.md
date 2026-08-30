# Research: SWOS v1.1 Evaluation and Human Approval

## Decision 1: Require a finalized run as the evaluation subject

**Decision**: Runtime-bound mode accepts one finalized run directory, verifies
its manifest, governed stores, frozen artifacts and provenance, and gives the
same subject to every plane.

**Rationale**: The current adapter evaluates fixture dictionaries without
loading runtime output. That proves control-shaped examples, not the released
system.

**Alternatives considered**: Keep fixture-only dispatch and relabel it; rejected
because it cannot support V11-EVAL-001. Run eight unrelated full projects;
rejected because plane results would no longer share one exact subject.

## Decision 2: Keep fixtures as probes, not subjects

**Decision**: Existing rights-cleared fixtures remain negative and rubric probes,
but production assurance controls operate over a verified runtime subject and
the adapter does not own duplicate policy logic.

**Rationale**: Fixtures are valuable anti-regression inputs. The defect is their
use as a substitute for runtime evidence.

**Alternatives considered**: Delete fixtures; rejected because this loses
adversarial and regression coverage. Copy more finalizer logic into the harness;
rejected because two policy implementations would drift.

## Decision 3: Use immutable release-evidence sidecars

**Decision**: Preserve finalized run bytes. Evaluation result, approval pack,
human decision and release-gate result live in a separate directory and bind to
the run manifest and each other by SHA-256.

**Rationale**: Human approval occurs after automated finalization. Rewriting the
run to add approval would invalidate the evidence the human reviewed.

**Alternatives considered**: Rewrite run-control and manifest after approval;
rejected because it changes the approved subject. Store approval only in chat or
GitHub; rejected because it is not portable audit evidence.

## Decision 4: Reuse frozen evaluation and SDL schemas

**Decision**: Emit a schema-valid evaluation result and represent the human
release decision as a schema-valid SDL document containing one release decision.

**Rationale**: These frozen contracts already encode the required plane result,
human approver, rationale, evidence references and policy basis.

**Alternatives considered**: Add new frozen schemas; rejected because the
existing contracts are sufficient and this slice must not revise Core 1.0.0.

## Decision 5: Separate recommendation from authority

**Decision**: Passing evaluation planes may recommend release, but the standalone
release gate remains denied until a valid human SDL decision is present.

**Rationale**: Evaluation is evidence. Human accountability is a distinct
authority boundary required by the constitution and governance policy.

**Alternatives considered**: Let CI create an approval; rejected because an
automated actor cannot satisfy human approval. Treat all public work as
system-approved; rejected because public proof and publication remain release
work, not low-risk internal synthesis.

## Decision 6: Enforce identity separation by stable actor IDs

**Decision**: Approver and author IDs must differ. Evaluation-owner and
contract-owner IDs must differ. Reviewer assurance must identify a reviewer
execution distinct from authoring execution and disclose limitations.

**Rationale**: Role labels alone do not prevent one actor from occupying both
roles.

**Alternatives considered**: Compare display names; rejected as ambiguous.
Accept undeclared independence; rejected because unknown assurance fails closed.
