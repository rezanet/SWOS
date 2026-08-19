# ADR-0010: Review loops are bounded at three iterations

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

Group-chat and maker-checker orchestration patterns support collaborative validation but require clear acceptance criteria, iteration caps and escalation behaviour, or they refine indefinitely. Unlimited self-refinement is a forbidden anti-pattern.

## Decision

Every reviewer role is capped at three iterations. On the fourth attempt the work escalates to a human. Every reviewer declares explicit test, pass, fail and escalation criteria. A blocker finding is not closed by revision-round exhaustion.

## Consequences

* Bounded, predictable review cost and latency.
* Genuinely difficult work reaches a human rather than looping to a fluent non-resolution.
* Some work escalates that a further round might have resolved. Accepted: escalation is cheaper than a confident wrong answer.
* The iteration counter is a useful signal - rising escalation rates indicate contract or pack drift.

## Alternatives considered

Rejected: refine until reviewers pass. That converts unresolved disagreement into fluency, which is the precise failure SWOS exists to prevent.
