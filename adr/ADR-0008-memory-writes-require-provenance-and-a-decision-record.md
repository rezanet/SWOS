# ADR-0008: Memory writes require provenance and a decision record

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

Reflection-style patterns improve later attempts by storing verbal reflections. They are also exactly how memory contamination begins: an unsupported reflection is read back in a later run as an established fact.

## Decision

A durable memory write requires all of: at least one supporting EPG node, an SDL `memory_write` decision, an accountable owner, a confidence, and an expiry date. Restricted content is never written. Raw prompts, responses, secrets, customer content and runtime payloads are never written. User style preferences are stored in an isolated scope and are never readable as evidence.

## Consequences

* Reflexion remains available but governed.
* Memory writes are slower and some are refused. That is the intent.
* Every memory item is traceable to the evidence that justified it.
* The memory-contamination evaluation plane can seed a false prior and assert it is rejected.

## Alternatives considered

Rejected: an unconstrained scratchpad memory. It optimises the first ten runs and corrupts the next thousand.
