# Interface Model

What crosses each boundary, and what must not.

## Boundary 1: Host to SWOS

**Crosses in:** work request, discipline, output type, audience, constraints,
data sensitivity, source constraints.
**Crosses out:** output bundle, gate results, escalations.
**Must not cross in:** host-specific frontmatter, host vocabulary, host approval
semantics. Adapters translate these.

## Boundary 2: Contract to Orchestration

**Crosses:** the workflow contract, agent handoff rules, abstention rules.
**Must not cross:** anything the orchestration layer could determine
deterministically. If the orchestrator can compute it, the contract must not
assert it.

## Boundary 3: Orchestration to Agents

**Crosses in:** the artefacts named in the agent's `inputs`, and nothing else.
**Crosses out:** the artefacts named in `outputs`, plus SDL entries for every
decision made and an EPG `AgentAction`.
**Must not cross:** artefacts outside the declared scope. This is enforced, not
trusted.

## Boundary 4: Tools to Evidence Layer

**Crosses:** typed results, EPG activities with complete parameters, rights
metadata, retraction status.
**Must not cross - and this is the security boundary:** instructions. Retrieved
content is **data**. It enters the Evidence Matrix and the EPG. It never enters
the Master Prompt Contract, an agent contract, a tool permission set or a
governance policy. Instruction-shaped content is logged as
`security.injection_attempt`, preserved verbatim as evidence, and executed never.

## Boundary 5: Evidence Layer to Drafting

**Crosses:** verified Evidence Matrix rows and approved Argument Graph nodes.
**Must not cross:** unverified rows, `context_only`-only claims presented as
supported, or any claim absent from the matrix. **A sentence that needs support
not in the matrix does not get written.**

This is the single most important interface in SWOS. Rule #3 is the state-machine
enforcement of it.

## Boundary 6: Everything to Memory

**Crosses:** approved, source-grounded lessons with EPG support, an SDL rationale,
an owner, a confidence and an expiry.
**Must not cross:** raw sensitive content, restricted-class content, prompts,
responses, secrets, customer content, runtime payloads, unsupported reflections.

## Boundary 7: SWOS to Release

**Crosses:** the output bundle - manuscript plus thirteen audit-pack artefacts.
**Gate:** every required evaluation plane passing, provenance completeness of 1.0,
zero open blocker findings, recorded approvals, complete audit pack.
**Must not cross:** a bare document. An output without an audit pack is not a SWOS
output.

## Interface stability

Boundaries 4, 5, 6 and 7 are **frozen at v1.0.0**. Changing what crosses them
requires an ADR and a major version. Boundaries 1, 2 and 3 may evolve in minor
versions provided the frozen schemas are unaffected.
