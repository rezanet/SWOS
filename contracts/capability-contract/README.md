# SWOS Capability Contract

**Status:** v2 architecture contract
**Authority:** `governance/policies/host-independence.md`
**Related ADR:** `adr/ADR-0011-host-independence-and-three-layer-architecture.md`

## Purpose

The Capability Contract is the boundary between SWOS Core and any model, host, API, local runtime, or replay adapter.

SWOS Core requests capabilities. Adapters fulfil them. SWOS then validates and governs the result.

A capability name describes a scholarly function, never a vendor implementation.

## Capability envelope

Every capability result presented to SWOS Core must be representable by the following logical envelope, whether the transport is Python, JSON, a host work order, MCP, CLI, or replay bundle.

```json
{
  "capability": "semantic_rerank",
  "contract_version": "1.0.0",
  "status": "completed",
  "result": {},
  "assurance": {
    "level": "verified",
    "independence": "same_context_limited"
  },
  "provenance": {
    "adapter": "codex-host",
    "execution_mode": "host_native_subscription",
    "model_host": "ChatGPT",
    "model": "runtime-reported",
    "api_key_used": false,
    "paid_api_calls": 0
  }
}
```

This is a logical contract, not yet a frozen wire schema. Transport-specific adapters may encode it differently, but they must preserve equivalent information.

## Core capability set

| Capability | Required result property | Fail-closed condition |
|---|---|---|
| `research_planning` | governed scope, queries, rivals, uncertainty | malformed or insufficient plan |
| `source_retrieval` | source records with retrievable provenance | no admissible source records |
| `semantic_rerank` | per-source semantic relevance/evidence scores | capability absent when required |
| `evidence_build` | atomic claims mapped to exact source spans | missing or non-exact support spans |
| `citation_support_audit` | independent support classification | uncertainty or unsupported claim |
| `argument_build` | thesis/nodes/edges using admitted evidence | empty or invalid graph |
| `draft_generation` | prose constrained to admitted evidence/argument | unsupported markers/claims |
| `semantic_verification` | explicit semantic safety verdict | non-pass under automatic-use policy |
| `review_panel` | role-bounded findings and verdicts | unresolved blocker/major findings |
| `research_repair_planning` | bounded queries tied to findings | no defensible repair path |
| `revision` | revised article using admitted state only | new unsupported material |
| `prose_transform` | safe transformed text or source fallback | unsafe changed text |

## Contract rules

1. Core requests a capability by **SWOS capability identifier**.
2. An adapter may fulfil one or many capabilities.
3. Different capabilities in one run may use different adapters/models.
4. An adapter must declare unavailable or degraded capabilities explicitly.
5. Missing required capability fails closed or triggers a governed assurance downgrade.
6. Provider/model names are provenance, not correctness criteria.
7. A core release gate may test `capability`, `status`, `assurance`, result validity, evidence properties, and provenance completeness; it may not test vendor identity.
8. Canonical stage instructions belong to SWOS and travel with the capability request. Adapters may translate host syntax, not scholarly policy.
9. Capability results are proposals until admitted by SWOS Core validation and state-transition rules.
10. A replay adapter may replay a prior result but must identify itself as replay; replay is not proof of live autonomous host execution.

## Capability discovery

An adapter should expose a declaration equivalent to:

```json
{
  "adapter": "codex-host",
  "execution_mode": "host_native_subscription",
  "capabilities": {
    "research_planning": {"support": "native"},
    "source_retrieval": {"support": "native"},
    "semantic_rerank": {"support": "native"},
    "evidence_build": {"support": "native"},
    "citation_support_audit": {
      "support": "native",
      "independence": "same_context_limited"
    },
    "argument_build": {"support": "native"},
    "draft_generation": {"support": "native"},
    "review_panel": {
      "support": "native",
      "independence": "same_context_limited"
    },
    "revision": {"support": "native"},
    "prose_transform": {"support": "native"}
  }
}
```

SWOS Core compares the required workflow capabilities and assurance levels against this declaration before or during execution.

## Host-native work-order protocol

Subscription hosts cannot be treated as implicit paid APIs. For host-native execution SWOS uses bounded work orders.

A work order contains:

* run/work identity;
* current scholarly state;
* requested capability;
* canonical SWOS stage instruction reference/version;
* permitted input artefacts;
* required output contract;
* assurance requirement;
* tool/data constraints;
* fail-closed behaviour.

A conforming host driver repeats:

1. ask SWOS for `next_work`;
2. fulfil that bounded capability using host-native intelligence/tools;
3. submit the result;
4. allow SWOS to validate and transition state;
5. stop only on `APPROVED`, `REVIEW_REQUIRED`, refusal, or unrecoverable failure.

The user supplies one research request. The user does not manually assemble intermediate stage files.

## API-backed protocol

API adapters may call model/provider SDKs internally, but they must return the same SWOS capability semantics as host-native adapters. Provider response formats, structured-output mechanisms, token accounting, and authentication remain adapter concerns.

## Conformance

A capability implementation conforms only when:

* its output satisfies the SWOS result contract;
* required provenance is present;
* required assurance/independence is truthful;
* deterministic SWOS validation passes;
* it does not require core to know vendor-specific method names;
* provider failure cannot silently become a successful result.

## Migration note for PR #41

The current Autonomous SWOS branch contains two known boundary leaks that must be removed during the three-layer refactor:

1. `swos_runtime.orchestrator.AutonomousSWOS` defaults directly to `OpenAIStageProvider` and the default prose path constructs OpenAI providers inside the orchestrator.
2. the core evidence gate tests the provider-specific reranker method string `openai_joint_query_document_cross_encoder` rather than a provider-neutral SWOS capability assertion.

Those are implementation defects relative to the Host Independence Rule, not exceptions to it.
