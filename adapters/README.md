# Host Adapters

Adapters are **thin**. They translate, they never decide.

| Adapter | Host | Status |
|---|---|---|
| [`agent-skills/`](agent-skills/) | Any Agent Skills runtime | Reference |
| [`claude-code/`](claude-code/) | Claude Code | Full |
| [`codex/`](codex/) | OpenAI Codex / ChatGPT | Full |
| [`mcp/`](mcp/) | Any MCP-capable host | Optional integration |
| [`cli/`](cli/) | Terminal and CI | Full |
| [`ide/`](ide/) | IDE agents | Partial |

Rules are normative in
[`contracts/host-adapter-contract/`](../contracts/host-adapter-contract/):

* Core skills carry only the six specification frontmatter fields.
* Host-specific behaviour lives in an **overlay**, never in the core skill.
* An adapter may not relax a rule, skip a gate, or change a schema.
* Every adapter ships a `capability-matrix.json` declaring what the host supports
  and, critically, what it does **not**.
