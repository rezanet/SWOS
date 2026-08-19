---
contract: swos-host-adapter-contract
version: 1.0.0
status: frozen
---

# SWOS Host Adapter Contract

SWOS is host-agnostic, model-agnostic and retrieval-agnostic. Adapters are
**thin**: they translate, they never decide.

## The core constraint: six frontmatter fields

Core skills in `skills/` may use **only** the fields the Agent Skills open
specification defines:

```yaml
name:           # required, max 64 chars, lowercase/numbers/hyphens, must match directory name
description:    # required, max 1024 chars
license:        # optional
compatibility:  # optional, max 500 chars
metadata:       # optional
allowed-tools:  # optional (experimental in the spec)
```

Everything else is a **host extension**. Using a host extension where the
specification is enforced - skill uploads, packaging APIs, spec validators -
produces a hard error of the form:

```
Unexpected key(s) in SKILL.md frontmatter: argument-hint.
Allowed properties are: allowed-tools, compatibility, description, license, metadata, name.
```

`tools/lint_skills.py` enforces this in CI. A pull request adding
`argument-hint`, `paths`, `hooks`, `context`, `agent`,
`disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`,
`effort` or `background` to a core skill is rejected.

## Progressive disclosure budget

Agent Skills load in three stages. SWOS skills are budgeted accordingly:

| Stage | Loaded | SWOS budget |
|---|---|---|
| Discovery | `name` + `description` | ~100 tokens per skill, at startup |
| Activation | Full `SKILL.md` body | Under 5,000 tokens |
| Execution | `scripts/`, `references/`, `assets/` | On demand only |

The Master Prompt Contract, Knowledge & Reasoning Specification and discipline
packs are **execution-stage resources**. They are referenced from `SKILL.md`, not
inlined into it.

## What an adapter may do

1. Translate SWOS artefacts into host-native packaging.
2. Bind SWOS tool classes to host-available tools.
3. Map host approval mechanisms onto SWOS governance gates.
4. Supply host-specific frontmatter in an **overlay file**, never in the core skill.
5. Declare which SWOS capabilities are unavailable on this host.

## What an adapter may NOT do

1. Change any schema.
2. Relax any of the seven rules.
3. Skip a governance gate because the host lacks a mechanism. If the host cannot
   enforce a gate, the adapter must declare the capability **unsupported** and the
   deployment is limited to work classes that do not require it.
4. Introduce host-specific vocabulary into `contracts/` or `schemas/`.
5. Persist memory outside the memory governance contract.

## Host behaviour that must stay in the adapter

| Host | Isolate in adapter |
|---|---|
| Claude Code | Invocation control (`disable-model-invocation`, `user-invocable`), subagent execution (`context: fork`, `agent`), dynamic context injection, `allowed-tools`/`disallowed-tools` extensions, hooks, path globs, model and effort overrides, live change detection |
| OpenAI Codex / ChatGPT | `.agents/skills` discovery across REPO/USER/ADMIN/SYSTEM scopes, `agents/openai.yaml` (interface, policy, dependencies), skill installer, plugin distribution, the skill-listing context budget (2% of the context window, or 8,000 characters when unknown) |
| Microsoft Agent Framework | `AgentSkillsProvider` / `SkillsProvider`, inline and class skills, MCP skill aggregation, caching and filtering skill sources, subprocess script runners, tool approval middleware and auto-approval rules |
| MCP | Resources, prompts and tools; hosts, clients and servers; capability negotiation; logging; security and trust framing |
| CLI / CI | Exit codes, artefact paths, non-interactive approval routing |
| IDE agents | Workspace scoping, file-watch triggers, editor context injection |

## Capability declaration

Every adapter ships `capability-matrix.json` declaring which SWOS capabilities the
host supports:

```
{
  "adapter": "claude-code",
  "swos_version": "1.0.0",
  "capabilities": {
    "progressive_disclosure": "full",
    "script_execution": "sandboxed_with_approval",
    "tool_approval_gate": "native",
    "persistent_memory": "external_required",
    "state_store": "external_required",
    "provenance_store": "external_required"
  },
  "unsupported": [],
  "work_classes_permitted": ["public", "internal"]
}
```

Where a capability is `external_required`, the adapter names the external service
binding. Where a capability is `unsupported`, `work_classes_permitted` must
exclude every class that depends on it. An adapter that cannot persist provenance
cannot be used for work requiring an audit pack - and must say so, in the matrix,
rather than degrade quietly.
