# Operations and Lifecycle Playbook

## Release checklist

- [ ] `make validate` green
- [ ] `make lint-skills` green
- [ ] `make governance-check` green
- [ ] `make eval` green, no plane regressed against the baseline
- [ ] Every ADR for this release merged
- [ ] `CHANGELOG.md` updated, including **known gaps**
- [ ] Schema versions unchanged, or a migration shipped and an ADR merged
- [ ] Adapter capability matrices reviewed against any new capability
- [ ] Release notes signed
- [ ] Provenance bundle for the release itself created and frozen
- [ ] Governance-owner approval recorded as an SDL `release` entry
- [ ] Backout plan documented and tested

## Rollback

Trigger: a regression detected post-release, a critical incident, or a governance
breach.

1. Halt distribution of the affected version.
2. Restore the previous contract and schema pack version.
3. Works in flight at states `initiated` through `argument_constructed` continue
   on the previous version. Works at `draft_generated` or beyond are **re-gated**
   under the previous version rather than migrated.
4. Record the rollback as an SDL `release` entry with `decision: rollback`.
5. Open an incident; close it only with a new evaluation fixture.

## Telemetry schema

| Signal | Purpose |
|---|---|
| `contract_version`, `schema_pack_version`, `agent_pack_version` | Attribution of any quality change |
| `model_id`, `retriever_id` | The two variables that move most |
| `tool_call_count`, `tool_latency`, `tool_failure_rate` | Retrieval health |
| `unsupported_claim_rate` | Grounding health |
| `citation_support_distribution` | Early laundering signal |
| `counter_position_recall` | Coverage-bias signal |
| `review_iterations`, `escalation_rate` | Contract or pack drift |
| `blocked_transition_count` by precondition | **Rule #3 pressure** |
| `gate_result` by gate type | Governance health |
| `waiver_count`, `waiver_expiry_overdue` | Governance erosion |
| `memory_write_rejection_rate` | Contamination pressure |
| `token_cost`, `cost_per_accepted_draft` | Economics |
| `security.injection_attempt` | Threat activity |

## Signals that warrant investigation

Not all bad news looks like an error.

| Signal | Likely meaning |
|---|---|
| Blocked `draft_generated` transitions rising | Evidence work is being skipped; contract or orchestration drift |
| Escalation rate falling to zero | The panel has stopped finding things. Check the hostile reviewer, not the quality |
| Waiver count rising | Governance erosion. Waivers are permitted; a trend is a symptom |
| **Zero blocked releases over many releases** | The gates are not gating. This is the governance-theatre signature |
| Scores improving without human-preference improvement | Evaluation gaming |
| `citation_support_distribution` shifting toward `partially_supports` | Retrieval degradation, or claims outrunning evidence |

## Periodic re-evaluation

| Cadence | Activity |
|---|---|
| Every release | Full harness, regression against baseline |
| Monthly | Retraction sweep across all cited sources in published works |
| Quarterly | Pairwise expert review against expert-written work |
| Every four releases | Rubric rotation or re-derivation |
| Annually | Full governance review, NIST AI RMF crosswalk refresh, threat-model review |

## Retirement

1. Complete the retirement checklist.
2. Archive the provenance bundle.
3. Record an SDL `retirement` entry.
4. De-register from any inventory.
5. Record deletion evidence for anything deleted under the retention policy.

Deleting history is not retirement.
