# ADR-0011: Host independence and three-layer architecture

**Status:** Accepted
**Date:** 2026-08-24
**Deciders:** Governance owner, contract owner, portability owner, maintainers

## Context

SWOS already describes itself as host-agnostic and model-agnostic, and its portability specification places host-specific behaviour in adapters. The Autonomous SWOS runtime in PR #41, however, exposed a stronger requirement: portability must govern not only packaging but also the definition of scholarly validity.

A SWOS run must not become valid or invalid because its planning, reranking, evidence construction, drafting, reviewing, or revision capability happened to be supplied by OpenAI, Anthropic, Gemini, a local model, a subscription host, or a direct API. Vendor identity is provenance. It is not scholarly authority.

Without an explicit constitutional boundary, provider details can leak into orchestration and release gates. That would make SWOS behaviour an accidental property of the current model stack rather than a property of SWOS.

## Decision

SWOS adopts the **Host Independence Rule** as a constitutional requirement:

> No SWOS core workflow, governance decision, schema, artefact, evaluation gate, or release criterion may depend on a specific model vendor, model family, API, authentication mechanism, or commercial access mode.

OpenAI, Anthropic, Gemini, local models, subscription hosts, direct APIs, and future execution providers belong outside SWOS Core behind adapters or capability bindings.

Changing the model or execution host **must not change the definition of what constitutes valid SWOS research**. Different providers may produce different candidate outputs, but every candidate is judged by the same SWOS evidence, provenance, argument, review, governance, integrity, and audit contracts.

SWOS is split conceptually and operationally into three layers:

1. **SWOS Core** — owns the scholarly state machine, Evidence Matrix, Argument Graph, citation verification, review/revision policy, scholarly state, EPG, SDL, RPM, governance gates, integrity chain, and audit package.
2. **Capability Layer** — exposes provider-neutral scholarly capabilities through explicit contracts. Capabilities are identified by what they do, never by vendor identity.
3. **Host / Provider Adapters** — Codex, ChatGPT, Claude Code, direct APIs, local models, MCP hosts, and future providers translate host facilities into the Capability Layer contracts.

The model is a replaceable worker. SWOS owns the process and the decision boundary.

## Normative consequences

* SWOS Core must not import provider SDKs or require provider credentials.
* Core release gates must test SWOS capability and evidence properties, never provider names or model identifiers.
* Provider/model/API/authentication/access-mode details may be recorded in provenance and cost/usage evidence, but cannot define correctness.
* Canonical prompts and stage instructions are SWOS assets; adapters may translate transport or host syntax but may not redefine the scholarly contract.
* Unsupported adapter capabilities must fail closed or cause a declared assurance downgrade; silent degradation is forbidden.
* Reviewer independence must be declared as a capability/assurance property rather than inferred from vendor or model names.
* A host-native subscription run and an API-backed run must be eligible for the same SWOS release state when they satisfy the same contracts.
* Host bundles remain valid as replay/interchange evidence, but bundle replay is not the definition of host-native autonomy.

## Enforcement

The rule is enforced by:

* `governance/policies/host-independence.md`;
* `contracts/capability-contract/README.md`;
* `docs/architecture/host-independent-three-layer-architecture.md`;
* adapter conformance tests;
* portability acceptance across at least one API-backed and one host-native execution mode;
* a vendor-leakage CI gate for SWOS Core paths;
* review of every new release criterion for provider-specific assumptions.

Because SWOS precedence is `governance policy > frozen schema > master contract > agent contract > discipline pack > host adapter`, the frozen Host Independence policy is authoritative immediately without mutating the already-frozen v1.0 Master Prompt Contract. The next constitutional contract revision must incorporate this rule explicitly.

## Consequences

* Provider integrations become replaceable infrastructure rather than architectural identity.
* SWOS can run through subscription hosts, APIs, local models, or future systems without changing scholarly validity.
* Some existing runtime code must move or be refactored because OpenAI-specific defaults and release checks currently cross the core boundary.
* Provider-specific benchmarking remains useful, but it measures an adapter/model implementation rather than redefining SWOS correctness.
* Cross-host acceptance becomes a release concern rather than optional portability documentation.

## Alternatives considered

**Keep OpenAI as the canonical reference implementation inside core.** Rejected because a reference implementation can quietly become the definition of correctness.

**Treat host portability as packaging only.** Rejected because a package can be portable while its release gates remain vendor-bound.

**Maintain separate SWOS variants per provider.** Rejected because that creates multiple definitions of scholarly validity and destroys the operating-system boundary.
