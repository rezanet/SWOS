# Capability Model

Twenty-eight capabilities in seven groups. Each maps to an owning component and an
evaluation plane, so no capability exists without a home and a measurement.

## Group 1 - Research planning and intake

| # | Capability | Owner | Evaluated by |
|---|---|---|---|
| 1 | Work and genre classification | Intake | scholarly |
| 2 | Research question formulation and decomposition | Research Planner | scholarly |
| 3 | Knowledge-gap identification | Research Planner | retrieval |
| 4 | Evidence-standard selection by discipline | Discipline pack | scholarly |

## Group 2 - Evidence acquisition and source intelligence

| # | Capability | Owner | Evaluated by |
|---|---|---|---|
| 5 | Hybrid retrieval: keyword, vector, citation graph, author graph, venue graph | Research Librarian | retrieval |
| 6 | Full-text evidence extraction, parsing and OCR | Tool layer | retrieval |
| 7 | Source quality scoring and tiering | Source Quality Analyst | retrieval |
| 8 | Counter-evidence and minority-position retrieval | Research Librarian | retrieval |
| 9 | Bibliographic deduplication and identifier resolution | Tool layer | citation |
| 10 | Copyright and licence checking | Governance | governance |
| 11 | Reranking | Tool layer | retrieval |

## Group 3 - Verification

| # | Capability | Owner | Evaluated by |
|---|---|---|---|
| 12 | Citation existence verification | Citation Auditor | citation |
| 13 | Citation metadata verification | Citation Auditor | citation |
| 14 | Passage-level claim-support classification | Citation Auditor | citation |
| 15 | Retraction and correction checking | Source Quality Analyst | citation |
| 16 | Quotation accuracy verification | Citation Auditor | citation |
| 17 | Unsupported-claim and overclaim detection | Evaluation harness | grounding |

## Group 4 - Knowledge structures

| # | Capability | Owner | Evaluated by |
|---|---|---|---|
| 18 | Evidence Matrix construction | Orchestration | grounding |
| 19 | Argument Graph construction (Toulmin, extended) | Argument Architect | scholarly |
| 20 | Scholarly knowledge graph and discipline ontologies | Knowledge layer | scholarly |
| 21 | Contradiction detection | Knowledge layer, RPM | memory_contamination |

## Group 5 - Reasoning and critique

| # | Capability | Owner | Evaluated by |
|---|---|---|---|
| 22 | Multi-mode reasoning: decomposition, ToT, ReAct, reflexion, self-refine, cross-reflection | Orchestration | scholarly |
| 23 | Methodological critique and statistical appraisal | Methodologist | scholarly |
| 24 | Adversarial review and over-association detection | Adversarial Reviewer | adversarial |
| 25 | Interpretive pluralism and rival readings | Discipline packs | scholarly |
| 26 | Prior-art search and novelty assessment | Adversarial Reviewer | adversarial |

## Group 6 - Writing and revision

| # | Capability | Owner | Evaluated by |
|---|---|---|---|
| 27 | Genre-controlled drafting from the Evidence Matrix, with audience adaptation | Editor, Orchestration | scholarly |

## Group 7 - Governance and operations

| # | Capability | Owner | Evaluated by |
|---|---|---|---|
| 28 | Provenance, decision recording, approval, audit and release control | Governance Officer | governance |

## Deferred capabilities

Named, scoped, and deliberately not in v1.0.0:

| Capability | Milestone | Why deferred |
|---|---|---|
| Concept synthesis and analogy discovery | Research-Grade | Requires a mature knowledge graph; premature synthesis is over-association |
| Gap detection at programme scale | Research-Grade | Requires RPM history across multiple works |
| Novelty estimation | Research-Grade | Requires prior-art coverage that v1 retrieval does not guarantee |
| Multi-disciplinary theory building | Product-Grade | Highest false-originality risk in the system |
| Multimodal scholarly reasoning | Research-Grade | Needs the image and object-analysis tool that would also promote the art packs to agents |

Deferring these is a deliberate sequencing choice. Each is a capability whose
failure mode is *false originality* or *over-association* - the two risks hardest
to detect and most damaging to credibility. They are built after the verification
and evaluation planes that would catch their failures, not before.
