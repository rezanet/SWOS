---
pack: swos-discipline-art-history
version: 1.0.0
discipline: art_history
---

# Discipline Pack: Art History

## 1. Reasoning module

Object, formal and contextual analysis. The object is the primary source. Art-historical writing gathers evidence from close observation and defends interpretation through **visual evidence** - which means an interpretive claim must anchor to observable features of the work, not to what a commentator said about it.

## 2. Evidence hierarchy

The object itself, and technical studies of the object - infrared reflectography, pigment analysis, dendrochronology, X-radiography - outrank all textual commentary about it. Catalogues raisonnés and conservation reports outrank exhibition catalogues. High-resolution reproduction is a mediated source and must be declared as such. Provenance documents are primary evidence for attribution and ownership, not for meaning.

## 3. Proof standard

An art-historical claim is discharged when it is anchored in described visual features, situated by material, technique and period, supported by provenance where attribution is at stake, and tested against historical plausibility. **An interpretation with no visual anchor is not art history.**

## 4. Required analysis moves

* Describe the object: material, dimensions, technique, condition
* Perform formal analysis: composition, colour, line, light, scale, facture
* Identify iconography and its sources
* State provenance and its gaps where attribution or dating is at stake
* Situate by period, workshop, patronage and function
* Test historical plausibility of the proposed reading
* Distinguish observed features from inferred ones
* Declare the mediation: was this seen, or seen in reproduction

An output in this discipline that omits a required move is incomplete regardless
of how well written it is.

## 5. Failure modes

* Describing the image and calling it analysis
* Interpretation with no anchor in an observed feature
* Attribution asserted without provenance or technical evidence
* Iconographic reading imported from a different tradition without justification
* Reproduction artefacts read as facture
* Patronage and function omitted, leaving the work floating free of its purpose

## 6. Rubric

| Dimension | Weight | Pass threshold |
|---|---|---|
| Object description | 0.15 | Material, technique, condition stated |
| Formal analysis quality | 0.20 | Specific, not generic |
| Visual evidence anchoring | 0.25 | Every interpretive claim anchored to an observed feature |
| Iconographic grounding | 0.15 | Sources identified |
| Provenance and attribution rigour | 0.15 | Gaps stated where attribution is claimed |
| Historical plausibility | 0.10 | Reading available in that context |

## 7. Acceptance test

`evals/fixtures/golden/art-history-visual-analysis.json`. **Pass condition:** the output uses visual evidence from the object rather than secondary commentary, and states provenance gaps.

## Promotion note

This pack is the strongest candidate for promotion to a full agent, because it is
the only discipline requiring an `image_analysis` tool that no other role calls.
Promotion is deferred to the Research-Grade milestone. See `adr/ADR-0005`.

