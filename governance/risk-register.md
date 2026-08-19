# Risk Register

Eight named risks. Each has an owner, a control and a detection method. A risk
without a detection method is a hope.

| # | Risk | Why it matters | Control | Detection |
|---|---|---|---|---|
| R1 | **Citation laundering** | A real source is attached to a claim it does not support | Passage-level citation-support classification; SDL rationale for every support judgement | Citation plane; `evals/fixtures/adversarial/citation-laundering-*` |
| R2 | **False originality** | Known ideas are reframed as novel | Prior-art search, genealogy graph, novelty ledger | Adversarial plane; hostile reviewer prior-art check |
| R3 | **Over-association** | Unrelated facts are made to look coherent | Relation-confidence scoring on every argument edge; adversarial review of low-confidence edges | Adversarial plane; relation-confidence distribution monitoring |
| R4 | **Method blindness** | Prose sounds expert while the method is weak | Dedicated methodologist role; discipline method checklists | Scholarly plane; discipline rubric thresholds |
| R5 | **Memory contamination** | Unsupported reflections become future "facts" | Governed memory writes requiring EPG support and SDL rationale; contradiction handling | Memory-contamination plane; seeded false-prior fixtures |
| R6 | **Evaluation gaming** | The system optimises for rubrics rather than scholarship | Rotating rubrics, hidden test sets, pairwise expert review, separation of contract and evaluation owners | Score improvement without human-preference improvement |
| R7 | **Privacy and IP exposure** | Scholarly tools ingest protected material | Licence checks, metadata-first logging, data minimisation, third-party due diligence | Governance plane; source-rights gate; egress denials |
| R8 | **Agent autonomy drift** | Agents exceed intended boundaries | Declared `decisions_allowed` and `escalation_conditions`; static tool sets; logging and human override | Governance plane; out-of-scope action detection |

## Additional named failure modes

Tracked but folded into the controls above rather than carried as separate risks:

* **Coverage bias** - retrieval favours accessible, popular or English-language
  sources. Control: source diversity targets, minority-position retrieval, declared
  coverage limits. Detection: retrieval plane source-diversity index.
* **Interpretive flattening** - humanities output collapses ambiguity into a
  single safe reading. Control: `rival_reading` as a first-class argument node,
  mandatory in interpretive disciplines. Detection: scholarly plane.
* **Tacit judgement gap** - experts know what matters without formalising it.
  Control: human expert review on high-value outputs. Detection: not automatable;
  this is why the discipline expert escalates rather than substitutes.
* **Automation anchoring** - human reviewers accept polished AI suggestions too
  readily. Control: blind review, forced objections, unsupported-claims-first
  approval packs. Detection: approval time versus finding count.
* **Governance theatre** - audit exists but never blocks. Control: gates that
  return `fail` and block CI. Detection: a release history with zero blocked
  releases is itself a warning sign.
* **Portability decay** - skills depend on one host. Control: six-field
  frontmatter constraint, capability matrices. Detection: `make lint-skills`.
