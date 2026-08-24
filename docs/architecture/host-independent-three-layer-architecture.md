# SWOS Host-Independent Three-Layer Architecture

**Status:** Normative architecture
**Authority:** `governance/policies/host-independence.md`
**Decision:** `adr/ADR-0011-host-independence-and-three-layer-architecture.md`

## Principle

> **SWOS owns the scholarly process. Models provide capabilities.**

SWOS is not the model underneath it. Models, hosts, APIs, and subscription environments are replaceable execution workers. SWOS owns the definition of valid research, the workflow that produces it, and the gates that determine whether it may be released.

## Three layers

```text
                    SWOS
                     │
        ┌────────────┴────────────┐
        │                         │
     SWOS CORE              Capability Layer
        │                         │
        │                ┌────────┼────────┐
        │                │        │        │
        │             Codex     Claude   API / local
        │             Host      Host      Providers
        │
 ┌──────┴───────────────────────────────┐
 │ Research state machine              │
 │ Evidence Matrix                     │
 │ Argument Graph                      │
 │ Citation verification               │
 │ Review/revision policy              │
 │ Scholarly state                     │
 │ EPG / SDL / RPM                     │
 │ Governance gates                    │
 │ Integrity chain                     │
 │ Audit package                       │
 └─────────────────────────────────────┘
```

The bottom box is SWOS. GPT, Claude, Gemini, local models, and future systems stand outside it.

## Layer 1 — SWOS Core

SWOS Core is the authoritative scholarly control plane. It owns:

* intake and scholarly state transitions;
* research-plan state and scope decisions;
* evidence admission rules;
* Evidence Matrix structure and validation;
* Argument Graph structure and validation;
* citation existence, metadata, span, and support requirements;
* review and revision policy;
* EPG provenance requirements;
* SDL decision requirements;
* RPM memory governance;
* release and abstention gates;
* integrity chain and run manifest;
* audit-package completeness;
* acceptance/evaluation definitions.

Core must make no assumption about who performs a model-mediated task. The same candidate result must face the same SWOS validity tests regardless of provider.

### Core may know

Core may know that a capability result came with properties such as:

* `capability=semantic_rerank`;
* `assurance=verified`;
* `independence=separate_context`;
* `execution_mode=host_native_subscription`;
* `api_key_used=false`;
* `model_host=ChatGPT`.

These are provenance and assurance facts.

### Core may not know as authority

Core must never say, in effect:

* "release because this was OpenAI";
* "reject because this was Claude";
* "this capability executed only if its method string starts with `openai_`";
* "an API key is part of the definition of a valid research run".

## Layer 2 — Capability Layer

The Capability Layer is the only boundary through which model/host intelligence enters SWOS Core.

Each capability contract defines:

1. capability identifier;
2. purpose;
3. input schema/contract;
4. output schema/contract;
5. evidence/provenance requirements;
6. assurance and independence properties;
7. failure semantics;
8. whether deterministic SWOS verification is required before downstream use.

Initial v2 capability set:

| Capability | Purpose |
|---|---|
| `research_planning` | Produce bounded scope, queries, rivals, uncertainty, reviewer needs |
| `source_retrieval` | Acquire source records under source/tool policy |
| `semantic_rerank` | Rank retrieved sources by relevance and evidentiary value |
| `evidence_build` | Propose atomic evidence-backed claims and exact source spans |
| `citation_support_audit` | Independently judge whether a span supports a claim |
| `argument_build` | Construct thesis, grounds, warrants, objections and rival readings |
| `draft_generation` | Render verified evidence/argument into prose |
| `semantic_verification` | Judge preservation or validity of a transformed proposition/text |
| `review_panel` | Attack citation, argument, discipline, prose and governance quality |
| `research_repair_planning` | Convert blocking review findings into bounded new research work |
| `revision` | Resolve findings using admitted evidence/argument only |
| `prose_transform` | Improve prose under SWOS semantic-safety constraints |

Adapters may provide multiple capabilities. SWOS may use different adapters for different capabilities in one run.

