# ADR-0004: EPG and SDL are separate artefacts

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

Early drafts blurred provenance and decision recording. Both are 'audit', so the temptation is to merge them.

## Decision

They are separate. The **EPG answers 'where did this come from and how was it produced'** - lineage of entities, activities and agents. The **SDL answers 'why was this judgement made'** - alternatives, rationale, criteria, dissent, approver, reversibility. The SDL references EPG nodes by identifier and never duplicates evidence.

## Consequences

* Two stores instead of one, linked by identifier.
* Each becomes checkable on its own terms: provenance completeness against the EPG, decision-trigger coverage against the SDL.
* The SDL is the more defensible asset: most systems retain traces of actions, few retain scholarly judgement.
* A blast-radius query on retraction runs against the EPG; a defence of an interpretive choice runs against the SDL.

## Alternatives considered

Rejected: a single unified audit log. It would have degraded into a chronological event stream from which neither question could be answered without reconstruction.
