# Agent Skills Adapter (reference)

The baseline. Every other adapter is this plus an overlay.

## Skill layout

```
swos-core/
  SKILL.md          # required; six frontmatter fields only
  references/       # execution-stage resources
  scripts/          # none shipped by default (see SECURITY.md)
  assets/           # none shipped by default
```

## Permitted frontmatter

```yaml
name:           # required, max 64 chars, [a-z0-9-], must equal directory name
description:    # required, max 1024 chars
license:        # optional
compatibility:  # optional, max 500 chars
metadata:       # optional
allowed-tools:  # optional (experimental in the spec)
```

Nothing else. `tools/lint_skills.py` enforces it.

## Writing the description field

The `description` is the **only** thing an agent sees at discovery time, at
roughly 100 tokens per skill. It decides whether the skill is loaded at all. It
must therefore state what the skill does *and the situations that should trigger
it*, in the user's vocabulary - not the architecture's.

Good: "...checking a manuscript for citation integrity, validating a reference
list, before submitting or publishing anything with references..."

Bad: "Implements Rule #5 of the SWOS master contract." True, and it will never
trigger.

## Packaging

```bash
python3 adapters/agent-skills/package_skill.py --skill swos-core --out dist/
```

Resolves `references/` from repository originals, validates frontmatter against
the six-field constraint, checks the activation-stage token budget, and emits a
distributable directory.

## Install

Copy the skill directory into the host's skills location. Discovery is by
directory name, which must equal the `name` field.
