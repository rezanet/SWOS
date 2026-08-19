# Agent Prompt Pack

Nine core agents. Each is a **bounded role, not a personality**.

| Agent | One-line responsibility |
|---|---|
| [Orchestrator](orchestrator.md) | Decompose, route, gate, assemble; owns state transitions |
| [Research Librarian](research-librarian.md) | Search strategy, recall, diversity, counter-positions |
| [Source Quality Analyst](source-quality-analyst.md) | Tier sources against the discipline's evidence hierarchy |
| [Citation Auditor](citation-auditor.md) | Existence, metadata, passage-level claim support (Rule #5) |
| [Argument Architect](argument-architect.md) | Evidence Matrix into an explicit Toulmin Argument Graph |
| [Methodologist](methodologist.md) | Method, design, statistics, bias, causal licence |
| [Adversarial Reviewer](adversarial-reviewer.md) | Attack the weakest load-bearing element |
| [Editor](editor.md) | Structure, clarity, genre fit - without changing meaning |
| [Governance Officer](governance-officer.md) | Policy, rights, audit, approval, release gates |

## Every agent contract declares six things

1. **Inputs** - the only artefacts it may read
2. **Outputs** - the only artefacts it may write
3. **Tools** - the only tools it may call
4. **Decisions allowed** - each one writes an SDL entry
5. **Escalation conditions** - when it stops rather than improvises
6. **Acceptance criteria** - what the Orchestrator checks before accepting output

Reviewer agents additionally declare test, pass, fail and escalation criteria in
`reviewer-packs/`.

## Why discipline specialists are not in this pack

Philosophy, psychology, materials science, humanities, art history and art
criticism ship as **discipline packs** - rubrics, ontologies, evidence
hierarchies and reasoning modules - not as agents. See `adr/ADR-0005`.

Promotion of a discipline pack to an agent requires one of:

* a discipline-specific tool that no other role calls (for example an image or
  object-analysis tool for art disciplines);
* a workflow whose reliable scope genuinely exceeds a single agent's.

Turning every noun into an agent buys coordination overhead, latency and new
failure modes, and buys no epistemic control.

## Roster tiers

| Tier | Members | Status |
|---|---|---|
| Core - always instantiated | The nine above | v1.0.0 |
| Discipline packs - activated on demand | philosophy, psychology, materials science, technical writing, engineering, humanities, art history, art criticism, interdisciplinary | v1.0.0 as packs |
| Deferred | Novelty estimator, gap detector, multi-disciplinary theory builder, research programme generator | Research-Grade milestone |
