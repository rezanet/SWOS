# SWOS 100% Completion Baseline Report

**Baseline date:** 2026-08-22  
**Repository:** `rezanet/SWOS`  
**Baseline branch:** `programme/swos-100-completion-baseline`  
**Canonical main SHA inspected:** `eb704e4baec57124a6d54065ff99ea3d5128c35c`  
**Platform specification version:** `1.0.0`  
**Released SWOS Prose version:** `0.2.0`

## 1. Executive Summary

SWOS is not a conventional web application. It is a **host-agnostic, model-agnostic, retrieval-agnostic scholarly reasoning platform** whose product surface is primarily contracts, schemas, governance controls, evaluation planes, adapters, portable skills, audit artefacts, and Python execution code for SWOS Prose.

The repository already has a substantial and unusually mature **specification/governance layer**. The v1.0.0 platform release is explicitly a **Specification Lock**, not the end-state implementation. The repository's own roadmap defines the remaining product programme:

1. **v1.1 — Reference Implementation**: orchestrator/state store, EPG/SDL/RPM stores with hash chaining, cross-encoder reranker, scholarly-index corpus adapters, end-to-end CLI, evaluation harness bound to a real system under test.
2. **v2.0 — Research Grade**: production RPM, formal discipline ontologies, trained citation-support classifier, measured source-diversity controls, deeper method critique, PROV round-trip certification, justified art-history/art-criticism agents, multimodal reasoning.
3. **v3.0 — Product Grade**: enterprise identity, RBAC/ABAC, tenant isolation, observability/drift monitoring, incident automation, compliance reporting, cost controls and service management.

Separately, **SWOS Prose v0.2.0** is a released semantic-safe post-draft editing layer implementing `mode=polish`. It is substantially implemented and empirically benchmarked, but the current Self-Healing/repair-loop milestone is still under review in PR #36 and must not be treated as merged or complete.

The generic "backend/frontend/database" completion template does not map literally to this repository. For SWOS, completion must follow the repository's contract-first architecture and roadmap rather than manufacture a browser frontend, CRUD API, database, authentication flow, or deployment topology that the current specification does not require. Product-grade identity and tenancy belong to v3.0 because the repository explicitly sequences them there.

## 2. Evidence Basis and Inspection Method

The baseline was derived from the repository itself, including:

