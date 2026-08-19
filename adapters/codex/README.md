# OpenAI Codex / ChatGPT Adapter

Skills build on the open Agent Skills standard: a directory with `SKILL.md` plus
optional `scripts/`, `references/` and `assets/`, and an optional
`agents/openai.yaml` carrying UI metadata, invocation policy and tool
dependencies. Skills are the authoring format; plugins are the distribution
surface across ChatGPT web, desktop and mobile, the Codex CLI and IDE extensions.

## Install

```
.agents/
  skills/
    swos-core/
      SKILL.md
      agents/openai.yaml
      references/
```

Discovery scopes: REPO, USER, ADMIN, SYSTEM. SWOS is normally installed at REPO
scope for a research project, or ADMIN scope for an organisation-wide standard.

## Context budget

The host allocates roughly 2% of the context window to skill listing, or 8,000
characters when the window size is unknown. Four SWOS skills at ~100 tokens of
`description` each fit comfortably. **Do not add more core skills to work around a
description that fails to trigger** - fix the description.

## Invocation policy

```yaml
# agents/openai.yaml - swos-reviewer
allow_implicit_invocation: false
```

Review is deliberate. Implicit invocation of a reviewer mid-draft produces
review theatre: the panel runs before the evidence work is complete and passes
work it should have blocked.

For `swos-core`, implicit invocation is appropriate - the skill's whole purpose is
to intercept a writing request before drafting starts.
