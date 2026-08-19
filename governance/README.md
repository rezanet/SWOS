# Governance Control Plane

**Governance controls that exist only as documentation are governance theatre.**
Every control here is expressed as a policy file the policy engine evaluates and a
Governance Gate record the audit pack carries.

| Artefact | Purpose |
|---|---|
| [`policy-model.md`](policy-model.md) | How policies are structured, evaluated and versioned |
| [`data-classification.md`](data-classification.md) | Four classes and what each permits |
| [`access-model.md`](access-model.md) | Who and what may read, write and export |
| [`source-rights-policy.md`](source-rights-policy.md) | Licence and rights gate before store or export |
| [`approval-matrix.md`](approval-matrix.md) | When a human must approve |
| [`audit-model.md`](audit-model.md) | What is recorded, and what is deliberately not |
| [`retention-and-deletion.md`](retention-and-deletion.md) | Lifecycle of stored artefacts |
| [`incident-and-correction.md`](incident-and-correction.md) | Retractions, false claims, contamination, override |
| [`risk-register.md`](risk-register.md) | Eight named risks with controls |
| [`nist-ai-rmf-crosswalk.md`](nist-ai-rmf-crosswalk.md) | Govern / Map / Measure / Manage audit map |
| [`policies/`](policies/) | Policy-as-code, machine-evaluated |

## The six controls that had to be mechanised

Named in the plans, previously not enforceable. All six now evaluate as policy:

1. **Source-rights and licence gate** before storing or exporting evidence
2. **Memory write approval** for anything above episodic scratch
3. **Human approval thresholds** for high-risk interpretations and regulated outputs
4. **Provenance completeness check** before release - every claim links to an EPG node
5. **Release gate** enforcing evaluation harness pass/fail, in CI
6. **Incident and correction workflow** for retractions, false claims, bad citations,
   memory contamination and reviewer override

## Standards baseline

NIST AI RMF 1.0 is the governance baseline. Its Core organises into four
functions - **Govern, Map, Measure and Manage** - with Govern designed as a
cross-cutting function infused throughout the other three. SWOS adopts that
framing directly and uses the category numbering as an audit map. See the
crosswalk.
