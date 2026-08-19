---
pack: swos-discipline-engineering
version: 1.0.0
discipline: engineering
---

# Discipline Pack: Engineering

## 1. Reasoning module

System, constraint and trade-off reasoning. Engineering claims are conditional on requirements, assumptions and operating envelope. A design assertion without its constraints is not an engineering claim; it is a preference.

## 2. Evidence hierarchy

Measured performance in a representative environment outranks bench results. Standards and specifications outrank vendor claims. Post-incident analyses are high-value evidence about failure modes. Reference architectures are evidence about convention, not about fitness for this context.

## 3. Proof standard

An engineering claim is discharged when requirements, assumptions, constraints and operating envelope are stated, at least two design alternatives are compared against them, and the failure modes of the selected option are identified with their mitigations.

## 4. Required analysis moves

* State functional and non-functional requirements
* State assumptions explicitly, including the ones that feel obvious
* State system boundaries and dependencies
* Compare at least two alternatives against the stated criteria
* Identify failure modes and their mitigations
* Address operability, maintainability, security and observability
* State the operating envelope within which the claim holds
* Identify the reversibility of the decision

An output in this discipline that omits a required move is incomplete regardless
of how well written it is.

## 5. Failure modes

* Solution-first reasoning: the alternative section written to justify a choice already made
* Silent assumptions, especially about scale, load and failure
* Non-functional requirements treated as an afterthought
* Trade-offs asserted without criteria
* Failure modes omitted because the design is expected to work
* Reference architecture cited as though it were a requirement

## 6. Rubric

| Dimension | Weight | Pass threshold |
|---|---|---|
| Requirements and constraints stated | 0.20 | Functional and non-functional both present |
| Assumptions made explicit | 0.15 | Zero unflagged load-bearing assumptions |
| Alternatives compared | 0.20 | At least two, against stated criteria |
| Failure-mode analysis | 0.20 | Modes and mitigations identified |
| Operability and maintainability | 0.15 | Addressed, not deferred |
| Decision reversibility | 0.10 | Stated |

## 7. Acceptance test

`evals/fixtures/golden/engineering-tradeoff-analysis.json`. **Pass condition:** the output compares alternatives against explicit criteria and names failure modes, rather than advocating a single design.

