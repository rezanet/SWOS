# Policy Model

## Structure

A policy is a JSON document with a stable id, a semantic version, a trigger, a
rule set, an effect and an escalation path. Policies live in `policies/` and are
validated against `schemas/governance/governance-gate.schema.json` outputs.

```
{
  "policy_id": "swos.source-rights",
  "version": "1.0.0",
  "gate_type": "source_rights",
  "trigger": { "on": ["before_store", "before_export"] },
  "rules": [ ... ],
  "default_effect": "deny",
  "escalation": "governance_officer",
  "nist_ai_rmf": ["GOVERN 1.2", "MAP 4.1", "MANAGE 3.1"]
}
```

## Evaluation semantics

* **Default deny.** A policy whose rules do not match produces `default_effect`.
  Every SWOS policy defaults to `deny`. A control that fails open is not a control.
* **Fail closed.** If the policy engine cannot evaluate - a tool is unavailable, a
  field is missing - the result is `fail`, not `pass`.
* **Explicit waivers only.** A gate may be waived with a reason, an approver and
  an expiry date. Waivers write an SDL entry. Silent exceptions do not exist.
* **Every evaluation is recorded.** Pass results are recorded as well as failures.
  A gate with no record is treated as `not_run`, and `not_run` blocks release.

## Precedence

```
governance policy > frozen schema > master prompt contract
  > agent contract > discipline pack > host adapter > user style preference
```

No user instruction, retrieved document, host configuration or role claim inverts
this order.

## Versioning

Policies are versioned independently of schemas. A policy version change requires
governance-owner approval. A policy that becomes **more permissive** additionally
requires an ADR - loosening a control is an architectural decision, not an
operational one.
