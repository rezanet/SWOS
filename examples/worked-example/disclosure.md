# AI-Use Disclosure

This work was produced using the Scholarly Writing Operating System (SWOS)
v1.0.0, a governed scholarly reasoning platform.

## What the system did

* Planned the research questions, scope, evidence standard and search strategy.
* Retrieved and parsed sources; ran a separate counter-evidence search.
* Verified every citation for existence, metadata correctness, retraction status
  and **passage-level claim support**.
* Constructed the evidence matrix and the argument graph.
* Ran a bounded reviewer panel: citation auditor, methodologist, argument
  examiner, discipline expert, hostile reviewer.
* Drafted the manuscript **from the verified evidence matrix and approved argument
  graph only**.

## What a human did

* Set the research question and scope.
* Approved the memory write.
* Approved the release. The approver is not the author.

## Verifiability

Every claim in the manuscript is traceable to a passage-level evidence span. The
complete audit pack accompanies this work:

* `evidence-matrix.json` - what supports each claim
* `argument-graph.json` - how the argument holds together
* `epg.json` - where every source came from and how it was processed
* `sdl.json` - why each judgement was made, with alternatives and dissent
* `reviewer-findings.json` - what the panel found
* `evaluation-result.json` - the gate results that permitted release
* `governance-gates.json` - the policy checks and their evidence
* `unsupported-claims.md` - **the claim that was tested and withheld**

## Limitations

Retrieval was limited to English-language, open-access sources. This limit was
declared in the research plan before evidence gathering and is restated in the
uncertainty statement. It bounds the conclusion.

## Model and retrieval

Model: operator-selected. Retrieval: OpenAlex v1.2.0, index 2026-01. SWOS is
model-agnostic and retrieval-agnostic; both are recorded in
`evaluation-result.json` under `subject_versions` so that any future change in
output quality can be attributed.
