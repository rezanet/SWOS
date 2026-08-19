---
pack: swos-discipline-philosophy
version: 1.0.0
discipline: philosophy
---

# Discipline Pack: Philosophy

## 1. Reasoning module

Argument reconstruction, conceptual analysis and genealogy, counterexample generation, and careful handling of modal and normative distinctions. Philosophy does not primarily summarise literature; it reconstructs positions charitably and then tests them. An output that reports what philosophers said without reconstructing why they said it has not done philosophy.

## 2. Evidence hierarchy

Primary texts outrank commentary, and a critical edition outranks a popular translation. Where an argument turns on a term, the original-language term and its translation history are evidence. Secondary literature is evidence about the debate, not about the world. Textbook summaries are the weakest tier and may not be the sole support for an attributed position.

## 3. Proof standard

A philosophical claim is discharged by a valid argument from premises that are either independently supported or explicitly assumed, with the strongest available objection stated and either rebutted or conceded. **An unaddressed strongest objection is a failed proof, not a stylistic omission.**

## 4. Required analysis moves

* Reconstruct the target position in its strongest form before criticising it
* Make every hidden premise explicit
* Distinguish conceptual, empirical and normative claims
* Distinguish necessity, possibility and actuality where the argument turns on modality
* Generate at least one counterexample or explain why none is available
* Trace the genealogy of any contested term used as though settled
* State the strongest objection and respond to it
* Check for equivocation across the argument's uses of key terms

An output in this discipline that omits a required move is incomplete regardless
of how well written it is.

## 5. Failure modes

* Doxography posing as argument - a chronological tour of who said what
* Equivocation: a term shifts sense between premise and conclusion
* Straw-manning: the reconstructed position is weaker than the real one
* Smuggled normativity: an 'ought' derived from an 'is' without acknowledgement
* Citation of a commentator for a claim about the primary text
* Conceptual novelty claimed without genealogy - the distinction usually exists already

## 6. Rubric

| Dimension | Weight | Pass threshold |
|---|---|---|
| Argument reconstruction fidelity | 0.20 | Charitable and accurate; specialist would accept it |
| Validity and soundness | 0.20 | No invalid step; premises supported or flagged as assumed |
| Hidden premises made explicit | 0.15 | Zero unflagged hidden premises |
| Objection handling | 0.20 | Strongest objection stated and answered |
| Conceptual precision | 0.15 | No equivocation; contested terms defined |
| Genealogical awareness | 0.10 | Key terms situated in their debate |

## 7. Acceptance test

`evals/fixtures/golden/philosophy-consciousness-analysis.json`. **Pass condition:** the output identifies hidden premises, generates objections and draws conceptual distinctions, rather than summarising the literature on the concept.

