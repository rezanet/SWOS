# Claude Code Adapter

Claude Code implements the Agent Skills open standard and adds host extensions.
Those extensions are useful and **must not leak into SWOS core skills**.

## Install

```bash
cp -r skills/swos-core skills/swos-research-planner \
      skills/swos-citation-auditor skills/swos-reviewer \
      ~/.claude/skills/
python3 adapters/claude-code/apply_overlay.py --target ~/.claude/skills/
```

`apply_overlay.py` merges `overlay.yaml` into the installed copies. It never
modifies the repository originals.

## Host extensions isolated here

| Extension | SWOS use |
|---|---|
| `disable-model-invocation` | Set on `swos-reviewer` so review is user-initiated, not auto-triggered mid-draft |
| `user-invocable` | `/swos-citation-auditor` as an explicit command |
| `context: fork` / `agent` | Runs the hostile reviewer in a forked context - the mechanism for **blind review** |
| `allowed-tools` / `disallowed-tools` | Binds the agent contract tool lists to host tools |
| Hooks | Emits EPG activity records on tool call and skill activation |
| Path globs | Auto-suggests `swos-citation-auditor` on files with reference sections |
| Model / effort overrides | Higher effort for argument construction, lower for formatting |
| Live change detection | Reloads discipline packs during development |

## Why this matters

Outside Claude Code, only the six specification fields are accepted. Custom keys
such as `argument-hint`, `paths`, `hooks`, `context`, `agent`,
`disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`,
`effort` and `background` cause a hard validation error where the specification is
enforced:

```
Unexpected key(s) in SKILL.md frontmatter: argument-hint.
Allowed properties are: allowed-tools, compatibility, description, license, metadata, name.
```

Overlay, do not embed.

## Blind review binding

```yaml
swos-reviewer:
  context: fork
  agent: hostile-reviewer
  disable-model-invocation: true
```

Forking gives the hostile reviewer a context without the prior draft rationale.
This is the host mechanism that satisfies the `blind_review` field in
`reviewer-finding.schema.json`.
