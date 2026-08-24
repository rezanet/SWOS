# Host Independence Policy

**Policy ID:** GOV-HOST-INDEPENDENCE-001
**Status:** Frozen
**Effective date:** 2026-08-24
**Authority:** SWOS Governance Control Plane
**Related ADR:** `adr/ADR-0011-host-independence-and-three-layer-architecture.md`

## Constitutional rule

**SWOS owns the scholarly process. Models provide capabilities.**

No SWOS core workflow, governance decision, schema, artefact, evaluation gate, or release criterion may depend on a specific model vendor, model family, API, authentication mechanism, or commercial access mode.

Changing the model or execution host must not change the definition of what constitutes valid SWOS research.

## Scope

This policy applies to:

* orchestration and scholarly state transitions;
* Evidence Matrix and Argument Graph construction/validation;
* citation and evidence verification;
* reviewer and revision policy;
* EPG, SDL, RPM, audit, integrity, and release controls;
* evaluation fixtures, gates, and acceptance criteria;
* core prompts, contracts, and schemas;
* runtime configuration and capability selection.

## Required architecture

SWOS is divided into three responsibility layers.

### 1. SWOS Core

SWOS Core owns scholarly validity. It includes the research state machine, Evidence Matrix, Argument Graph, citation verification, review/revision policy, scholarly state, EPG, SDL, RPM, governance gates, integrity chain, and audit package.

Core code and contracts MUST:

* express requirements in provider-neutral terms;
* validate capability outputs against SWOS contracts;
* fail closed when required capabilities or assurance are unavailable;
* preserve provider/model identity only as provenance, diagnostics, performance, or cost information.

Core code and contracts MUST NOT:

* import a provider SDK as a condition of core operation;
* require a provider credential as a condition of scholarly validity;
* compare provider, model, API, or authentication names to decide release eligibility;
* weaken or strengthen a SWOS gate because a particular vendor supplied an output.

### 2. Capability Layer

The Capability Layer defines bounded tasks by function, input contract, output contract, assurance requirement, provenance requirement, and failure semantics.

A capability is identified by what SWOS requires, for example `research_planning`, `source_retrieval`, `semantic_rerank`, `evidence_build`, `citation_support_audit`, `argument_build`, `draft_generation`, `semantic_verification`, `hostile_review`, `revision`, or `prose_transform`.

Capability conformance is evaluated against SWOS contracts, never vendor identity.

### 3. Host / Provider Adapters

Host and provider adapters translate available execution facilities into Capability Layer contracts. Examples include Codex/ChatGPT subscription execution, Claude Code subscription execution, OpenAI API, Anthropic API, local models, MCP hosts, replay bundles, and future providers.

Adapters MUST declare capability support and degradation explicitly. Silent degradation is prohibited.

## Release invariants

A release gate MAY require:

* a named SWOS capability;
* a minimum assurance level;
* verified evidence or provenance properties;
* declared reviewer independence;
* deterministic integrity or schema checks;
* bounded cost/usage policy;
* a complete audit package.

A release gate MUST NOT require:

* a particular vendor;
* a particular commercial model name;
* an API key when the required capability is supplied through another conforming execution mode;
* direct API billing when a conforming host-native execution mode is available;
* a provider-specific method string as proof that a SWOS capability executed.

## Provenance

Provider and model information is still required when available. A run should record:

* adapter and execution mode;
* model host and model identifier where exposed;
* capability invoked;
* assurance and independence properties;
* API credential use;
* paid API-call count or equivalent usage evidence when observable;
* token, latency, and cost evidence when observable.

These fields describe **how** a capability was supplied. They do not define whether the scholarly result is valid.

## Conformance test

A host-independent SWOS implementation must be capable of running the same governed acceptance contract through materially different execution bindings without changing the release definition.

At minimum, the v2 portability gate requires:

1. one API-backed execution; and
2. one host-native subscription execution with no provider API credential and no paid provider API calls.

The outputs need not be textually identical. They must be judged by the same SWOS evidence, argument, citation, review, state, governance, integrity, and audit criteria.

## Violations

The following are policy violations:

* provider SDK imports in SWOS Core paths;
* provider/model names embedded in core release decisions;
* provider-specific schemas presented as canonical SWOS artefacts;
* hidden capability degradation;
* declaring host independence solely because a replay bundle can be consumed;
* making one vendor's prompt or response format the canonical scholarly contract.

A violation blocks release until removed or isolated behind an adapter boundary.
