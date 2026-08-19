# ADR-0005: Discipline specialists ship as packs, not agents

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

The original roster proposed philosophy, humanities, psychology, materials science, art history and art criticism as separate agents - fifteen agents in total. Multi-agent systems add coordination, latency and new failure modes; complexity must earn its keep.

## Decision

Discipline specialists ship as **packs**: reasoning module, evidence hierarchy, proof standard, required analysis moves, failure modes, rubric and acceptance test. The core roster is nine agents. A pack is promoted to an agent only when it requires a discipline-specific tool no other role calls, or a workflow genuinely exceeding one agent's reliable scope.

## Consequences

* Nine agents instead of fifteen; materially less orchestration surface.
* Discipline knowledge is contributable by domain experts who need not understand agent orchestration.
* Rubrics and ontologies are directly testable via golden fixtures.
* Art history and art criticism are the strongest promotion candidates, because visual analysis needs an image and object-analysis tool. Deferred to Research-Grade.

## Alternatives considered

Rejected: instantiate every discipline as an agent from v1. It would have bought coordination overhead and no epistemic control - the anti-pattern of turning every noun into an agent.
