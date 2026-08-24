---
amendment: swos-constitutional-amendment-0001
status: frozen
effective_date: 2026-08-24
amends: swos-master-prompt-contract@1.0.0
incorporate_into_next_contract_revision: true
---

# Constitutional Amendment 0001 — Host Independence

This amendment adds one non-negotiable constitutional rule to SWOS without rewriting the already-frozen `MASTER-PROMPT-CONTRACT.md` v1.0.0 in place.

## Rule #8 — Host Independence

> **SWOS owns the scholarly process. Models provide capabilities.**
>
> No SWOS core workflow, governance decision, schema, artefact, evaluation gate, or release criterion may depend on a specific model vendor, model family, API, authentication mechanism, or commercial access mode.
>
> Changing the model or execution host must not change the definition of what constitutes valid SWOS research.

OpenAI, Anthropic, Gemini, local models, subscription hosts, direct APIs, and future execution providers belong behind SWOS capability/adaptor boundaries. Provider and model identity may be recorded as provenance, diagnostics, performance, assurance, or cost evidence; it may not define scholarly validity.

## Interpretation

Rule #8 extends, rather than weakens, Rules #1 and #2:

* provider-specific behaviour that can live in an adapter must live in an adapter;
* provider-specific transport, SDK, authentication, and commercial access concerns are never core scholarly requirements;
* core gates must ask whether a required SWOS capability executed and satisfied its contract, not which vendor supplied it;
* adapter limitations and reviewer-independence limits must be declared and governed rather than hidden;
* a conforming host-native subscription run and a conforming API-backed run face the same SWOS definition of release validity.

## Enforcement

Normative enforcement lives outside this constitutional text, by Rule #2:

* `governance/policies/host-independence.md`
* `contracts/capability-contract/README.md`
* `docs/architecture/host-independent-three-layer-architecture.md`
* adapter-conformance and portability evaluation gates
* vendor-leakage checks for SWOS Core paths

## Precedence and freeze semantics

The existing Master Prompt Contract states:

`governance policy > frozen schema > master contract > agent contract > discipline pack > host adapter > user preference on style`.

The frozen governance policy therefore has immediate operational authority. This amendment records the corresponding constitutional principle without mutating the historical v1.0.0 contract body.

The next versioned Master Prompt Contract must incorporate Rule #8 directly and change references from “seven non-negotiable rules” to “eight non-negotiable rules”. Historical v1.0.0 remains immutable.
