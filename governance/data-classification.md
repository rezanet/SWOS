# Data Classification

Four classes. Classification is assigned at intake and re-evaluated whenever new
material enters the work.

| Class | Definition | Tool egress | Memory | Export |
|---|---|---|---|---|
| `public` | Openly published; no access restriction | Any registered tool | Permitted with provenance | Permitted |
| `internal` | Organisation-internal, non-sensitive | Tools approved for internal | Metadata and lessons only | Permitted with approval |
| `confidential` | Commercially or personally sensitive | Approved tools only, egress allow-listed | **Lessons only, never content** | Requires human approval |
| `restricted` | Regulated, legally privileged, special-category personal data | Local-only tools (empty egress list) | **No memory writes at all** | Prohibited without named authority |

## The metadata-first principle

For anything above `public`, SWOS records **what happened, not the payload it
happened to**. The minimum record is source provenance, evidence references,
discovery events and data-quality issues. Deliberately excluded from durable
records: prompts, responses, secrets, customer content and runtime payloads.

This is not a storage optimisation. An audit trail that contains the sensitive
material it audits has multiplied the exposure it was built to control.

## Classification drift

A work's classification is the **maximum** of its intake classification and the
classification of everything it has ingested. Retrieving one confidential source
into a public work reclassifies the work, and the reclassification triggers
re-evaluation of the tool egress and memory gates. This is checked on every
evidence-layer write, not at release.
