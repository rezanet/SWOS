# G-Prose95 Specification

Status: approved for autonomous implementation on branch `codex/g-prose95`.

This document records the implementation contract for Goal G-Prose95: bring SWOS
Prose from the current M1/G2 substrate to approximately 95% full-engine
completion. The governing user brief is the authority for scope. The repository's
current code, frozen v0.2 evidence, and existing M1 safety contract are
authoritative where they are more recent than the brief.

## Scope and non-goals

The goal covers the `swos-prose` subsystem only:

- three executable writer modes: `naturalise`, `clarify`, and `tighten`;
- five named presets: `scholarly-natural`, `precise-technical`,
  `plain-intelligent`, `elegant-essay`, and `executive`;
- conservative heuristic diagnostics that may abstain before generation only
  when positive evidence proves that no useful safe change is needed;
- semantic, contextual, and adversarial safety hardening;
- versioned active benchmark expansion with equivalent and material-change probes;
- verifier stability-distribution evidence;
- aligned Python API, CLI, portable skill, packaging, and provenance output;
- deterministic tests, quality/security gates, and hosted CI evidence.

Out of scope: v1.1, unrelated SWOS platform components, truth or citation
verification, free creative rewriting, translation, source repair, release tags,
and any change to frozen v0.2 evidence under `benchmark/baseline.json`,
`benchmark/FROZEN_AT`, or `benchmark/artifacts/raw-evidence-v0.2/`.

## Safety invariants (unchanged and strengthened only fail-closed)

1. A changed candidate can receive automatic `PASS` only after the ordinary
   deterministic and independent semantic-verifier path establishes equivalence.
2. A governed material-change probe must never receive automatic `PASS`.
   `REVIEW` and `REJECT` remain fail-closed and are never counted as `PASS`.
3. Diagnostics may skip generation only on reviewed positive evidence. Missing,
   ambiguous, contextual, or merely fluent evidence must proceed to generation
   and verification; heuristic confidence is not semantic approval.
4. Repair is a salvage operation. It is limited to two attempts, one bounded local
   span, mechanical outside-span confinement, complete provenance, and full
   re-verification after every mutation. Ambiguous localisation, structural or
   hard-invariant deltas, provider failure, and non-`PASS` re-verification fall
   back to the original source.
5. Numbers, dates, units, citations, quotations, proposition additions/removals,
   structural scope changes, causal direction, and other hard invariants bypass
   repair. Existing M1 fixtures `repair-001` through `repair-006` remain governed.
6. Read-only surrounding context is untrusted input. It may improve local flow
   only when the source proposition remains licensed by the source; context-only
   claims must not enter a candidate or justify an abstention.
7. Provider output, prompts, retrieved text, and provenance metadata are untrusted
   data. Structured parsing, bounded budgets, explicit model/prompt identity, and
   safe fallbacks are mandatory.

## Capability map and dependency direction

The work is one goal and one delivery branch, but it is decomposed into reviewable
capabilities so that each behavior has a testable contract. Dependencies point
from foundational safety to user-facing surfaces; no module may bypass the
pipeline or verifier.

| Module ID | Capability | Depends on | Primary proof |
|---|---|---|---|
| `semantic-safety` | shared result/mode/preset contracts, semantic force and context guards | existing M1/G2 | red/green semantic-delta and boundary tests |
| `writer-modes` | `naturalise`, `clarify`, `tighten` generation plans and provider support | `semantic-safety` | mode behavior, provider request, fallback tests |
| `writer-presets` | five conservative policy presets | `writer-modes` | complete matrix and preservation tests |
| `intelligent-diagnostics` | mode/preset-aware positive-evidence abstention | `semantic-safety`, `writer-modes` | unsafe-abstention and no-provider tests |
| `context-safety` | reviewed context mapping, cardinality, leakage, and instruction-injection resistance | `semantic-safety` | context attack and provenance tests |
| `verifier-stability` | repeated-draw distributions and uncertainty reporting | `semantic-safety`, `benchmark` | deterministic aggregation and live evidence |
| `benchmark-contract` | new versioned active corpus, identity/hash, material-change gate | all behavior modules | schema, count, hash, safety contract |
| `surface-alignment` | API, CLI, packaging, skill, schemas, and provenance | all behavior modules | import/CLI/skill/schema tests |
| `performance-evidence` | bounded latency, token/cost accounting, and mode/preset observations | all runtime modules | measured local and hosted reports |

