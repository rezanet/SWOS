# Host Independence Policy

**Policy ID:** GOV-HOST-INDEPENDENCE-001  
**Status:** Frozen  
**Effective date:** 2026-08-24  
**Authority:** SWOS Governance Control Plane  
**Related ADR:** `adr/ADR-0011-host-independence-and-three-layer-architecture.md`

## Constitutional rule

**SWOS owns the scholarly process. Models provide capabilities.**

No SWOS core workflow, scholarly instruction, governance decision, schema, artefact, evaluation gate or release criterion may depend on a specific model vendor, model family, API, authentication mechanism or commercial access mode.

A model may be replaced, upgraded, mixed with other models, or supplied locally without changing the definition of valid SWOS research.

## Required runtime architecture

```text
User request
    ↓
SWOS Core / scholarly state machine
    ↓
CapabilityBroker
    ↓
selected adapter(s)
    ↓
model / host / retrieval / tool capability
    ↓
SWOS work-order result validation
    ↓
SWOS governance
```

SWOS Core owns stage eligibility, deterministic validation, evidence/argument structures, review policy, EPG, SDL, RPM, integrity, audit and release decisions. Adapters own transport and execution details only.

### Capability identity

SWOS asks whether an adapter can satisfy a named SWOS capability contract, not which vendor it belongs to. A validity gate therefore tests properties such as:

```text
capability == semantic_rerank
contract == swos.semantic-rerank.v1
contract_passed == true
```

A provider-specific method string is implementation/debug provenance only and cannot satisfy a release gate by itself.

## Canonical scholarly instruction ownership

Research Planner, Evidence Builder, Citation Auditor, Argument Architect, Drafting Agent, semantic verifier, Reviewer Panel and Revision Agent instructions are canonical SWOS assets.

The normative flow is:

```text
SWOS capability contract
+ SWOS canonical instruction id/hash/text
+ governed run state
        ↓
adapter transport translation
        ↓
model / host
```

Adapters MAY translate message roles, JSON schema syntax, tool-call format or host-specific packaging. They MUST NOT redefine, weaken, extend or privately own the scholarly instruction.

A stage result must preserve the canonical instruction ID and hash in provenance so a replay can prove which SWOS instruction governed the work.

## Intelligence and authority

**Models may propose. SWOS decides.**

Model judgement is not itself a governance decision. Where model judgement is used, SWOS records at minimum:

* `judgement_type`;
* capability and contract;
* adapter;
* host;
* model identifier where exposed;
* confidence where supplied;
* assurance declaration;
* reviewer independence and limitations where relevant;
* canonical instruction ID/hash;
* authority classification showing that the judgement is advisory evidence for SWOS governance.

SWOS independently performs every deterministic check available to it before permitting the corresponding state transition or release, including source identity, metadata eligibility, exact-quote presence, citation-marker validity, counter-evidence requirements, schema conformance, state eligibility, review requirements and integrity-chain validation.

## Reviewer independence truthfulness

A second model call, separate conversation or separate context is not automatically independent peer review.

Adapters must explicitly declare:

* `review_mode`;
* `independence`;
* `blind_review_supported`;
* `independence_limitations`;
* relevant assurance properties.

SWOS must never infer blindness from a model/provider name or from the mere fact that a separate call/context was used.

For the current `automatic_delivery` assurance level, declared **limited** independence is permitted when all deterministic gates and bounded-review requirements pass. `unknown`, `none` or `unsupported` independence blocks automatic delivery. A future higher-assurance profile may require verified independent review.

## Live host execution and host bundle role

The primary subscription/agent-host mechanism is `swos.work-orders.v1`:

```text
LIVE HOST EXECUTION
        ↓
SWOS work-order protocol
        ↓
bounded host stage outputs
        ↓
SWOS validation/state transition
        ↓
canonical host bundle / audit record
```

`host_bundle` is retained as a **replay / interchange / debugging / reproducibility format**. It is not a fictional subscription API and not the primary live execution mechanism.

A completed run may be replayed later without the original host. Replay is a new execution mode whose provenance preserves the original host information while making clear that no original live host/API call occurred during replay.

## Release invariants

A release gate MAY require a named SWOS capability, contract conformance, a minimum assurance level, verified evidence/provenance properties, declared reviewer independence, deterministic integrity/schema checks, bounded resource policy and a complete audit package.

A release gate MUST NOT require a particular vendor, commercial model name, API key, billing mode, provider-specific method string or provider-specific prompt representation.

## Provenance

Provider/model details remain useful provenance. Runs should record adapter, execution mode, host/model identity where exposed, capability, contract, canonical instruction identity, assurance/independence, API credential use, paid-call evidence where observable, and token/latency/cost evidence where observable.

These fields describe **how** a capability was supplied. They do not define scholarly validity.

## Portability conformance

The same governed acceptance contract must be executable through materially different bindings without changing the release definition. At minimum the v2 portability gate requires:

1. one direct/API-backed execution; and
2. one host-native subscription execution with no model API credential and no paid model API calls.

A replay run is useful reproducibility evidence but does not substitute for the host-native portability test.

## Violations

The following block release until removed or isolated behind an adapter boundary:

* provider SDK imports in SWOS Core;
* provider/model names in core release decisions;
* provider-specific method strings as capability proof;
* scholarly prompt text owned privately by an adapter;
* hidden capability degradation;
* fabricated reviewer independence or blindness;
* treating replay-bundle consumption as proof of live host autonomy;
* allowing a model judgement to bypass a deterministic SWOS check.
