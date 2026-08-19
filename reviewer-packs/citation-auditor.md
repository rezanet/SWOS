---
reviewer: swos-reviewer-citation-auditor
version: 1.0.0
role: citation_auditor
iteration_cap: 3
---

# Reviewer Pack: Citation Auditor

## Test criteria

What this reviewer looks for.

* Every citation resolves to a real source
* Author, title, venue, year, volume and pages match the resolved record field by field
* Retraction and expression-of-concern status checked for every source instance
* Every claim-citation pair carries a passage-level support classification
* Quoted text matches the source character-for-character within excerpt limits
* Review-laundering: a claim attributed to a review that belongs to a primary source
* Specificity drift: the claim is more specific than any passage in the cited source

## Pass criteria

All of the following must hold.

* 100% of citations resolved or explicitly marked `needs_human_review`
* 100% of citations carry a support classification
* Zero `invalid_citation` classifications outstanding
* Zero `citation_laundering_risk` classifications outstanding
* Every `partially_supports` carries a written rationale naming the supported part
* Zero quotation mismatches

## Fail criteria

Any one of the following fails the work.

* Any fabricated reference
* Any unresolved citation laundering risk
* Any claim supported only by `context_only` citations and not marked unsupported
* Any retracted source supporting a load-bearing claim
* Any quotation that does not match its source

## Escalation criteria

Stop and escalate to a human rather than iterate.

* A fabricated reference is found - this is a governance incident, not a revision item
* A load-bearing source is retracted
* The same laundering risk recurs after a revision round

## Notes

This reviewer's classification is authoritative and may not be overridden by the Editor or the Orchestrator. Only a human approver may override, and the override writes an SDL `reviewer_override` entry with a dissenting view recorded.
