# swos-core execution-stage resources

These files are loaded **only when the task requires them**, per the Agent Skills
progressive-disclosure model. Do not inline them into `SKILL.md`.

| Resource | Load when |
|---|---|
| `master-prompt-contract.md` | Always, at Stage 1 |
| `knowledge-and-reasoning-spec.md` | At Stage 4, before typing any claim |
| `discipline-packs/<discipline>.md` | At Stage 1, once discipline is resolved |
| `schemas/*.json` | At Stage 4 and Stage 5, when constructing artefacts |

In a packaged distribution these are symlinks or copies of the repository
originals: `contracts/master-prompt-contract/MASTER-PROMPT-CONTRACT.md`,
`docs/knowledge-and-reasoning-spec.md`, `discipline-packs/` and `schemas/`.
Packaging is performed by `adapters/agent-skills/package_skill.py`.
