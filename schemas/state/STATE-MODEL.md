# Scholarly State Model

The lifecycle spine of SWOS. Every claim, evidence record, decision, memory item,
reviewer finding and output carries a state. This is what makes Rule #3 - *no
drafting until the research plan, evidence matrix, argument graph, provenance
graph and decision ledger exist* - a machine-enforceable precondition rather than
an instruction the model may forget.

## Canonical states

| Scholarly state | AI SDLC phase | Governance checkpoint | EPG state | SDL event |
|---|---|---|---|---|
| `initiated` | Discover | Use case and scope registered | Empty bundle | Initiation rationale |
| `planned` | Design | Evidence standard agreed | Query plan | Scope decision |
| `evidence_gathering` | Build | Source policy enforced | Retrieval events | Search decisions |
| `evidence_verified` | Validate | Citation and support gate | Verified spans | Inclusion and exclusion |
| `argument_constructed` | Validate | Argument review | Claim graph | Thesis and warrant choice |
| `draft_generated` | Build | Draft from evidence matrix only | Output derivation | Draft decision |
| `reviewed` | Validate | Expert and adversarial review | Review bundle | Review outcome |
| `revised` | Validate | Regression check | Revision derivation | Change rationale |
| `approved` | Release | Human approval | Release bundle | Approval decision |
| `published` | Release | Disclosure and audit pack | Published artefact | Publication gate |
| `monitored` | Operate | Quality and incident monitoring | Telemetry links | Monitoring decision |
| `superseded` | Evolve | New evidence or version | Supersession relation | Supersession rationale |
| `retired` | Retire | Archive and de-registration | Archived bundle | Retirement decision |

## Transition preconditions

A transition is refused, logged to `blocked_transitions`, and raised as a
governance event when its preconditions are unmet.

| Transition | Preconditions |
|---|---|
| `initiated -> planned` | Intake record complete; risk class assigned; discipline pack selected; evidence standard agreed |
| `planned -> evidence_gathering` | Research questions, search strategy and source constraints recorded; source-rights policy bound |
| `evidence_gathering -> evidence_verified` | Every retrieval logged as an EPG activity; licence and retraction checks run on every `source_instance` |
| `evidence_verified -> argument_constructed` | Every Evidence Matrix row has `verification_status` in `{pass, needs_human_review}`; no row left `not_yet_verified`; counter-evidence search executed |
| `argument_constructed -> draft_generated` | **Rule #3 gate.** Research plan, Evidence Matrix, Argument Graph, EPG bundle and SDL all exist and validate. Thesis has at least one warrant with `evidence_claim_ids` |
| `draft_generated -> reviewed` | Draft cites only claim ids present in the Evidence Matrix. Any citation not traceable to a matrix row fails the transition |
| `reviewed -> revised` | At least the citation auditor, argument examiner and one discipline expert have produced a Reviewer Finding |
| `revised -> reviewed` | Iteration counter incremented. **Cap: 3.** On the fourth attempt the work escalates to a human rather than looping |
| `revised -> approved` | No `blocker` findings open; unsupported-claim list empty or every entry explicitly marked in the draft; evaluation result present with all gates `pass` |
| `approved -> published` | Audit pack assembled; provenance bundle frozen; AI-use disclosure generated; human approver recorded in SDL |
| `published -> monitored` | Telemetry bound; retraction watch registered for every cited `source_instance` |
| `monitored -> superseded` | New evidence, retraction, or corrected source detected; superseding work id recorded |
| `any -> retired` | Retirement checklist complete; provenance archived; deletion evidence recorded |

## Why blocked transitions are logged, not swallowed

An agent that attempts to draft before evidence is verified has revealed
something about the orchestration, the prompt contract, or the work itself.
Silently retrying destroys that signal. `blocked_transitions` is a first-class
telemetry source: a rising rate of blocked `draft_generated` attempts is an early
indicator of contract drift.
