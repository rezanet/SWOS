# Subscription Work-Order Protocol

**Protocol:** `swos.work-orders.v1`

## Principle

**SWOS owns the scholarly process. Models provide capabilities.**

A subscription host is not an API provider. SWOS uses inversion of control: SWOS persists run state, issues one bounded work order, validates the returned result, and alone chooses the next scholarly stage.

## User contract

The user gives one request. Normal intermediate stages require no user orchestration.

```text
swos start request.json --adapter adapters/codex/subscription-capabilities-v1.json
```

The installed host driver loops automatically:

```text
while SWOS status == ACTIVE:
    order = swos next-work <run-dir>
    result = host.fulfil(
        order.capability,
        order.contract,
        order.canonical_instruction,
        order.inputs
    )
    swos submit <run-dir> result.json
```

No paid model API is implied by this protocol.

## Work-order authority

Every work order contains:

* SWOS capability name;
* frozen capability contract;
* canonical SWOS instruction ID, hash and text;
* exact governed inputs for the stage;
* adapter assurance declaration;
* required provenance fields.

The host does not choose, skip, merge or reorder scholarly stages.

## Stage sequence

1. `research_planning`
2. `source_retrieval`
3. `semantic_rerank`
4. `evidence_extraction`
5. `citation_support_audit`
6. `argument_construction`
7. `draft_generation`
8. `prose_transformation`
9. `semantic_verification`
10. `hostile_review`
11. `revision` when required, followed by transformation, semantic verification and re-review

Review loops are bounded. Failure to clear blocker/major findings within the bound becomes `REVIEW_REQUIRED`.

## Deterministic SWOS validation

A model result is a proposal. Before advancing, SWOS performs deterministic checks available at that boundary. These include source identity, metadata eligibility, exact-quote presence, citation-audit completeness, evidence references, source-marker integrity and protected-marker preservation during prose transformation.

Final governance repeats release-critical checks, validates frozen schemas and integrity evidence, and records the release decision in SWOS artefacts.

## Reviewer assurance

The work order carries the adapter's declared review assurance. Separate calls or contexts do not automatically become independent or blind review. SWOS records `review_mode`, `independence`, `blind_review_supported` and limitations and applies the requested assurance policy.

## Model judgement evidence

For judgement-bearing stages, SWOS records model judgement as advisory evidence with adapter, host, model, confidence, assurance, independence information and canonical instruction identity. The judgement cannot self-authorise a SWOS transition or release.

## Host bundle

The canonical host bundle remains part of the architecture, but its role is secondary:

**replay / interchange / debugging / reproducibility**.

```text
LIVE HOST EXECUTION
        ↓
SWOS work-order protocol
        ↓
accepted bounded stage outputs
        ↓
canonical host bundle / audit record
        ↓
replay or independent inspection later
```

The user never hand-assembles the bundle. SWOS emits it from accepted submissions. A completed run can therefore be replayed later without the original host while preserving the original execution provenance.

Replay is explicitly marked `execution_mode: replay`; it is not evidence that a live subscription host was used during replay.

## Separation of authority

The host supplies intelligence and tools. SWOS retains authority for:

* stage transitions and eligibility;
* canonical scholarly instructions;
* capability-contract validation;
* deterministic evidence/citation checks;
* review-loop bounds and assurance policy;
* governance/release decisions;
* provenance and integrity records;
* audit-package completeness.

Changing the worker therefore changes capability implementation, not the definition of SWOS research.
