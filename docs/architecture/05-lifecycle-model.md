# Lifecycle Model

The enterprise AI SDLC - Discover, Design, Build, Validate, Release, Operate,
Evolve, Retire - with governance as a cross-cutting overlay rather than a final
gate. This maps onto the NIST AI RMF functions, where Govern is infused
throughout Map, Measure and Manage.

| Phase | SWOS focus | Mandatory artefacts |
|---|---|---|
| **Discover** | Problem framing, use-case registration, evidence risk, source constraints | Intake record, risk pre-assessment, evidence standard, governance pre-check |
| **Design** | Architecture, prompt and tool boundaries, provenance and evaluation model | Solution blueprint, prompt contract, tool contract, K&R spec, threat model |
| **Build** | Orchestrator, tools, memory, knowledge structures, evaluation harness | Versioned contracts, test datasets, tool registry, schema pack |
| **Validate** | Retrieval, citation support, argument quality, security, governance | Evaluation report, red-team findings, release-readiness pack |
| **Release** | Freeze version, publish output contract, disclosure, runbook, support route | Release notes, model and prompt card, audit pack, backout plan |
| **Operate** | Monitor quality, safety, cost, drift, source changes, reviewer defects | Dashboards, incident register, periodic evaluation report |
| **Evolve** | Update ontologies, contracts, tools, memory rules, benchmarks | Change log, regression report, lessons learned |
| **Retire** | Decommission outputs, tools, memories or connectors safely | Retirement checklist, archived provenance, deletion evidence |

## Two lifecycles, not one

SWOS runs **two** lifecycles that are easily confused:

1. **The platform lifecycle** - the table above, governing SWOS itself as a
   product.
2. **The work lifecycle** - the Scholarly State Model, governing an individual
   manuscript or report from `initiated` to `retired`.

They share phase vocabulary and share governance checkpoints, but they move at
different speeds. A platform release may occur while fifty works are in flight;
a work may be retired while the platform is unchanged. The Scholarly State Model
records both: each state carries its `sdlc_phase` alongside its scholarly state.

See [`schemas/state/STATE-MODEL.md`](../../schemas/state/STATE-MODEL.md) for the
work lifecycle, including its transition preconditions.

## Runtime sequence within a work

1. Intake classifies the work - discipline, output type, audience, source
   constraints, risk, evidence standard.
2. Governance sets the boundary - access policy, data classification, licence
   constraints, retention rules, approval route.
3. The orchestrator creates the research plan - decomposes tasks, assigns agents,
   defines stop conditions.
4. Tools retrieve and parse sources. Search, citation traversal, full-text
   extraction, metadata validation and licence checks all run **before** drafting.
5. Counter-evidence search runs as a distinct step.
6. The Evidence Matrix is populated.
7. The EPG records the chain, as it happens.
8. The Argument Graph is built.
9. The SDL records choices.
10. The reviewer panel attacks the work in bounded loops.
11. The evaluation harness gates release.
12. The draft is produced - **only now**.
13. The output bundle is assembled.
14. The memory update is governed.

Steps 10 and 11 preceding step 12 is not an oversight. **Review and evaluation
apply to the evidence and the argument, not to the prose.** Drafting is a
rendering step.
