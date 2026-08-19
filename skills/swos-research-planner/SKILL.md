---
name: swos-research-planner
description: Produces a governed research plan before any evidence is gathered or any prose is written. Use at the start of a literature review, systematic or scoping review, research article, thesis chapter, technical investigation, or enterprise research report. Decomposes a topic into research questions and subtopics, identifies knowledge gaps, selects the discipline evidence hierarchy and proof standard, designs the search strategy including deliberate counter-evidence and minority-position retrieval, sets the evidence budget, generates rival thesis candidates, and states known uncertainties up front. Use when someone is about to start researching and needs the plan that makes the research defensible.
license: MIT
compatibility: Works without retrieval tools - planning is a design activity. Retrieval improves gap detection and seminal-work identification but is not required. No specific model or host required.
metadata:
  version: 1.0.0
  swos_component: orchestration
  spec: agent-skills
---

# SWOS Research Planner

A research plan is a **precondition**, not a courtesy. Rule #3 means no drafting
happens until this exists.

## What you produce

1. **Research question** - one primary, precisely scoped.
2. **Sub-questions** - the decomposition that makes the primary question answerable.
3. **Scope** - explicitly including what is *out* of scope and why.
4. **Discipline and evidence standard** - which pack governs, what counts as
   strong evidence here, what discharges the burden for a claim.
5. **Search strategy** - corpora, query families, citation-graph walks, date
   bounds, language coverage, and the **counter-evidence strategy as a separate
   named component**.
6. **Evidence budget** - how much evidence a claim of each epistemic type requires
   before it may be asserted.
7. **Rival thesis candidates** - at least two, at least one genuinely opposed.
8. **Method or interpretation plan** - the analytical approach, and its limits.
9. **Known uncertainties** - declared before evidence, so they cannot be
   retrofitted afterwards.
10. **Reviewer plan** - which reviewer roles this work requires and why.

## Decomposition heuristic

For an interdisciplinary topic, decompose by **discipline lens** before
decomposing by subtopic. "Aesthetics in AI-generated art" is not one literature;
it is philosophy of aesthetics, art history, computational creativity, psychology
of perception and current critical debate - each with a different evidence
hierarchy and a different proof standard. Planning by subtopic alone silently
imports one discipline's standards into another's questions.

## Coverage-bias controls to build into the strategy

* Name the languages and regions the strategy will and will not reach.
* Include at least one query family aimed at **minority or dissenting positions**.
* Include a seminal-work walk via citation graph, not popularity ranking alone.
* Set a source-diversity target and state how it will be measured.

State these as commitments in the plan. Coverage limits declared in advance are
scholarship; coverage limits discovered afterwards are excuses.

## Gap identification

Distinguish four gap types, because they have different remedies:

| Gap | Remedy |
|---|---|
| Evidence gap - nobody has measured this | Declare as future work; do not infer across it |
| Synthesis gap - measured separately, never connected | This may be the contribution; prior-art check required |
| Method gap - measured with an inadequate method | Methodologist appraisal, qualified claims |
| Access gap - exists but unreachable from here | Declare explicitly in the coverage report |

An access gap presented as an evidence gap is a false originality claim in
embryo.

## Output

A plan document plus an initialised Scholarly State record at state `planned`,
plus SDL scope decisions for every default that was applied rather than specified.
