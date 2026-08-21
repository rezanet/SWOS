# SWOS - Scholarly Writing Operating System

**SWOS is not a chatbot and not a prompt. It is a governed research institute in
software form: a host-agnostic, model-agnostic, retrieval-agnostic scholarly
reasoning platform.**

SWOS does not optimise for prose. It optimises for trustworthy scholarly
reasoning - epistemic correctness, evidence traceability, methodological rigour,
reproducibility, governance compliance and auditability.

`contracts frozen v1.0.0` · `SWOS Prose v0.2.0` · `MIT` · `provenance: W3C PROV-DM` · `governance: NIST AI RMF 1.0`

---

## SWOS Prose v0.2

**SWOS Prose is the post-draft semantic-safe editing layer: rewrite the language,
preserve the meaning.** It operates after claims and evidence are settled, and it
fails closed to the source whenever a proposed rewrite cannot be approved safely.

The v0.2 released surface implements `mode=polish` only. It combines conservative
pre-generation diagnostics, one rewrite proposal when needed, deterministic
semantic-delta checks, and independent semantic verification. `REVIEW`, `REJECT`
or provider failure never silently releases the candidate.

The active governed benchmark contains 56 cases. The frozen v0.2 release evidence
remains preserved at [`benchmark/artifacts/raw-evidence-v0.2/`](benchmark/artifacts/raw-evidence-v0.2/)
and its compact claim surface is [`benchmark/baseline.json`](benchmark/baseline.json);
that historical evidence covers 50 cases and is not the active runner input. On the
frozen benchmark SWOS Prose recorded **0 unsafe semantic PASS outcomes**, **0 unsafe
diagnostic abstentions**, and **3.04% token savings** from its intentionally tiny
exact-exemplar diagnostics fast path. Equivalent-pair verifier wobble remains visible
and is tracked separately rather than being disguised as a safety success.

- Portable skill: [`skills/swos-prose/SKILL.md`](skills/swos-prose/SKILL.md)
- Frozen baseline: [`benchmark/baseline.json`](benchmark/baseline.json)
- Evidence provenance: [`benchmark/FROZEN_AT`](benchmark/FROZEN_AT)
- Python implementation: [`swos_prose/`](swos_prose/)

```bash
export OPENAI_API_KEY=...
python3 -m swos_prose.cli polish \
  --source "The analysis was performed using a t-test." \
  --assurance strict \
  --json
```

SWOS Prose does not establish whether the source is true or adequately supported.
Use the evidence-first SWOS workflow and citation audit before polishing.

---

## Why SWOS exists

A master prompt can define roles, behaviour, standards and output contracts. It
**cannot** guarantee citation verification, memory, provenance, source retrieval,
access control, evaluation, auditability or expert review. Those belong in the
surrounding system.

The evidence is unambiguous. Published benchmark work on scholarly synthesis
reports that general-purpose frontier models fabricate citations in the large
majority of scientific queries, and that the dominant residual failure in
long-form generated articles is not classic hallucination but *red herrings* -
shaky links and irrelevant content presented as coherent synthesis. Fluency is
therefore a **risk signal, not a quality signal**.

SWOS answers that with architecture, not adjectives.

## What SWOS can write, and for whom

SWOS supports evidence-grounded writing across humanities, arts, social sciences,
technical domains and enterprise contexts, as long as sources can be retrieved
and verified.

| Output type | Typical subjects | Primary audiences |
|---|---|---|
| Research article | Philosophy, psychology, history, materials science, engineering | Researchers, graduate students, reviewers |
| Literature review / state-of-the-field | Art history, humanities, interdisciplinary topics | Scholars, educators, policy teams |
| Critical essay / position analysis | Art criticism, philosophy, cultural studies | General readers, critics, students |
| Method critique | Experimental design, causal claims, statistical interpretation | Methods readers, reviewers, advanced learners |
| Enterprise analytical report | Governance, risk, policy, technical evaluation | Decision-makers, audit/compliance teams, interested non-specialists |

The audience range is intentionally broad: artists, philosophers, historians,
technical readers and non-specialists who still need transparent evidence trails.

## Why this is better than common alternatives