## Layer 3 — Host / Provider Adapters

Adapters translate a host/provider into SWOS capability contracts.

Examples:

* `codex-host` — ChatGPT/Codex subscription-native execution;
* `claude-code-host` — Claude Code subscription-native execution;
* `openai-api` — direct OpenAI Responses API execution;
* `anthropic-api` — direct Anthropic API execution;
* `local-model` — conforming local inference runtime;
* `mcp-host` — external capabilities exposed through MCP;
* `host-bundle-replay` — deterministic replay/interchange of previously produced stage results.

An adapter does not own scholarly policy. It only answers capability requests according to SWOS contracts.

## Execution model

### API-backed execution

```text
User request
   ↓
SWOS Core
   ↓ capability request
Capability Layer
   ↓
API adapter
   ↓
Provider model/tool
   ↓ capability result
Capability Layer validation
   ↓
SWOS Core
```

### Host-native subscription execution

A subscription host is not treated as a hidden API. Control is inverted through bounded SWOS work orders:

```text
User request
   ↓
SWOS Core creates run
   ↓
SWOS: next_work = research_planning
   ↓
Codex / Claude host fulfils bounded capability
   ↓
SWOS validates result
   ↓
SWOS: next_work = source_retrieval
   ↓
... repeat until release or fail-closed stop ...
```

The host driver may loop automatically, but SWOS decides the next scholarly state and whether a submitted result satisfies the contract.

From the user's perspective this remains one request. The user does not manually orchestrate stages or construct a host bundle.

## Host bundle role

`host_bundle` is retained as a useful replay/interchange and debugging format. It can demonstrate that SWOS can consume provider-neutral outputs, preserve provenance, and reproduce validation.

It is **not**, by itself, proof of autonomous host-native subscription execution. A complete host-native acceptance requires the host to fulfil SWOS work orders without manual stage assembly.

## Canonical ownership of instructions

Research Planner, Evidence Builder, Citation Auditor, Argument Architect, Drafting, Reviewer, Revision, and other stage instructions are SWOS canonical assets.

Adapters may translate:

* transport syntax;
* structured-output mechanisms;
* tool-call formats;
* host-specific session mechanics.

Adapters must not silently redefine:

* evidence standards;
* citation requirements;
* epistemic classifications;
* release gates;
* reviewer severity policy;
* provenance requirements.

## Intelligence versus authority

A model may propose a claim, rank, judgement, argument, review finding, or revision.

SWOS decides whether that proposal is admitted into the scholarly state.

Where deterministic validation is possible, SWOS performs it directly. Where model judgement is unavoidable, SWOS records the judgement's capability, adapter, host/model provenance, assurance, independence, and uncertainty before applying the governed downstream rule.

## Independence

Reviewer independence is a capability property, not a vendor assumption.

Examples:

* `independence=blind_separate_context`;
* `independence=separate_context_same_model`;
* `independence=same_context_limited`;
* `independence=external_model`.

A workflow may require a minimum independence level for automatic release. If the active adapter cannot supply it, SWOS must downgrade assurance or require review; it may not pretend independence exists.

## Core-path boundary

Provider/vendor-specific code belongs in adapter/provider paths. Core paths are prohibited from depending on provider SDKs, credentials, model names, API method names, or commercial-plan identity.

Provider identities are allowed in:

* adapter implementations;
* provider-specific tests;
* provenance records;
* performance/cost diagnostics;
* provider benchmark evidence.

They are forbidden as release authority in:

* core orchestration;
* governance policy;
* schemas;
* canonical artefact definitions;
* host-independent evaluation gates.

## Portability acceptance

The same canonical SWOS research-writing acceptance contract must be runnable through materially different bindings.

Required v2 evidence:

1. API-backed run — conforming adapter, complete audit package.
2. Host-native subscription run — no provider API key, no paid provider API calls, complete audit package.
3. Same SWOS release definition in both modes.

A later portability gate should add a second independent host family (for example Claude Code) to prove the abstraction is not merely Codex-shaped.

Outputs may differ. Validity criteria may not.
