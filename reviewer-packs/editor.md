---
reviewer: swos-reviewer-editor
version: 1.0.0
role: editor
iteration_cap: 3
---

# Reviewer Pack: Editor

## Test criteria

What this reviewer looks for.

* Structure: does the argument's order match the Argument Graph
* Clarity: is each sentence's claim identifiable
* Concision: is any passage doing no work
* Voice and register: appropriate to genre and audience
* Genre fit: does this read as the form it claims to be
* Citation style conformance
* **Meaning preservation**: has any claim's epistemic type changed under editing

## Pass criteria

All of the following must hold.

* Zero claims whose epistemic type changed during editing
* Every qualifier present in the Argument Graph survives into the prose
* No transition asserts a relation absent from the Argument Graph
* Revision log records every substantive change with a reason
* Genre and audience requirements met

## Fail criteria

Any one of the following fails the work.

* A hedge removed or weakened without an evidence change
* A transition asserting causation or entailment not present in the Argument Graph
* A claim's epistemic type changed by rewording
* Confidence language introduced without evidential support

## Escalation criteria

Stop and escalate to a human rather than iterate.

* A sentence cannot be made clear without changing what it claims
* Genre requirements conflict with the available evidence
* The author rejects an edit required to preserve a qualifier

## Notes

This reviewer is constrained more tightly than any other, because editing is the last place a governed system silently fails: a fluent editor smoothing a hedged claim into a confident one undoes every upstream control. **Every edit is diffed against the Evidence Matrix before acceptance.** Style polish masking weak evidence is a forbidden anti-pattern.
