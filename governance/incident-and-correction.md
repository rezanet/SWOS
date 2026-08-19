# Incident and Correction Workflow

## Incident classes

| Class | Example | Severity |
|---|---|---|
| Retraction | A cited source is retracted after publication | High |
| False claim | A published claim is shown to be unsupported | High |
| Bad citation | Fabrication or laundering discovered post-release | High |
| Memory contamination | An unsupported item entered RPM and influenced output | High |
| Rights breach | Licensed content stored or exported without rights | Critical |
| Classification breach | Restricted content passed to an unapproved tool | Critical |
| Injection | Retrieved content attempted to alter behaviour | Medium unless successful |
| Autonomy drift | An agent acted outside its declared decision scope | High |
| Evaluation gaming | Scores improved without a corresponding quality improvement | Medium |

## Workflow

```
Detect -> Classify -> Contain -> Assess blast radius -> Correct -> Supersede
       -> Notify -> Record -> Learn
```

1. **Detect.** Automated: retraction watch, provenance completeness monitoring,
   regression deltas, contradiction detection. Manual: reader or reviewer report.
2. **Classify.** Assign class and severity. Critical incidents halt affected
   releases immediately.
3. **Contain.** Suspend the affected output's `published` state; move to
   `monitored` with a visible incident flag.
4. **Assess blast radius.** Query the EPG: which claims used the affected source,
   which outputs used those claims, which memory items derive from them, which
   downstream works cite the output. **This query is the reason the EPG exists.**
5. **Correct.** Issue a corrected version. Never mutate the original.
6. **Supersede.** The original decision moves to `superseded`, with the original
   rationale intact. The original provenance bundle is preserved and a superseding
   bundle is created.
7. **Notify.** Downstream consumers identified in step 4.
8. **Record.** Incident record, SDL entries, gate records.
9. **Learn.** A reviewer lesson enters RPM - under the memory write gate like any
   other write. An evaluation fixture is added so the same failure is detectable
   next time.

## Step 9 is not optional

An incident that produces no new evaluation fixture will recur. Every high or
critical incident closes with a fixture in `evals/fixtures/regression/` or
`evals/fixtures/adversarial/`.

## Reviewer override

A reviewer verdict may be overridden by a human approver. The override writes an
SDL `reviewer_override` entry with the **dissenting view recorded**. Suppressing
dissent is itself an incident.
