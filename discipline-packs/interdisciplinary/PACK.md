---
pack: swos-discipline-interdisciplinary
version: 1.0.0
discipline: interdisciplinary
---

# Discipline Pack: Interdisciplinary Scholarship

## 1. Reasoning module

Boundary translation. The work is not combining two literatures; it is managing what happens at the seam - where the same word means different things, where a method licensed in one field is unlicensed in another, and where evidence standards differ by an order of magnitude. Most interdisciplinary failure happens at the seam, not in either field.

## 2. Evidence hierarchy

Within each contributing discipline, that discipline's hierarchy applies unchanged. **The pack does not create a merged hierarchy** - doing so would silently import the weaker standard. Evidence crossing a boundary is downgraded one tier unless the transfer is explicitly justified.

## 3. Proof standard

An interdisciplinary claim is discharged when each contributing claim meets its own discipline's proof standard, every term used across the boundary is disambiguated, every method transfer is justified, and the synthesis link itself is supported rather than asserted.

## 4. Required analysis moves

* Identify each contributing discipline and load its pack
* Build a terminology map for every term that crosses the boundary
* Justify every method transfer explicitly
* Apply each discipline's evidence standard to its own claims, unmerged
* Support the synthesis link itself, not just the things being synthesised
* Run a prior-art check on the connection - novelty claims are highest-risk here
* State where the disciplines genuinely disagree rather than harmonising them
* Flag domain-transfer risk in the uncertainty statement

An output in this discipline that omits a required move is incomplete regardless
of how well written it is.

## 5. Failure modes

* Over-association: two literatures linked by a resemblance that does not survive scrutiny
* Terminology collision unaddressed - 'model', 'representation', 'structure', 'validity'
* Method laundering: an unlicensed method acquires legitimacy by crossing a boundary
* Standard levelling: the weaker evidence standard silently governs both fields
* False originality: the connection exists in a third literature neither author searched
* Harmonising a real disagreement into a synthesis nobody in either field accepts

## 6. Rubric

| Dimension | Weight | Pass threshold |
|---|---|---|
| Per-discipline standards maintained | 0.25 | No standard levelling |
| Terminology disambiguation | 0.20 | Every boundary-crossing term mapped |
| Method transfer justification | 0.20 | Every transfer justified |
| Synthesis link supported | 0.20 | The connection itself has evidence |
| Prior-art and novelty check | 0.15 | Connection checked against a third literature |

## 7. Acceptance test

`evals/fixtures/golden/interdisciplinary-boundary-translation.json`. **Pass condition:** the output maps colliding terminology and justifies method transfer, and does not present an unsupported resemblance as a synthesis.

