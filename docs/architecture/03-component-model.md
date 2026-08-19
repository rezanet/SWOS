# Component Model

Twelve layers. Governance and evaluation are cross-cutting; the rest are ordered
by the flow of work.

| # | Layer | Responsibility | Key outputs |
|---|---|---|---|
| 1 | **Host Adapter Layer** | Maps SWOS contracts into host-native packaging | SKILL.md, plugin manifest, MCP descriptor, capability matrix |
| 2 | **Master Prompt Contract Layer** | Mission, principles, refusal rules, input and output contracts, handoff rules | Versioned prompt contract |
| 3 | **Orchestration Layer** | Plans work, routes agents, manages state, applies gates and stop conditions | Plan, task graph, reviewer route, state transitions |
| 4 | **Tool Layer** | Acquires, parses, validates and enriches evidence | Evidence package, source records, extracted passages |
| 5 | **Knowledge Structures Layer** | Converts retrieved material into reasoning structures | Knowledge graph, discipline ontologies |
| 6 | **Evidence Layer** | Atomic claim-to-source mapping | Evidence Matrix, argument graph inputs |
| 7 | **Provenance Layer** | Records how every artefact was produced or derived | PROV-compatible EPG bundles |
| 8 | **Decision Layer** | Records why judgements were made | Scholarly Decision Ledger |
| 9 | **Memory Layer** | Preserves continuity without corrupting facts | Episodic, semantic, reflective, user and programme memory |
| 10 | **Evaluation Layer** | Measures evidence, retrieval, reasoning, writing and governance quality | Evaluation Result, acceptance scorecard |
| 11 | **Governance Control Plane** | Policy, risk, access, approval, audit, lifecycle | Gate records, audit pack, approval and incident records |
| 12 | **Output Layer** | Produces manuscript plus proof pack | Draft plus the thirteen audit-pack artefacts |

## Component boundaries that matter

### Evidence Matrix vs Argument Graph vs EPG vs SDL

These four are routinely conflated. They are not the same thing, and merging any
pair destroys a capability.

| Component | Correct role | Anti-pattern |
|---|---|---|
| **Evidence Matrix** | Atomic claim-to-source map with span, support level, epistemic type, confidence, counter-evidence, verification status | Becoming a provenance ledger |
| **Argument Graph** | Thesis, claims, warrants, evidence, backing, qualifiers, rebuttals, objections, rival readings | Storing raw source metadata |
| **EPG** | Entities, activities, agents, derivations, collections, bundles per W3C PROV | Becoming a judgement log |
| **SDL** | Why a judgement was made, alternatives, evidence basis, approver, reversibility | Duplicating Evidence Matrix rows |
| **RPM** | Long-running governed continuity across projects | Storing unsupported reflections as facts |

The test is the question each answers:

* Evidence Matrix - *what supports this claim?*
* Argument Graph - *how does the argument hold together?*
* EPG - *where did this come from and how was it produced?*
* SDL - *why was this judgement made?*
* RPM - *what has this programme already settled?*

### Why the EPG must not become a judgement log

The EPG's highest-value operation is the **blast-radius query**: when a source is
retracted, which claims used it, which outputs used those claims, which memory
items derive from them, and who cites those outputs. That query is fast and
correct only if the EPG is a clean lineage graph. Mixing judgement records into it
turns a graph traversal into a text search.

## Deployment neutrality

The component model specifies responsibilities and interfaces, not deployment.
The state store, policy engine, provenance store, decision ledger, memory service
and evaluation runner may each be a library, a service, a database or a file on
disk. SWOS specifies what each must guarantee - append-only, tamper-evident,
queryable by identifier - not what technology provides it.