| Alternative | Typical failure mode | SWOS advantage |
|---|---|---|
| Single giant prompt | Fluent prose with weak or invisible evidence | Contracts, schemas and gates make controls machine-checkable |
| Draft-first workflow | Claims appear before verification | Rule #3 blocks drafting until planning, evidence and argument artefacts exist |
| Reviewer swarm on weak retrieval | More critique chatter, same weak sources | Retrieval, verification and reranking are enforced before reviewer loops |
| Style-first editing pipeline | Confidence language outruns support | Editor role is constrained by evidence and audit requirements |

## How to read this repository

If you want the narrative first:

1. `README.md` (this document)
2. `SWOS-Solution-Architecture.md`
3. `docs/knowledge-and-reasoning-spec.md`

If you want implementation details and controls:

1. `contracts/`
2. `schemas/`
3. `governance/policies/`
4. `evals/harness/`

---

## The seven non-negotiable rules

These are constitutional. They are enforced by
[`contracts/master-prompt-contract/`](contracts/master-prompt-contract/) and by
machine-checkable gates in [`governance/`](governance/) and [`evals/`](evals/).

| # | Rule |
|---|------|
| **1** | Do not build a giant prompt. Build contracts, schemas, specifications, workflows, governance models, evaluation systems and portable skills. |
| **2** | If a requirement can be solved outside the prompt, it **must** be solved outside the prompt. |
| **3** | No drafting is allowed until a research plan, evidence matrix, argument graph, provenance graph and decision ledger exist. |
| **4** | Every factual claim must be supported, marked uncertain, or removed. |
| **5** | Every citation must be verified for existence, for metadata, and for claim support. |
| **6** | Every scholarly decision must be traceable. |
| **7** | Every final output must be auditable. |

---

## The nine first-class components

The prompt is not the product. **These are the product.**

| Component | Answers | Spec |
|---|---|---|
| **Evidence Matrix** | *What supports this claim?* | [`schemas/evidence-matrix/`](schemas/evidence-matrix/) |
| **Argument Graph** | *How does the argument hold together?* | [`schemas/argument-graph/`](schemas/argument-graph/) |
| **Evidence Provenance Graph (EPG)** | *Where did it come from and how was it produced?* | [`schemas/provenance-graph/`](schemas/provenance-graph/) |
| **Scholarly Decision Ledger (SDL)** | *Why was this judgement made?* | [`schemas/decision-ledger/`](schemas/decision-ledger/) |
| **Research Program Memory (RPM)** | *What has this research programme already settled?* | [`schemas/memory/`](schemas/memory/) |
| **Knowledge & Reasoning Specification** | *What may the system mean by "evidence"?* | [`docs/knowledge-and-reasoning-spec.md`](docs/knowledge-and-reasoning-spec.md) |
| **Reviewer Simulation System** | *Who attacks this, and against what criteria?* | [`reviewer-packs/`](reviewer-packs/) |
| **Evaluation Harness** | *May this be released?* | [`evals/`](evals/) |
| **Governance Control Plane** | *Who is accountable, and is it auditable?* | [`governance/`](governance/) |

---

## Architecture in one screen

```
                     +-------------------------------------------+
                     |        GOVERNANCE CONTROL PLANE (11)      |  cross-cutting
                     |  policy . risk . access . approval . audit|  (NIST AI RMF: Govern)
                     +-------------------------------------------+

  +-----------+   +---------------+   +--------------+   +----------------------+
  | 1 HOST    |-->| 2 MASTER      |-->| 3 ORCHES-    |-->| 4 TOOL LAYER         |
  |  ADAPTER  |   |   PROMPT      |   |   TRATION    |   | search . DOI . OCR   |
  |  LAYER    |   |   CONTRACT    |   |   LAYER      |   | retraction . licence |
  +-----------+   +---------------+   +--------------+   +----------------------+
                                             |                      |
       +-------------------------------------+----------------------+
       v                 v                   v                v
  +---------+      +-----------+      +-----------+     +-----------+
  | 5 KNOW- |      | 6 EVIDENCE|      | 7 PROVEN- |     | 8 DECISION|
  |  LEDGE  |      |   LAYER   |      |   ANCE    |     |   LAYER   |
  |  STRUCT |      | (Ev.Matrix|      |   (EPG)   |     |   (SDL)   |
  +---------+      +-----------+      +-----------+     +-----------+
       |                 |                  |                 |
       +-----------------+--------+---------+-----------------+
                                  v
                     +------------------------+    +----------------+
                     | 9 MEMORY LAYER (RPM)   |    | 10 EVALUATION  |
                     +------------------------+    |    LAYER       |
                                                   +----------------+
                     +-------------------------------------------+
                     | 12 OUTPUT LAYER - manuscript + AUDIT PACK |
                     +-------------------------------------------+
```

