# SWOS Skills

Four portable skill packages, authored to the **Agent Skills open specification**.

| Skill | Activates when |
|---|---|
| `swos-core` | Any governed scholarly or enterprise writing work |
| `swos-research-planner` | Planning a research programme before any evidence work |
| `swos-citation-auditor` | Verifying citations, detecting fabrication and laundering |
| `swos-reviewer` | Running the bounded, role-based reviewer panel |

## The six-field rule

Every `SKILL.md` in this directory uses **only** `name`, `description`,
`license`, `compatibility`, `metadata` and `allowed-tools`. Host-specific
frontmatter lives in `adapters/`, never here. `make lint-skills` enforces this,
and CI fails the build on violation.

This is not pedantry. Host-specific keys cause hard validation errors when the
same skill is uploaded to a spec-enforcing surface, which is precisely the
portability failure SWOS is designed to avoid.

## Progressive disclosure

Each skill is budgeted for three-stage loading: `name` + `description` at
discovery (~100 tokens), the `SKILL.md` body at activation (under 5,000 tokens),
and `references/` only when the task actually needs them.

The Master Prompt Contract, Knowledge & Reasoning Specification, discipline packs
and reviewer packs are **execution-stage resources**. They are linked from
`SKILL.md`, never inlined.