Build order is therefore `semantic-safety` → `writer-modes` → `writer-presets` →
`intelligent-diagnostics` → `context-safety` → `benchmark-contract` and
`verifier-stability` → `surface-alignment` → `performance-evidence`.

## Behavioral contract

### Modes

All modes accept the same source, optional read-only context, assurance level,
provider bindings, and optional preset. They differ only in bounded editorial
objectives. Every mode returns the existing result shape extended additively with
the selected `mode`, `preset`, diagnostics, verification, repair attempts, and
provenance. The mode itself never decides semantic safety.

- `naturalise`: improve idiomatic flow and sentence construction while retaining
  scholarly/technical precision and every force-bearing expression.
- `clarify`: improve readability and resolve only syntactic ambiguity that is
  licensed by the source; unresolved ambiguity must remain unchanged or fall to
  review.
- `tighten`: remove redundant wording and compress expression without dropping
  qualifiers, conditions, exceptions, attribution, or material detail.

### Presets

Presets are explicit policy data, not hidden prompt personality. They constrain
register and objectives while sharing the same safety rules:

`scholarly-natural`, `precise-technical`, `plain-intelligent`, `elegant-essay`,
and `executive`.

Unknown modes and presets fail before provider calls. Default behavior remains
backward compatible with `mode=polish`; existing callers and fixtures must keep
their current semantics.

### Diagnostics

Diagnostics expose a recommendation (`NO_CHANGE_RECOMMENDED` or
`PROCEED_TO_REWRITE`), confidence, evidence/signals, selected mode/preset, and a
reason code. Only the reviewed abstention path can return
`NO_CHANGE_RECOMMENDED`. Context, multi-sentence structure, force-bearing
language, uncertain references, and unreviewed prose must conservatively proceed.
The benchmark must demonstrate zero unsafe diagnostic abstentions on governed
material-change fixtures.

### Provenance and resource bounds

Serialized output records source/candidate/final text, mode, preset, assurance,
diagnostic decision, verifier decision, every repair attempt, model and prompt
versions, input hashes, response IDs when available, token usage, cost estimate,
and benchmark identity where the runner produces a report. No API key or secret
may appear in output. Generation and repair budgets remain finite and visible.

## Benchmark and evidence contract

The frozen v0.2 50-case evidence is immutable. The active corpus receives a new
G-Prose95 version and a canonical SHA-256 identity. It must contain mode/preset
coverage, equivalent probes, material-change probes, context traps, diagnostic
abstention negatives, hard-invariant repair negatives, and stability probes.

The active runner must report:

- exact benchmark version, fixture count, canonical corpus hash, groups, and
  relation counts;
- zero unsafe `PASS` outcomes on all governed material-change probes;
- equivalent-pair `PASS`/`REVIEW`/`REJECT` results without relabelling abstention
  or uncertainty as success;
- diagnostics unsafe-abstention count and expectation mismatches;
- mode × preset result matrix;
- repair success/fallback/attempt distributions and token accounting including
  every `RepairAttempt.token_usage`;
- context-safety attack outcomes;
- verifier stability distributions across repeated draws;
- token, cost, and latency observations with method and model identity.

Claims are empirical and bound to the exact benchmark commit/hash. No universal
guarantee is implied.

## Success criteria

G-Prose95 is complete only when all of the following are true on the exact final
code head:

- all modes and presets are callable through API and CLI and documented by the
  portable skill;
- existing M1 safety fixtures and frozen v0.2 claims remain intact;
- deterministic tests, schema/governance tests, eight evaluation planes, lint,
  coverage policy, SCA, SAST, and clean-environment validation pass;
- the active benchmark validates with its recorded identity;
- governed material-change probes have zero unsafe `PASS` outcomes;
- diagnostic abstention is zero-unsafe on governed negatives;
- repair remains bounded, local, fully re-verified, and fail-closed;
- the final exact-head adversarial review finds no unresolved P0/P1/P2 safety or
  correctness issue;
- CI has passed on the exact pushed head;
- the final builder report records exact SHAs, runs, files, deviations, risks, and
  any measured gap to the approximately 95% target.
