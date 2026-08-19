# Changelog

Format follows Keep a Changelog. Versioning is Semantic Versioning applied to
**contracts and schemas**, not to prose.

## [1.0.0] - Specification Lock

The v1.0.0 release freezes the contract and schema layer. This is the release the
architecture assessment called for: do not spend the next milestone polishing
prompt wording or adding agents - spend it extracting contracts.

### Added - Contracts
* Master Prompt Contract: mission, principles, input contract, handoff rules,
  output contract, abstention rules, the seven non-negotiable rules
* Agent Prompt Pack: nine core agents, each with inputs, outputs, tools,
  decisions allowed, escalation conditions, acceptance criteria
* Tool Contract: typed tool interfaces, injection defence, egress rules
* Memory Governance Contract, split out of the tool contract as recommended
* Host Adapter Contract, making the six-field frontmatter constraint normative
* Evaluation Contract: planes, gates, thresholds

### Added - Schemas (frozen)
* `evidence-matrix.schema.json`
* `argument-graph.schema.json`
* `epg.schema.json` - W3C PROV-DM compatible, including bundles
* `sdl.schema.json`
* `rpm.schema.json`
* `reviewer-finding.schema.json`
* `evaluation-result.schema.json`
* `governance-gate.schema.json`
* `scholarly-state.schema.json` - the lifecycle spine

### Added - Knowledge
* Knowledge & Reasoning Specification as a standalone artefact: epistemic
  typology, citation-support taxonomy, uncertainty taxonomy, argument schema,
  evidence hierarchy, discipline ontologies, reasoning standards

### Added - Governance
* Policy-as-code: source-rights gate, memory-write approval, human-approval
  threshold matrix, provenance-completeness check, release gate, incident and
  correction workflow, retention and deletion policy
* NIST AI RMF 1.0 crosswalk across Govern, Map, Measure, Manage
* Eight-entry risk register with named controls

### Added - Evaluation
* Eight-category harness: retrieval, grounding, citation, scholarly quality,
  governance, regression, memory contamination, adversarial
* Golden, adversarial and regression fixtures
* Release gates enforced in CI, not in documentation

### Added - Portability
* Adapters for Agent Skills, Claude Code, Codex, MCP, CLI and IDE agents
* Four core skills packaged to the Agent Skills open specification

### Decisions of record
* EPG and SDL are separate artefacts. EPG answers where from and how produced;
  SDL answers why this judgement. See `adr/ADR-0004`.
* Discipline specialists ship as packs, not agents. Promotion to an agent
  requires a specialised tool or workflow. See `adr/ADR-0005`.
* MCP is optional, never mandatory. See `adr/ADR-0009`.

### Known gaps carried to 1.1
* No reference retrieval corpus is bundled. Adapters exist; corpus choice is the
  operator's.
* The cross-encoder reranker is specified in the tool contract but has no
  reference implementation.
* Novelty estimator, gap detector and theory builder remain out of scope until
  the Research-Grade milestone.
