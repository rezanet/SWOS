# Human Approval Threshold Matrix

Human accountability for final judgement is a principle, not a setting.

| Work characteristic | Approval required | Approver role |
|---|---|---|
| Data classification `restricted` | Always, before evidence gathering **and** before release | Named data authority |
| Data classification `confidential` | Before release and before any export | Governance officer plus work owner |
| External publication | Before release | Human author plus governance officer |
| Regulated enterprise output | Before release | Compliance-designated approver |
| Novel claim (contribution type `theory` or `position`) | Before release | Discipline expert (human) |
| Interpretive claim in a contested area | Before release | Discipline expert (human) |
| Any reviewer override | At the point of override | Governance officer |
| Any durable memory write above episodic scratch | At write time | Memory owner |
| Any governance waiver | At waiver time | Governance owner |
| Retirement of a published output | At retirement | Original approver or successor |
| Internal, `public`-class, non-novel synthesis | Not required | System-approved under policy |

## Approval is evidence, not a click

An approval record is an SDL entry containing: the decision, the alternatives, the
rationale, the evidence references, the approver identity, the timestamp and the
policy basis. An approval without a rationale is a signature, not an approval, and
does not satisfy the gate.

## Anti-rubber-stamping

Approval requests present the **unsupported-claim list, the counter-evidence list
and the open reviewer findings first**, before the manuscript. Automation
anchoring - accepting polished output too readily - is a named failure mode, and
the ordering of the approval pack is one of its controls.