- `README.md`
- `SWOS-Solution-Architecture.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `GOVERNANCE.md`
- `SECURITY.md`
- `LICENSE`
- `VERSION`
- `Makefile`
- `pyproject.toml`
- `docs/roadmap.md`
- repository tree and current GitHub metadata
- all discoverable open and closed GitHub Issues
- all discoverable pull requests through PR #36
- current PR #36 review threads
- `.github/workflows/swos-ci.yml`
- current SWOS Prose tests and benchmark structure.

A direct `git clone` was attempted in the inspection runtime, but that runtime could not resolve `github.com` via DNS. This is an inspection-environment network limitation, not evidence of a repository defect. Repository state and CI were therefore inspected through the authenticated GitHub integration. A truly clean local installation/build execution should be repeated in a normal networked environment during the environment/CI milestone.

## 3. What SWOS Is

SWOS describes itself as a **governed research institute in software form**. Its optimisation target is trustworthy scholarly reasoning rather than fluent text. Its constitutional controls include:

1. no giant prompt;
2. deterministic/persistent/measurable controls live outside prompts;
3. no drafting before plan, Evidence Matrix, Argument Graph, provenance graph and decision ledger exist;
4. every factual claim is supported, marked uncertain or removed;
5. every citation is checked for existence, metadata and claim support;
6. every scholarly decision is traceable;
7. every final output is auditable.

The first-class architecture includes the Evidence Matrix, Argument Graph, Evidence Provenance Graph (EPG), Scholarly Decision Ledger (SDL), Research Program Memory (RPM), Knowledge & Reasoning Specification, reviewer system, eight-plane evaluation harness and governance control plane.

The key architectural separation is intentional:

- Evidence Matrix: **what supports this claim?**
- Argument Graph: **how does the argument hold together?**
- EPG: **where did this come from and how was it produced?**
- SDL: **why was this judgement made?**
- RPM: **what has this research programme already settled?**

## 4. Technology and Repository Stack

### 4.1 Current executable stack

- **Primary implementation language:** Python.
- **Supported Python:** `>=3.11` for the packaged SWOS Prose surface.
- **Package/build:** `setuptools` via `pyproject.toml`.
- **Released Python package:** `swos-prose` version `0.2.0`.
- **Primary external SDK dependency:** `openai>=1.70.0`.
- **CLI entry point:** `swos-prose = swos_prose.cli:main`.
- **Unit-test framework:** Python `unittest` for SWOS Prose.
- **Schema validation:** JSON Schema tooling plus repository validators.
- **CI/CD:** GitHub Actions.
- **Build/task entry point:** `Makefile` plus Python CLIs.
- **Evaluation:** repository-owned eight-plane harness.

### 4.2 Current architecture artefacts

- JSON Schemas under `schemas/`, frozen at platform v1.0.0.
- Contracts under `contracts/`.
- Policy-as-code under `governance/`.
- Agent Skills under `skills/` with a six-field frontmatter constraint.
- Host adapters for Agent Skills, Claude Code, Codex, MCP, CLI and IDE environments.
- Discipline packs and reviewer packs.
- Worked audit-pack example and release provenance.
- SWOS Prose benchmark, frozen v0.2 evidence and active development benchmark work.

### 4.3 What is **not** currently a first-class stack component

No repository evidence requires a conventional browser frontend, REST/GraphQL application backend, ORM, relational database, registration/login/password-reset flow, or web-session layer at the current release stage. Those should not be invented to satisfy a generic checklist. Persistent reference stores are explicitly a v1.1 roadmap item; enterprise identity and tenant isolation are explicitly v3.0 items.

## 5. Current Feature / Capability Baseline

### 5.1 Working / released

| Capability | Status | Evidence / notes |
|---|---|---|
| Contract-first architecture | Released | v1.0.0 Specification Lock |
| Frozen core schemas | Released | Nine platform schemas; schema-change governance applies |
| Knowledge & Reasoning Specification | Released | Standalone governed specification |
| Governance policy-as-code | Released | Release, source-rights, memory, approvals, provenance, classification and incident controls |
| Eight-plane evaluation harness | Released | Retrieval, grounding, citation, scholarly, governance, regression, memory contamination, adversarial |
| Host portability model | Released | Six adapters, capability matrices, Agent Skills constraint |
| Discipline and reviewer packs | Released | Governed packs with acceptance criteria |
| Worked audit-pack example | Released | Schema-valid release example |
| SWOS Prose deterministic semantic delta layer | Released | Protected anchors and semantic-risk checks |
| Bidirectional semantic verifier contract | Released | Proposition preservation/licensing contract |
| OpenAI semantic-verifier adapter | Released | Responses API integration and structured output |
| SWOS Prose `polish` generation | Released | One proposal followed by fail-closed verification |
| Diagnostics / safe abstention | Released | Tiny reviewed whole-sentence fast path; zero provider calls on abstention |
| SWOS Prose CLI and package | Released | v0.2.0 installable package and `swos-prose` command |
| Dogfood and live evidence workflow | Released | Secret-gated Luna live evidence and five-case dogfood |
| Frozen v0.2 benchmark | Released/frozen | 50 cases; 0 unsafe material-change PASS; 0 unsafe abstention; 3.04% measured token saving |

### 5.2 Partial / in progress

| Capability | Status | Current gap |
|---|---|---|
| Self-Healing Engine / bounded repair | **PR #36 open** | Current head `8ebe11361848d52697242d9058091743d1dd8eef`; three new P2 Codex findings remain unresolved |
| Semantic verifier stability | Open issue #32 | Equivalent paraphrase outcomes remain stochastic; must improve without weakening fail-closed safety |
| Lexical/scope semantic hardening | Open issues #4, #5, #6, #7, #12, #13, #14, #16 | Specific known semantic attack surfaces remain |
| Contributor templates | PR #17 open | Old base and currently unmerged; should be reconciled rather than blindly merged |
| Reference execution system | Roadmap v1.1 | Specification exists; reference orchestrator/store/retrieval pipeline is not yet complete |

### 5.3 Missing according to the authoritative roadmap

#### v1.1 Reference Implementation

- reference orchestrator and state store;
- concrete EPG, SDL and RPM stores with hash chaining;
- cross-encoder reranker reference implementation;
- corpus adapters for open scholarly indexes;
- working end-to-end SWOS CLI beyond the standalone Prose component;
- evaluation harness bound to an actual system under test rather than contract-mode fixtures.

#### v2.0 Research Grade

- production RPM across projects;
- formal discipline ontologies beyond rubric packs;
- trained citation-support classifier;
- measured source-diversity controls;
- deeper discipline-specific method critique;
- full PROV round-trip certification;
- image/object-analysis tooling and justified art-history/art-criticism agent promotion;
- multimodal scholarly reasoning.

#### v3.0 Product Grade

- enterprise identity;
- RBAC/ABAC;
- tenant isolation;
- observability dashboards and drift monitoring;
- incident workflow automation;
- compliance reporting;
- cost controls and service management.

## 6. GitHub Issues and Pull Requests

### 6.1 Open issues at baseline

The active issue set identifies nine substantive known work items:

- **#4** lexical negation beyond explicit `not`/`never`;
- **#5** attribution-force drift;
- **#6** quantifier binding and modal scope;
- **#7** relation direction / causal-role reversal;
- **#12** causal explanations added during polish;
- **#13** referential hallucination from read-only context;
- **#14** qualification deletion during compression;
- **#16** citation-attachment broadening during reordering;
- **#32** semantic-verifier stability on equivalent paraphrases.

These are not cosmetic backlog items. Most are explicit semantic-safety or verifier-quality boundaries and must be incorporated into the completion programme.

### 6.2 Closed issues already incorporated

Closed work includes diagnostics abstention (#15), GPT-5.6 temperature compatibility (#19), degree/modal-force preservation (#21), reviewed lexical-negation equivalence (#24), denial-scope causal handling (#25), terminal-line-ending no-change handling (#26), and attributed relation-frame alignment (#30).

### 6.3 Open PRs

**PR #17 — Add contributor issue and pull request templates**

- open and mergeable;
- based on an old main SHA;
- should be rebased/reconciled and independently reviewed before merge.

**PR #36 — M1: Self-Healing Engine (Repair Loop)**

- open and mergeable;
- base: released SWOS Prose v0.2 main SHA `eb704e4...`;
- current head: `8ebe11361848d52697242d9058091743d1dd8eef`;
- expands the active development benchmark to 56 cases while preserving the frozen v0.2 evidence;
- first three Codex review findings were addressed and their threads resolved;
- **three later Codex P2 findings remain unresolved and therefore block milestone merge:**
  1. active 56-case reports still identify the benchmark as old `0.2.0-rc1`; the active M1 corpus needs its own benchmark version;
  2. `MODALITY_WEAKENED` is advertised as repairable but a helper currently makes that branch unreachable;
  3. repair-provider provenance notes (provider/model/prompt version/input hash/response ID) are not retained on each repair attempt/result.

PR #36 must remain unmerged until those findings are fixed, exact-head CI is green, and adversarial re-review signs off.

## 7. Testing and Quality Baseline

### 7.1 Existing automated gates

The main GitHub Actions workflow currently runs:

- strict schema/contract conformance;
- Agent Skills frontmatter portability check;
- SWOS Prose package install and CLI smoke test;
- full `tests/prose` unit/adversarial suite;
- secret-gated live OpenAI semantic-verifier regression and five-case dogfood;
- all eight evaluation planes;
- governance policy validation;
- DCO commit-range validation.

This is a strong domain-specific CI foundation.

### 7.2 Coverage

**Current numeric source-code coverage is not established by the repository CI inspected in this baseline.** No coverage collector or minimum coverage threshold is configured in `pyproject.toml`, the Makefile or the main CI workflow inspected.

Therefore the completion-plan requirement `>=80%` cannot currently be claimed. The appropriate SWOS adaptation is to measure and enforce coverage for executable Python components and critical policy/evaluation code. There is no current frontend codebase for which a separate frontend percentage would be meaningful.

### 7.3 Linting and formatting

The repository has a domain-specific Agent Skills linter, but a general Python static lint/format gate was not identified in the inspected main CI. This is a Milestone 1 environment/quality gap.

### 7.4 Test architecture observation

SWOS already contains extensive semantic and adversarial tests. Raw line coverage alone would be an insufficient quality measure. Completion should combine:

- source coverage threshold;
- semantic attack fixtures;
- release-plane gates;
- deterministic benchmark contracts;
- repeated live stability evidence where stochastic providers are involved;
- mutation testing where practical on critical deterministic gates.

## 8. CI/CD and Repository Governance Baseline

The workflow comments say release gates are enforced in CI and that degradation blocks merge. The jobs themselves are real and substantial.

However, GitHub metadata for `main` currently reports branch protection with **required status-check enforcement off and no required check contexts configured**. This creates a gap between repository governance intent and GitHub merge enforcement. A green workflow exists, but repository settings do not currently prove that a maintainer is mechanically prevented from merging while those checks are red or absent.

This must be investigated and corrected as part of the environment/CI milestone unless an external ruleset (not visible in the inspected branch metadata) is the actual enforcement authority.

Additional CI gaps relative to a production-grade completion target:

- no numeric code-coverage gate currently established;
- no general Python lint/format gate identified;
- no dependency vulnerability scan identified in the main workflow;
- no SAST/CodeQL/Semgrep gate identified in the main workflow;
- the live semantic-verifier regression step is intentionally `continue-on-error`, so it is evidence rather than a hard release gate; this should remain a deliberate policy choice and be documented as such.

## 9. Security Baseline

### Strengths

SWOS already has a mature written threat model covering:

- prompt injection in retrieved sources;
- citation laundering;
- malicious skill scripts;
- memory poisoning;
- rights/IP exposure;
- data exfiltration;
- agent autonomy drift.

The architecture includes fail-closed verification-tool requirements, data classification, egress controls, source-rights policy, memory-write governance, audit events and human approval thresholds.

### Gaps between specification and production implementation

The main risk is **specification-to-runtime distance**. Many security controls are strongly specified but the reference orchestrator, stores and retrieval/tool execution runtime are still v1.1 work. Production readiness requires proving those policies actually constrain an implementation.

Additional baseline gaps:

- dependency/SCA scanning is not currently visible in the main CI;
- SAST is not currently visible in the main CI;
- there is no network service yet, so a DAST requirement such as OWASP ZAP is presently not applicable; it becomes applicable only if/when a service surface is introduced;
- v3 identity/tenant security is intentionally not implemented yet;
- clean sandbox/egress enforcement for future executable host tooling must be validated in implementation, not merely documented.

No claim is made here that critical/high vulnerabilities are absent; the required scanners have not yet been run as a governed baseline campaign.

## 10. External Dependencies and Services

Current known external/runtime dependencies include:

- OpenAI SDK (`openai>=1.70.0`) for SWOS Prose live generation/verification;
- `OPENAI_API_KEY` for live evidence paths;
- GitHub Actions for CI evidence;
- host environments described by adapters: Agent Skills, Claude Code, Codex/OpenAI, MCP, CLI and IDE agents.

Missing by design at this stage:

- bundled scholarly retrieval corpus;
- reference adapters to open scholarly indexes;
- cross-encoder reranker implementation;
- concrete persistent EPG/SDL/RPM state stores.

Those are v1.1 deliverables, not accidental omissions from a web backend.

## 11. Environment / Setup Baseline

Current released SWOS Prose installation surface:

```bash
python3 -m pip install -e .
export OPENAI_API_KEY=...
swos-prose --help
python3 -m swos_prose.cli polish \
  --source "The analysis was performed using a t-test." \
  --assurance strict \
  --json
