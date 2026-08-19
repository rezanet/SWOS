# ADR-0002: W3C PROV-DM as the provenance baseline

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

The Evidence Provenance Graph needs an interoperability baseline. Inventing a bespoke provenance model would isolate SWOS from existing tooling and from institutional archives that already speak PROV.

## Decision

The EPG is W3C PROV-DM compatible. Core relations - used, wasGeneratedBy, wasDerivedFrom, wasAttributedTo, wasAssociatedWith, wasRevisionOf, wasQuotedFrom, hadPrimarySource, hadMember, wasInformedBy, actedOnBehalfOf, alternateOf, specializationOf - round-trip to PROV without loss. SWOS domain relations (supportsClaim, partiallySupports, contextualises, contradicts, requiresHumanReview, evaluatedBy, approvedBy, supersedes, belongsToResearchProgramme) live in a declared extension namespace. PROV **bundles** are adopted explicitly.

## Consequences

* EPG documents are consumable by existing PROV tooling and archival systems.
* Bundles give provenance-of-provenance: a reviewer knows not only what evidence supports a claim, but who or what asserted that support, and when.
* The schema is constrained by PROV's shape; some SWOS-natural modelling requires the extension namespace.
* Serialisation compatibility becomes a testable non-functional requirement.

## Alternatives considered

Rejected: a bespoke lineage model. Simpler to design, impossible to federate, and it would have made provenance export a bilateral integration problem forever.
