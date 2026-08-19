# Vision and Principles

## Vision

SWOS is a portable, governed scholarly reasoning platform supporting technical
writing, enterprise reporting, engineering, philosophy, psychology, materials
science, humanities, art history, art criticism and interdisciplinary
scholarship.

It operates like a research institute in software: **evidence is acquired before
prose, arguments are explicit, provenance is preserved, decisions are logged,
reviewers are role-based, memory is governed, and release requires evaluation
evidence.**

It produces not only a draft, but the evidence matrix, argument graph, citation
audit, reviewer simulation, decision ledger, uncertainty statement and governance
pack. That is the difference between a writing assistant and a scholarly
operating system.

## The problem being solved

The real problem is not prose. It is **epistemic control**: what counts as
evidence, what counts as interpretation, what level of confidence is justified,
which claims lack support, and which decisions must survive audit.

A system that solves prose and not epistemic control produces fluent, plausible,
well-cited-looking output whose failures are invisible precisely because it is
fluent. The architecture must define authoritative stores, control boundaries,
lifecycle states, verification gates, provenance, decision records, memory rules
and evaluation evidence. Otherwise it becomes a beautifully worded liability.

## Nine principles

### 1. Evidence before prose
No draft until an evidence plan, evidence matrix and citation-support
classification exist. This is Rule #3 and it is the centre of gravity of the
entire design.

### 2. Prompt last, architecture first
Prompts set roles, standards and output contracts. Tools, memory, knowledge
structures, provenance, evaluation and governance provide the control surface.
If a requirement can be solved outside the prompt, it must be.

### 3. Every claim has an epistemic status
Observed fact, source-backed claim, inference, interpretation, hypothesis,
speculation, normative judgement, critical assessment, unverified claim. A system
that cannot distinguish these cannot be trusted with any of them.

### 4. Every citation has a support relationship
Citation existence is insufficient. Classify whether the passage directly
supports, partially supports, contextualises, contradicts or fails the claim.

### 5. Argument is a graph, not paragraph soup
Claims, warrants, backing, objections, rebuttals, implications and rival readings
are represented explicitly, so their absence is detectable.

### 6. Memory is governed, not merely long
Control how memory is read, written, updated, contradicted, expired and deleted.
Unsupported reflection never becomes fact.

### 7. Review is role-based
"Review critically" is not an architecture. Reviewer simulation needs citation
auditors, methodologists, argument examiners, discipline experts, hostile
reviewers, editors and governance reviewers - each with test, pass, fail and
escalation criteria.

### 8. Governance is continuous
Governance overlays the whole lifecycle - Discover, Design, Build, Validate,
Release, Operate, Evolve or Retire - as a cross-cutting function, not a gate at
the end. Audit metadata is preferred to raw sensitive content.

### 9. Portability is preserved by contract
Contracts, schemas, events and evaluation artefacts are defined independently of
implementation tools. Every host, model, retriever and store is replaceable
without changing a scholarly contract.

## What SWOS refuses to be

* A prose stylist that improves fluency without touching evidence.
* One giant prompt with the architecture hidden in prose.
* A vendor-bound product.
* An autonomous publisher. Human accountability for final judgement is a
  principle, not a configuration option.

## Treat fluency as a risk signal

This deserves separate statement because it inverts the intuition most systems
are built on. In SWOS, fluent output with thin evidence is a **more** dangerous
result than rough output with strong evidence, because fluency suppresses the
reader's scrutiny exactly when scrutiny is most needed. Every control in the
platform follows from taking that seriously.