```

Repository checks currently expose:

```bash
make validate
make lint-skills
make eval
make test-prose
make benchmark-prose
make governance-check
make ci
```

The setup story is adequate for the specification/Prose layer but is not yet a v1.1 end-to-end SWOS runtime setup, because that runtime is precisely what the roadmap says remains to be built.

## 12. Known Bugs, Risks and Immediate Blockers

### Merge blocker: PR #36

The current Self-Healing Engine cannot be declared complete while the three unresolved Codex P2 findings listed in Section 6.3 remain open.

### Backlog semantic risks

Issues #4, #5, #6, #7, #12, #13, #14 and #16 define known semantic attack surfaces. Closing them must preserve the existing invariant: ambiguity becomes REVIEW/REJECT, never an optimistic PASS.

### Stability risk

Issue #32 is a quality/stability problem on intended-equivalent paraphrases. It must stay separate from semantic safety: improving stability must not weaken deterministic blockers.

### Governance enforcement risk

The current branch-protection metadata does not show required CI checks enforced at GitHub settings level.

### Evidence/versioning risk

The platform and Prose component correctly use separate version lines (`1.0.0` platform specification; `0.2.0` Prose), but active benchmark evidence must be independently versioned from frozen v0.2 evidence. This is already an unresolved PR #36 review finding.

## 13. Proposed SWOS-Native Scope for “100% Completion”

The completion programme should preserve the user's Milestone 0–9 reporting cadence, but reinterpret generic web-app assumptions through SWOS's actual architecture.

### Milestone 0 — Repository Discovery and Baseline

This report and `PROGRESS.md`. No product code changes.

### Milestone 1 — Environment, CI and Quality Baseline

- finish/reconcile existing open administrative PR #17;
- close PR #36 review blockers only through its own governed M1 workflow, not from the baseline branch;
- clean reproducible install/setup documentation;
- general Python lint/format configuration;
- source coverage measurement and threshold policy;
- dependency/SCA and SAST baseline;
- verify/repair GitHub required-check enforcement;
- explicit environment-variable documentation;
- preserve existing domain-specific gates.

### Milestone 2 — Core Reference Implementation (maps to roadmap v1.1)

- cross-encoder reranker first, per architecture sequencing;
- reference orchestrator and scholarly state machine;
- EPG/SDL/RPM hash-chained stores;
- corpus adapters to open scholarly indexes;
- end-to-end SWOS CLI;
- system-under-test binding for the eight-plane harness.

### Milestone 3 — Host/User Interaction Layer

There is no specified browser frontend to “complete”. This milestone should instead complete the supported host interaction surfaces and CLI/operator UX, with accessibility/usability requirements applied if a visual/web surface is introduced later. Do not create a frontend merely to satisfy a generic template.

### Milestone 4 — Feature Completion and Semantic Hardening

- resolve all current open semantic issues or explicitly record governed deferrals;
- complete the SWOS Prose roadmap only when prerequisite safety fixtures exist;
- integrate v1.1 reference components;
- full regression against frozen contracts/evidence.

### Milestone 5 — Security Hardening

- SCA/SAST and secret scanning;
- concrete prompt-injection/data-egress tests against the reference runtime;
- sandbox/resource-limit verification for executable integrations;
- state-store integrity/tamper tests;
- IDOR/session/JWT/DAST controls only if the product actually introduces those surfaces;
- security report with residual risk.

### Milestone 6 — Performance, Cost and Scalability

SWOS-native metrics should include retrieval/reranking latency, provider-call latency, token/cost budgets, state-store query cost, provenance growth, batch throughput and concurrency. Browser page-load targets are inapplicable unless a browser product is added.

### Milestone 7 — Testing and Quality Gates

- >=80% executable Python coverage as a floor, with higher thresholds for critical gates where justified;
- mutation testing on deterministic safety boundaries where feasible;
- repeated stochastic stability campaigns;
- performance budgets;
- zero flaky release-gate tests;
- preserve eight-plane release predicates.

### Milestone 8 — Documentation, Distribution and Deployment

- complete developer/operator/user documentation;
- reproducible clean-environment installation;
- container/package deployment only where useful to the actual runtime;
- architecture and data-store docs;
- release/migration guidance.

### Milestone 9 — Final Integration and Release

The release target must be tied to a named SWOS roadmap boundary rather than an arbitrary “v1.0.0” because platform v1.0.0 already exists. A future release version must be selected from the real completed scope, with green exact-head/main CI, provenance bundle, SDL release approval, changelog/release notes and a verified Git tag.

If “100%” means **the full currently declared repository roadmap**, then completion extends through the v3 Product Grade capabilities after v1.1 and v2 prerequisites are met. It is not honest to call the project 100% complete at the end of a generic web-app checklist while v1.1/v2/v3 roadmap components remain absent.

## 14. Baseline Definition of Done for the Completion Programme

A final completion claim must be evidence-backed. At minimum:

- all in-scope roadmap capabilities have executable implementations, not only specifications;
- all non-deferred open issues are closed with regression evidence;
- no unresolved review blockers exist;
- all required CI gates are mechanically enforced on protected release branches;
- source coverage threshold is measured and met;
- zero critical/high vulnerabilities remain after a recorded scan campaign;
- deterministic safety boundaries remain fail-closed;
- stochastic model quality is reported as distributions, not cherry-picked single runs;
- clean-environment installation and end-to-end operation are demonstrated;
- documentation and deployment/distribution surfaces match reality;
- release provenance, SDL approval, changelog and verified tag exist.

## 15. Project Health Assessment

| Area | Baseline assessment |
|---|---|
| Architecture/specification | **Strong** — unusually explicit and governed |
| Schemas/contracts | **Strong / frozen** |
| Governance design | **Strong**, but GitHub enforcement needs verification/hardening |
| Evaluation design | **Strong** — eight-plane domain-specific harness |
| SWOS Prose v0.2 | **Released and empirically benchmarked** |
| M1 repair engine | **Advanced but currently blocked in PR review** |
| Reference end-to-end SWOS runtime | **Incomplete (v1.1 work)** |
| Retrieval/reranking reference implementation | **Incomplete** |
| Research-grade capabilities | **Mostly future roadmap** |
| Product-grade enterprise runtime | **Future roadmap** |
| Numeric code coverage | **Unknown / not currently enforced** |
| General SCA/SAST baseline | **Not established in inspected CI** |
| Documentation | **Strong for architecture; incomplete for future runtime because runtime is not built** |

## 16. Completion Estimate

**Planning estimate: ~35% complete against the full declared v1.0 → v3.0 product roadmap.**

This is deliberately **not a quality score** and not a claim of mathematical precision. The specification/governance/evaluation foundation is much further along than 35%, and SWOS Prose is also advanced. The lower programme-level estimate reflects that the v1.1 reference runtime, most v2 research-grade capabilities and v3 product-grade capabilities are still explicitly future work.

Milestone 1 should replace this rough estimate with a component-weighted progress ledger derived directly from the roadmap and acceptance tests.

## 17. Milestone 0 Conclusion

The repository is healthy as a **specification-locked governed platform plus a released Prose subsystem**, but it is not yet the full production-grade SWOS described by its own roadmap.

The immediate engineering sequence is:

1. keep this baseline branch documentation-only;
2. finish PR #36 through its existing adversarial gate without bypassing the three open P2 findings;
3. reconcile stale PR #17;
4. establish enforceable CI/coverage/security/tooling baselines;
5. then begin v1.1 with the cross-encoder reranker and reference runtime in the repository-defined order.

No requirement for a conventional frontend/backend/database should override SWOS's own contract-first architecture or deliberately sequenced roadmap.
