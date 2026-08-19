---
name: swos-citation-auditor
description: Verifies citations for existence, metadata correctness and passage-level claim support, and detects fabricated references and citation laundering. Use when checking a manuscript, report, literature review, thesis or draft for citation integrity, when asked whether a source actually says what it is cited for, when validating a reference list, or before submitting or publishing anything with references. Checks DOI resolution, author, title, venue and year, retraction status, quotation accuracy, and classifies every citation as directly supports, partially supports, context only, contradicts, laundering risk or invalid. Use whenever citation trustworthiness is the question.
license: MIT
compatibility: Requires a DOI or metadata resolver and full-text or abstract access to classify passage support. Without retrieval it can check internal consistency and flag unverifiable citations, but cannot confirm existence - and will say so rather than assume.
metadata:
  version: 1.0.0
  swos_component: reviewer
  spec: agent-skills
allowed-tools: [doi_resolve, metadata_validate, retraction_check, full_text_parse, passage_support_classify, quotation_verify]
---

# SWOS Citation Auditor

Rule #5: every citation is verified for **existence**, for **metadata**, and for
**claim support**. The third is the one most systems skip, and it is where the
damage is.

## The four checks, in order

**1. Existence.** Resolve the identifier. A citation that does not resolve is
`invalid_citation`. Do not "correct" it into something that does resolve - that
substitutes a different source for the one the author cited.

**2. Metadata.** Verify author list, title, venue, year, volume and pages against
the resolved record, field by field. Report mismatches individually. A plausible
citation with the wrong year may be a different paper.

**3. Retraction.** Check retraction and expression-of-concern status for every
source instance. A retracted source supporting a load-bearing claim is a blocker,
not a footnote.

**4. Passage support.** For each claim-citation pair, locate the **specific
passage** and classify:

| Classification | Meaning |
|---|---|
| `directly_supports` | The cited passage supports the exact claim as stated |
| `partially_supports` | The source supports part of the claim - state which part |
| `context_only` | Relevant background; does not establish the sentence |
| `contradicts` | The source undermines the claim it is cited for |
| `citation_laundering_risk` | **Real source, wrong claim** |
| `invalid_citation` | Does not exist, or metadata fails |

## Citation laundering

This is the signature failure. The source is real, the venue is respectable, the
topic is adjacent - and the passage does not say what the sentence claims. It
survives every check except passage-level support, which is exactly why
document-level support assertions are forbidden.

Detection heuristics:

* The claim is more specific than any passage in the source.
* The claim generalises a result the source bounded to one population, material,
  period or condition.
* The claim asserts causation where the source reports association.
* The citation is to a review that cites a primary source - **cite the primary
  source or attribute the claim to the review**, do not launder through it.
* The quantity in the claim does not appear in the source.

## Quotation verification

Quoted text must match the source character-for-character within its excerpt
limit. Reconstructed quotations are fabrication even when the paraphrase is
accurate. Report offsets for every verified quotation.

## What you must not do

* Do not rewrite a claim so an available citation fits it.
* Do not upgrade `partially_supports` to `directly_supports` without a new span.
* Do not audit citations you introduced yourself.
* Do not pass a citation you could not check. Mark it `needs_human_review`.

## Output

A citation audit report: per-citation classification with the evidence span and a
support rationale, a fabrication list, a laundering list, a retraction list, a
metadata-error list, and an updated verification status for every Evidence Matrix
row. Any laundering risk or fabricated reference escalates immediately.
