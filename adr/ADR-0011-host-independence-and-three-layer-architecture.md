# ADR-0011: Host independence and three-layer architecture

**Status:** Accepted  
**Date:** 2026-08-24  
**Deciders:** Governance owner, contract owner, portability owner, maintainers

## Context

SWOS is intended to remain SWOS when the underlying intelligence changes. A run may use a subscription host today, a direct API tomorrow, several models in one workflow, or a future local scholarly model without changing the definition of scholarly validity.

PR #41 exposed four ways vendor identity could otherwise leak into the system: provider-specific release checks, a monolithic provider-shaped orchestrator, scholarly prompts living inside an adapter, and reviewer “independence” inferred from separate calls rather than proved by the execution environment.

## Decision

SWOS adopts the **Host Independence Rule**:

> No SWOS core workflow, governance decision, scholarly instruction, schema, artefact, evaluation gate or release criterion may depend on a specific model vendor, model family, API, authentication mechanism or commercial access mode.

The operational layering is:

1. **SWOS Core** owns the scholarly state machine, deterministic validation, Evidence Matrix, Argument Graph, review/revision policy, scholarly state, EPG, SDL, RPM, governance gates, integrity chain and audit package.
2. **Capability Layer / CapabilityBroker** exposes bounded provider-neutral capabilities through frozen SWOS contracts.
3. **Host / Provider Adapters** translate host, API, replay or local execution facilities into those contracts.

The model is a replaceable worker. SWOS owns stage authority and release authority.

## Canonical instruction ownership

Scholarly stage instructions are SWOS assets, not adapter assets. The canonical instruction set is versioned and hashed. Adapters may translate transport syntax but may not redefine the intellectual task.

```text
SWOS stage contract
+ SWOS canonical instruction
+ governed run state
        ↓
adapter
        ↓
model / host / local worker
```

Replacing an adapter therefore cannot silently replace the Research Planner, Evidence Builder, Citation Auditor, Argument Architect, Drafting Agent, Reviewer Panel or Revision Agent definition.

## Intelligence versus authority

Models may generate text and may provide judgements that cannot be made deterministically. Those judgements are recorded as evidence about a SWOS decision, including judgement type, adapter, host, model, confidence, assurance and independence limitations.

SWOS independently performs available deterministic checks and owns the resulting state transition. A model may say that a citation supports a claim; SWOS still checks source identity, metadata eligibility, exact quote presence, marker validity, required counter-evidence, schema/state conditions, review requirements and integrity evidence.

## Reviewer independence

Reviewer independence is an explicit assurance property. A separate call or separate context does not prove independence or blindness.

An adapter must declare `review_mode`, `independence`, `blind_review_supported` and `independence_limitations`. SWOS decides whether the declaration satisfies the requested assurance profile. The current automatic-delivery profile permits limited independence but does not rename it independent review.

## Host bundle decision

The host bundle is retained and deliberately demoted.

Its normative role is **replay / interchange / debugging / reproducibility**. Live subscription/agent-host execution uses `swos.work-orders.v1`, where SWOS issues bounded work orders and chooses every next stage.

A canonical bundle is emitted from accepted stage outputs so a completed run can be replayed later without the original host. Replay preserves the original execution provenance while declaring that the current execution mode is replay.

## Normative consequences

* SWOS Core must not import provider SDKs or instantiate provider-specific workers.
* Core release gates test SWOS capability/contract evidence, never provider method names.
* `AutonomousSWOS` depends on `CapabilityBroker`; concrete adapter selection belongs outside core.
* Provider/model/authentication/access-mode details are provenance, diagnostics and resource evidence only.
* Canonical stage instructions are SWOS-owned, versioned and hashed.
* Model judgements are advisory governance evidence, not self-approving decisions.
* Reviewer independence/blindness must be explicitly declared and never inferred.
* Unsupported capabilities or inadequate assurance fail closed; silent degradation is prohibited.
* Host-native subscription and API-backed runs are judged by the same SWOS contracts.
* Host-bundle replay does not count as proof of live host autonomy.

## Enforcement

Enforcement is provided by:

* `governance/policies/host-independence.md`;
* `contracts/capability-contract/capabilities-v1.json`;
* `contracts/stage-instruction/stage-instructions-v1.json`;
* `swos_runtime/broker.py` and `swos_runtime/work_orders.py`;
* adapter conformance and final-governance tests;
* the host-independence CI checker;
* portability acceptance through at least one API-backed and one host-native execution mode.

The legacy provider-shaped runtime is preserved only as historical/reference code outside the core authority path so regression evidence is not lost while the architecture is corrected.

## Consequences

Provider integrations become replaceable infrastructure rather than architectural identity. SWOS may mix several conforming workers in one future run. Provider-specific benchmarking remains useful, but it measures an implementation of a capability rather than redefining SWOS correctness.

## Alternatives considered

**Keep one provider as the canonical reference implementation inside core.** Rejected because the reference implementation can quietly become the definition of scholarly validity.

**Treat portability as packaging only.** Rejected because a portable package can still contain vendor-bound prompts and gates.

**Maintain separate SWOS variants per provider.** Rejected because that creates multiple scholarly operating systems instead of one governed SWOS.
