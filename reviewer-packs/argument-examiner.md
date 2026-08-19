---
reviewer: swos-reviewer-argument-examiner
version: 1.0.0
role: argument_examiner
iteration_cap: 3
---

# Reviewer Pack: Argument Examiner

## Test criteria

What this reviewer looks for.

* Every warrant explicit rather than assumed
* Hidden premises identified and surfaced
* Circular reasoning: does a premise presuppose the conclusion
* Equivocation across the argument's uses of key terms
* Every `grounds` node references an Evidence Matrix row
* Relation confidence: are low-confidence edges doing load-bearing work
* Objections: is the strongest one stated and answered
* Qualifiers: does the claim's scope match its evidence

## Pass criteria

All of the following must hold.

* Zero unflagged hidden premises
* Zero circular arguments
* Zero grounds nodes without evidence references
* Strongest objection stated and either rebutted or conceded
* Every qualifier traceable to an uncertainty type in the Evidence Matrix
* No load-bearing inference rests on a low-confidence relation

## Fail criteria

Any one of the following fails the work.

* A conclusion that does not follow from its stated grounds
* A hidden premise that, once surfaced, is not supportable
* An unaddressed strongest objection
* A claim whose scope exceeds its evidence and carries no qualifier

## Escalation criteria

Stop and escalate to a human rather than iterate.

* The argument cannot be repaired without changing the thesis
* An objection is raised that the Argument Graph structurally cannot absorb
* Two reviewers disagree on whether an inference is valid

## Notes

Runs blind where the host supports it. This reviewer examines the Argument Graph, not the prose - a well-written paragraph and a valid argument are independent properties, and conflating them is how style polish masks weak evidence.