Full component and interface model: [`docs/architecture/`](docs/architecture/).

---

## Repository guide

| Area | Why it exists |
|---|---|
| [`contracts/`](contracts/) | Behavioural contracts for prompt, agents, tools, memory, adapters and evaluation |
| [`schemas/`](schemas/) | Frozen JSON Schemas (machine-checkable spine) |
| [`skills/`](skills/) | Portable Agent Skills packages (six-field frontmatter) |
| [`adapters/`](adapters/) | Host overlays for Agent Skills, Claude Code, Codex, MCP, CLI and IDE |
| [`discipline-packs/`](discipline-packs/) | Discipline-specific rubrics, ontologies and reasoning rules |
| [`reviewer-packs/`](reviewer-packs/) | Reviewer roles with pass/fail/escalation criteria |
| [`governance/`](governance/) | Policy-as-code, risk and approval models, RMF crosswalk |
| [`evals/`](evals/) | Eight-plane evaluation harness and fixtures |
| [`benchmark/`](benchmark/) | Governed SWOS Prose corpus, frozen baseline and raw evidence provenance |
| [`examples/`](examples/) | Worked example with a full audit pack |
| [`docs/`](docs/) | Architecture and operations documents |
| [`adr/`](adr/) | Architecture decisions and rationale history |
| [`tools/`](tools/) | Validators and CI lint/verification utilities |

---

## Quick start

```bash
make validate          # every artefact against the frozen schemas
make lint-skills       # six-field Agent Skills frontmatter constraint
make eval              # all eight evaluation planes
make benchmark-prose   # deterministic active 56-case prose benchmark contract
ls examples/worked-example/   # a complete output bundle with audit pack
```

`make ci` is exactly what CI runs. A release is blocked unless it passes.

---

## Installing SWOS into a host

SWOS core skills use **only the six fields the Agent Skills specification
allows** - `name`, `description`, `license`, `compatibility`, `metadata`,
`allowed-tools`. Every host-specific capability lives in an adapter overlay,
never in the core skill.

| Host | Install | Adapter |
|---|---|---|
| Any Agent Skills runtime | copy `skills/*` into the skills directory | [`adapters/agent-skills/`](adapters/agent-skills/) |
| Claude Code | copy skills, then apply the overlay | [`adapters/claude-code/`](adapters/claude-code/) |
| OpenAI Codex / ChatGPT | place under `.agents/skills/`, add `agents/openai.yaml` | [`adapters/codex/`](adapters/codex/) |
| MCP-capable host | run the SWOS MCP server descriptor | [`adapters/mcp/`](adapters/mcp/) |
| CLI / CI | `swos run --contract master --work-id ...` | [`adapters/cli/`](adapters/cli/) |
| IDE agents | workspace-scoped skill discovery | [`adapters/ide/`](adapters/ide/) |

See [`docs/portability-and-adapter-spec.md`](docs/portability-and-adapter-spec.md).

---

## What SWOS produces

SWOS never returns only a draft. Every release produces an **output bundle**:

1. Final manuscript or report
2. Executive summary
3. Evidence matrix
4. Argument map
5. Citation audit
6. Unsupported-claim list
7. Counter-evidence list
8. Reviewer simulation notes
9. Revision log
10. Provenance bundle (PROV-compatible)
11. Decision ledger extract
12. Uncertainty statement
13. Governance and approval record
14. AI-use disclosure text

Items 3-14 are the **audit pack**. An output without an audit pack is not a SWOS
output.

---

## Non-goals

SWOS is deliberately **not**:

* an unconstrained prose stylist that improves fluency without semantic verification - `swos-prose` is the bounded, fail-closed editing layer;
* a single giant prompt with the architecture hidden in prose;
* a vendor-bound product - no host, model, retriever or store is mandatory;
* an autonomous publisher - human accountability for final judgement is a
  principle, not a setting.

---

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md), [`GOVERNANCE.md`](GOVERNANCE.md) and
[`SECURITY.md`](SECURITY.md) first. Discipline packs and evaluation fixtures are
the highest-value contributions; both have templates and a mandatory review
checklist. All commits require a DCO sign-off.

## Licence

MIT for code, schemas, contracts and specifications. Data and third-party
material are licensed separately - see the licence boundary notice in
[`LICENSE`](LICENSE).
