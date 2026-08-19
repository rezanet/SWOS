# CLI Adapter

For terminal use, batch processing and CI. This is the adapter to build first:
governance gates, evaluation planes and provenance stores are far easier to wire
in a non-interactive context than behind a chat interface.

## Commands

```bash
swos init      --work-id W --discipline philosophy --output-type essay
swos plan      --work-id W --question "..." 
swos gather    --work-id W --strategy plan.json
swos matrix    --work-id W                     # build the Evidence Matrix
swos audit     --work-id W                     # citation audit
swos argue     --work-id W                     # build the Argument Graph
swos review    --work-id W --panel full
swos eval      --work-id W --planes all
swos draft     --work-id W                     # blocked unless state >= argument_constructed
swos release   --work-id W --approver alice@example.org
swos audit-pack --work-id W --out ./bundle/
swos state     --work-id W                     # show state and blocked transitions
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 10 | State transition refused - preconditions unmet |
| 20 | Governance gate failed |
| 30 | Evaluation plane failed |
| 40 | Reviewer blocker findings open |
| 50 | Provenance incompleteness |
| 60 | Rights or licence violation |

Distinct codes matter in CI: "the citation gate failed" and "the licence gate
failed" require different responses from different people.

## Rule #3 in practice

```bash
$ swos draft --work-id W-7f3a
ERROR [10] Transition refused: argument_constructed -> draft_generated
  Precondition unmet: evidence_matrix.coverage.unsupported_claims = 4 (must be 0 or explicitly marked)
  Precondition unmet: argument_graph.thesis.rival_theses_considered = [] (required for contribution_type=position)
  Recorded to blocked_transitions. No draft produced.
```

The system does not warn and continue. It refuses and records.
