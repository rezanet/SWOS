# Data Model: SWOS v1.1 Capability Ledger

## Capability record

Each row records:

- `capability_id` — immutable feature-local identifier;
- `requirement` — one testable `v1.1` obligation;
- `authority` — repository document or governed PR contract that states it,
  resolved through the ledger's authority-coverage matrix;
- `slice` — the Phase 1 slice accountable for completion;
- `state` — highest evidence-backed state;
- `implementation_evidence` — exact source/configuration artifacts or an em dash;
- `test_evidence` — deterministic automated evidence or an em dash;
- `demonstration_evidence` — complete reproducible scenario or an em dash;
- `certification_evidence` — authorized independent acceptance or an em dash;
- `verified_gap` — precise missing behavior/evidence; and
- `disposition` — later Spec Kit feature that owns the gap.

## State rules

The ordered vocabulary is `specified`, `implemented`, `tested`, `demonstrated`,
`certified`. State is not a percentage. A partial implementation does not advance
the requirement beyond `specified` when the named capability is materially
absent. A complete deterministic scenario may prove `demonstrated`; it does not
prove independent certification.

## Evidence rules

- A PR description is a discovery source, not implementation evidence.
- A contract marker does not prove the implementation behind the marker.
- A fixture evaluator that does not invoke the runtime is not a real-SUT binding.
- A generated EPG, SDL or RPM-shaped document is not a persistent governed store.
- Workflow definitions are not executed live evidence.
- Certification requires an authorized reviewer and exact accepted evidence.

## Gap record

A verified gap names the missing behavior, not a broad aspiration. Dispositions
are dependency ordered:

1. retrieval and citation assurance;
2. governed stores and audit verification;
3. real-runtime evaluation and human approval; and
4. public proof and release.
