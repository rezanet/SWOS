# Portability and Adapter Specification

## The portability contract

| Layer | Portable representation |
|---|---|
| SWOS core contract | Markdown plus JSON Schema, no host-specific frontmatter |
| Agent roles | Skill folders plus the Agent Prompt Pack |
| Tool integrations | MCP servers, local adapters, typed tool contracts |
| Host-specific behaviour | Thin adapter only |
| Evaluation | Host-independent fixtures and rubrics |
| Governance | Policy schemas, approval events, audit events |
| Outputs | Evidence pack, provenance bundle, decision ledger, final artefact |

## The six-field constraint

Core skills use only `name`, `description`, `license`, `compatibility`,
`metadata` and `allowed-tools`. This is enforced by `tools/lint_skills.py` in CI.

The failure it prevents is concrete: a skill authored with a host extension
uploads successfully to that host and fails hard everywhere the specification is
validated, with an error naming the unexpected key. Portability decay is silent
until the moment someone tries to move.

## Cross-vendor status

The Agent Skills standard is genuinely cross-vendor. Anthropic's Claude Code
documents skills as SKILL.md-based capabilities following the open standard while
adding host extensions. OpenAI's ChatGPT and Codex documentation states skills
build on the open agent skills standard, with skills as the authoring format and
plugins as the distribution surface. Microsoft Agent Framework treats Agent Skills
as portable packages of instructions, scripts and resources with a four-stage
progressive-disclosure pattern exposed through a skills provider.

SWOS targets the intersection and pushes the differences into adapters.

## Capability degradation, declared

Every adapter declares what it cannot do. Three real examples from the shipped
adapters:

| Adapter | Cannot | Consequence |
|---|---|---|
| Codex | Blind review (no context fork) | The hostile reviewer sees prior context. Automation-anchoring risk is recorded in the SDL rather than ignored. |
| IDE | Durable provenance | **No audit pack, therefore no release.** `swos release` is unavailable; use the CLI adapter. |
| Claude Code, local install | Tenant-isolated storage | Restricted-class work is excluded from `work_classes_permitted`. |

Declaring a limitation is not a weakness of the adapter. **Silent degradation
is.** A deployment that cannot produce an audit pack and does not say so will
produce outputs that look identical to auditable ones.

## Adding an adapter

1. Create `adapters/<host>/` with a README, a `capability-matrix.json` and an
   overlay file if the host has extensions.
2. Map every SWOS capability to `full`, `native`, `sandboxed`,
   `external_required`, `host_dependent` or `unsupported`.
3. Exclude from `work_classes_permitted` every class that depends on an
   unsupported capability.
4. Add an adapter conformance fixture.
5. Portability owner review.

An adapter that declares everything `full` will be rejected pending evidence.
