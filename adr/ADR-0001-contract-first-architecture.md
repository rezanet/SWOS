# ADR-0001: Contract-first architecture

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

The original SWOS artefact was a single large prompt that reached into schema design, provenance modelling, decision-ledger fields, memory governance, discipline ontologies, reviewer criteria, evaluation categories, repository structure and adapter design. Those requirements were correct. Their location was not.

## Decision

SWOS is contract-first. The prompt becomes a Master Prompt Contract carrying mission, principles, input contract, workflow contract, handoff rules, output contract, abstention rules and the seven rules. Everything deterministic, persistent, measurable or auditable moves into schemas, tools, evaluation and governance.

## Consequences

* The prompt can no longer 'just handle' a new requirement; each one needs a home. This is the point.
* Contributors must learn the layer model before contributing.
* Guarantees become checkable: 'auditable' is now a measurement, not an adjective.
* Host and model portability improves, because behaviour no longer hides in prompt prose.

## Alternatives considered

Rejected: keep a single authoritative prompt and document the architecture separately. Rejected because documentation that does not constrain execution is decoration - the failure the assessment named as 'a beautifully worded liability'.
