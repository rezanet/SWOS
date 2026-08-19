---
pack: swos-discipline-humanities
version: 1.0.0
discipline: humanities
---

# Discipline Pack: Humanities

## 1. Reasoning module

Hermeneutic and historical reasoning. Meaning is reconstructed within a context, from evidence that is partial by nature. The archive's silences are data. An output that presents a single confident reading of a contested text has not done humanities work; it has flattened it.

## 2. Evidence hierarchy

Primary sources and archival documents outrank all commentary. Critical editions outrank popular editions. Contemporary sources outrank retrospective accounts for what was believed at the time, and are weaker for what was actually the case. Translations are evidence with a mediation layer that must be declared.

## 3. Proof standard

An interpretive claim is discharged when it is anchored in primary evidence, situated in its historical context, weighed against at least one rival reading, and bounded by an explicit statement of what the archive does not contain.

## 4. Required analysis moves

* Anchor every interpretive claim in primary evidence
* State the historical context and its bearing on the reading
* Present at least one rival reading and explain the preference on evidential grounds
* State archival limits: what is missing, destroyed, unindexed or inaccessible
* Flag translation dependencies where the argument turns on a term
* Distinguish original meaning, historical reception and present reception
* Name the interpretive frame rather than naturalising it
* Distinguish evidence of belief from evidence of fact

An output in this discipline that omits a required move is incomplete regardless
of how well written it is.

## 5. Failure modes

* Interpretive flattening: one confident reading where the evidence supports several
* Presentism: reading current categories back into the source
* Archival silence treated as absence of the phenomenon
* Translation dependence unflagged
* Commentary cited for a claim about the primary source
* Theoretical frame applied without acknowledgement that it is one frame among several

## 6. Rubric

| Dimension | Weight | Pass threshold |
|---|---|---|
| Primary-source anchoring | 0.20 | Every interpretive claim anchored |
| Historical contextualisation | 0.20 | Context stated and load-bearing |
| Interpretive plurality | 0.25 | At least one rival reading, evidentially weighed |
| Archival limits declared | 0.15 | Gaps stated |
| Translation and mediation flagged | 0.10 | Dependencies declared |
| Frame acknowledged | 0.10 | Named, not naturalised |

## 7. Acceptance test

`evals/fixtures/golden/humanities-rival-readings.json`. **Pass condition:** the output presents rival readings with evidential weighing and states archival limits, rather than resolving to a single reading.

