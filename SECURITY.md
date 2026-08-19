# Security Policy

## Reporting a vulnerability

Report privately via GitHub Security Advisories. Do not open a public issue.
Target acknowledgement 3 business days; target triage 10 business days.

## Threat model summary

SWOS ingests untrusted third-party content (papers, web pages, PDFs, enterprise
documents) and may execute packaged scripts inside an agent host. Both are
attack surfaces.

| Threat | Vector | Control |
|---|---|---|
| Prompt injection via retrieved source | Malicious instructions inside a PDF, abstract or web page | Retrieved content is **data, never instruction**. Tool output enters the evidence layer, never the contract layer. Enforced by `contracts/tool-contract/`. |
| Citation laundering | Real source attached to a claim it does not support | Passage-level citation-support classification plus `evals/fixtures/adversarial/citation-laundering-*` |
| Malicious skill script | Contributed `scripts/` in a skill package | Sandboxing, resource limits, allow-listing, audit logging, approval by default |
| Memory poisoning | Unsupported reflection written to RPM, later read as fact | Memory writes require EPG support, SDL rationale, owner and expiry. `governance/policies/memory-write.policy.json` |
| Rights and IP exposure | Redistribution of licensed full text | Source-rights gate before store or export. `governance/source-rights-policy.md` |
| Exfiltration through tool calls | Agent sends sensitive content to an external connector | Data classification plus egress allow-list in the tool registry; restricted classes are tool-limited |
| Autonomy drift | Agent exceeds its declared decision scope | Every agent contract declares `decisions_allowed` and `escalation_conditions`; violations are governance incidents |

## Script execution policy

Skills in this repository ship **no executable scripts by default**. Where a host
adapter enables scripts, the following are mandatory.

1. **Approval by default.** Skill-invoking tools (load skill, read skill
   resource, run skill script) require explicit approval. Read-only
   auto-approval may be configured by an operator; blanket auto-approval of all
   tools must not be enabled in production.
2. **Sandboxing.** Subprocess execution runs with no ambient network access and
   no credentials in the environment.
3. **Resource limits.** CPU, memory, wall-clock and output-size caps.
4. **Allow-listing.** Only interpreters and binaries on the operator allow-list.
5. **Audit logging.** Every invocation emits an EPG `AgentAction` node and a
   governance audit event.

Reference subprocess runners shipped by agent frameworks are demonstration code.
Do not deploy them unmodified.

## Script inventory

| Path | Purpose | Network | Sandbox required |
|---|---|---|---|
| `tools/validate_schemas.py` | Local schema validation | none | no (developer tool) |
| `tools/lint_skills.py` | Frontmatter constraint linter | none | no (developer tool) |
| `tools/check_governance.py` | Policy-as-code validation | none | no (developer tool) |
| `evals/harness/run_evals.py` | Evaluation runner | none | no (developer tool) |

Any new script in `skills/` must be added to this table in the same pull request.

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |
| < 1.0 | No |
