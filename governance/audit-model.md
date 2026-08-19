# Audit Model

## What is recorded

| Event class | Recorded |
|---|---|
| Retrieval | Query, corpus, parameters, result identifiers, timestamp, tool version |
| Transformation | Input entity, output entity, activity type, tool, parameters |
| Classification | Claim id, citation id, classification, classifier, rationale |
| Agent action | Agent, inputs read, outputs written, tools called |
| Decision | Full SDL entry |
| Review | Reviewer role, findings, verdict, iteration, blindness |
| Evaluation | Plane, metrics, thresholds, gate result, subject versions |
| Gate | Gate type, policy id and version, result, evidence, NIST reference |
| Approval | Approver, rationale, timestamp, policy basis |
| Memory | Write, correction, expiry, deletion - with rationale |
| Security | Injection attempts, egress denials, classification violations |
| Blocked transition | Attempted state, blocking precondition, timestamp |

## What is deliberately NOT recorded

Prompts, responses, secrets, customer content and runtime payloads are excluded
from durable audit records for anything above `public` classification.

The reason is stated plainly: an audit trail that contains the sensitive material
it audits has multiplied the exposure it was built to control. SWOS audits
**metadata and provenance**, not payloads. Where a higher-risk use case genuinely
requires retained content, it is retained under a separate, explicitly approved
control with its own retention clock.

## The audit pack

Assembled at release, frozen, and shipped with the output:

1. Evidence matrix
2. Argument map
3. Citation audit
4. Unsupported-claim list
5. Counter-evidence list
6. Reviewer simulation notes
7. Revision log
8. Provenance bundle (PROV-compatible, frozen)
9. Decision ledger extract
10. Uncertainty statement
11. Governance gate records
12. Approval record
13. AI-use disclosure

A frozen bundle is append-only. Corrections create a **superseding** bundle; they
never mutate the original.

## Provenance completeness

```
provenance_completeness = claims_with_epg_node / total_claims
```

Release requires **1.0**. This is the single most load-bearing governance check
in SWOS: it is what makes "auditable" a measurement rather than an aspiration.
