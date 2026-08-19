---
pack: swos-discipline-technical-writing
version: 1.0.0
discipline: technical_writing
---

# Discipline Pack: Technical Writing

## 1. Reasoning module

Requirements and design reasoning rendered for a specific audience and decision. The controlling question is what decision the reader must make and what they need in order to make it. Technical writing fails by omission of constraints far more often than by imprecision of prose.

## 2. Evidence hierarchy

Primary system artefacts - specifications, measured telemetry, incident records, architecture decision records - outrank narrative descriptions. Vendor documentation is evidence about intent, not behaviour. Undocumented tribal knowledge must be recorded as an unverified claim, not as fact.

## 3. Proof standard

A technical claim is discharged when the requirement it serves, the assumptions it rests on, the constraints that bound it and the failure modes it accepts are all stated, and the reader can act on it without a follow-up conversation.

## 4. Required analysis moves

* State the decision the document supports and the audience making it
* State requirements, assumptions, constraints and trade-offs
* Present design alternatives with their consequences
* Include failure modes and operational considerations
* Include diagrams where structure is easier seen than read
* Separate what is decided from what is proposed from what is open
* State what is out of scope

An output in this discipline that omits a required move is incomplete regardless
of how well written it is.

## 5. Failure modes

* Describing the system instead of supporting the decision
* Assumptions embedded in diagrams but absent from text
* Proposals written in the grammar of decisions
* Operational considerations deferred to a later document that is never written
* Audience mismatch: executive summary written for engineers, or the reverse

## 6. Rubric

| Dimension | Weight | Pass threshold |
|---|---|---|
| Decision and audience clarity | 0.20 | Both explicit |
| Requirements and constraints | 0.20 | Stated and traceable |
| Alternatives and trade-offs | 0.20 | Consequences stated |
| Failure modes and operations | 0.20 | Addressed |
| Decided vs proposed vs open | 0.10 | Clearly separated |
| Scope boundaries | 0.10 | Out-of-scope stated |

## 7. Acceptance test

`evals/fixtures/golden/technical-decision-brief.json`. **Pass condition:** the output separates decided, proposed and open items and states constraints, rather than producing an undifferentiated description.

