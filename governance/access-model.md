# Access Model

## Principals

| Principal | Description |
|---|---|
| Human author | Accountable for the final output |
| Human approver | Accountable for a release or an override; must not be the author for restricted work |
| Specialist agent | A bounded role with a declared tool and artefact scope |
| Orchestrator | May transition state; may not make scholarly judgements |
| Tool | Acts within a declared maximum data classification and egress list |
| Governance officer | May block; may not approve its own block |

## Rules

1. **Least artefact.** An agent reads only its contract's `inputs` and writes only
   its `outputs`. Enforced by the orchestrator, not by convention.
2. **Least tool.** An agent calls only tools in its `tools` list. Tool sets are
   static per agent per run; no tool grants tools.
3. **Classification ceiling.** A tool never receives content above its declared
   `max_data_classification`. Checked before the call.
4. **Separation of duties.** No agent approves its own output. No human is both
   author and approver on restricted work. The contract owner and evaluation owner
   are different people.
5. **Egress control.** Content classified `confidential` or above passes only to
   tools with an empty egress list or an explicitly approved allow-list entry.
6. **Read-down, write-up prohibited.** A `public` work may not write into a
   `restricted` memory scope, and a `restricted` work's content may not be written
   into memory readable by a `public` work.

## Enforcement point

The policy engine evaluates access **before** the call, not after. Post-hoc
detection of an unauthorised egress is an incident, not a control.
