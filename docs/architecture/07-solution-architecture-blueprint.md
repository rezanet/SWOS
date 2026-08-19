# Solution Architecture Blueprint

The consolidated view: layers, ownership, state, control points, NFRs and
integration boundaries.

## Layered view

```
+=========================================================================+
|  GOVERNANCE CONTROL PLANE                        (cross-cutting)        |
|  policy engine . risk classifier . access . approval . audit . incident |
|  NIST AI RMF: GOVERN infused through MAP, MEASURE, MANAGE               |
+=========================================================================+
|  EVALUATION PLANE                                (cross-cutting)        |
|  retrieval | grounding | citation | scholarly | governance              |
|  regression | memory contamination | adversarial      -> RELEASE GATE   |
+=========================================================================+

  [1] HOST ADAPTER LAYER
      agent-skills | claude-code | codex | mcp | cli | ide
      capability matrix declares what the host CANNOT do
              |
              v
  [2] MASTER PROMPT CONTRACT LAYER
      mission . principles . input contract . handoff . output contract
      abstention rules . seven non-negotiable rules
              |
              v
  [3] ORCHESTRATION LAYER
      plan -> route -> gate -> assemble ; owns state transitions
      bounded review loops (cap 3) ; escalation
              |
              v
  [4] TOOL LAYER                          ---- security boundary ----
      scholarly/enterprise search . parse . OCR . DOI . metadata
      retraction . licence . passage-support . counter-evidence . rerank
      RETRIEVED CONTENT IS DATA, NEVER INSTRUCTION
              |
    +---------+---------+-----------------+------------------+
    v                   v                 v                  v
  [5] KNOWLEDGE      [6] EVIDENCE      [7] PROVENANCE     [8] DECISION
      STRUCTURES         LAYER             LAYER              LAYER
      knowledge graph    Evidence Matrix   EPG (W3C PROV)     SDL
      discipline         claim->span       entities/          why, not what
      ontologies         support level     activities/agents  append-only
                         epistemic type    bundles            tamper-evident
    +---------+---------+-----------------+------------------+
                        |
                        v
  [9] MEMORY LAYER                        [10] EVALUATION LAYER
      working | episodic | semantic            harness . golden sets
      reflective | user | RPM                  rubrics . regression
      write requires EPG + SDL + expiry        hidden sets
                        |
                        v
  [12] OUTPUT LAYER
      manuscript + AUDIT PACK (13 artefacts)
      no audit pack = not a SWOS output
```

## Control points

| # | Control point | Blocks | Owner |
|---|---|---|---|
| C1 | Governance pre-check at intake | Evidence gathering | Governance Officer |
| C2 | Source-rights gate | Store and export | Governance Officer |
| C3 | Data-classification ceiling | Tool calls | Policy engine |
| C4 | Citation support classification | `evidence_verified` transition | Citation Auditor |
| C5 | **Rule #3 gate** | `draft_generated` transition | Orchestrator |
| C6 | Reviewer blocker findings | `approved` transition | Reviewer panel |
| C7 | Evaluation planes | Release | Evaluation harness |
| C8 | Provenance completeness | Release | Governance Officer |
| C9 | Human approval threshold | Release, export, override, memory write | Approval matrix |
| C10 | Memory write gate | Durable memory | Policy engine |

**C5 is the load-bearing control.** Everything upstream produces evidence;
everything downstream consumes it. If C5 leaks, every other control is auditing a
document whose claims were never grounded.

## State

| Store | Property | Consistency |
|---|---|---|
| Scholarly State | Single current state plus full history | Strongly consistent; transitions serialised |
| Evidence Matrix | Mutable until `evidence_verified`, then append-only | Strongly consistent |
| Argument Graph | Mutable until `approved` | Strongly consistent |
| EPG | Append-only; bundles frozen at publication | Append-only, hash-chained |
| SDL | Append-only; supersession, never mutation | Append-only, hash-chained |
| RPM | Mutable via correction only; expiry is a visibility change | Eventually consistent across works |
| Evaluation Results | Immutable per run | Immutable |
| Gate Records | Immutable | Immutable |

## Integration boundaries

| Boundary | Protocol | Substitutable |
|---|---|---|
| Host to SWOS | Agent Skills packaging, or CLI, or API | Yes - six adapters ship |
| SWOS to tools | Tool contract; MCP optional | Yes - any transport |
| SWOS to model | None. SWOS never assumes a model | Yes - fully model-agnostic |
| SWOS to retriever | Tool contract, `scholarly_search` class | Yes - retrieval-agnostic |
| SWOS to storage | Store guarantees, not technologies | Yes - file, database or service |
| SWOS to identity | Access model principals | Yes - enterprise identity at Product-Grade |

## The defensible asset

Not the prompt. Prompts get copied. The durable advantage is the governed
reasoning infrastructure:

* the EPG schema and its validation rules
* the SDL schema and its governance semantics
* the citation-support classifier and the citation-laundering test suite
* discipline-specific reasoning packs
* reviewer simulation rubrics and acceptance tests
* the RPM model and memory-governance policies
* the evaluation harness and the hidden benchmark factory
* portability contracts across hosts, runtimes, models and retrievers
* the provenance-preserving export format
* the governance-by-design lifecycle and audit model

For an MIT-licensed project the moat is not secrecy. It is the quality of the
schemas, the test suites, the community benchmarks, the discipline ontologies,
provenance interoperability, and trusted contributor governance.
