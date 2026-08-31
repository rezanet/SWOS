# Evaluation Harness

**A product subsystem, not a testing afterthought.**

```bash
make eval                                  # all eight planes
python3 evals/harness/run_evals.py --planes citation,adversarial --fail-on-gate
```

Runtime-bound mode requires one finalized SWOS run and evaluates every selected
plane against that exact subject:

```bash
python3 evals/harness/run_evals.py --all --system autonomous-swos \
  --run-dir path/to/finalized-run --out evaluation-result.json --fail-on-gate
```

Ordinary CI uses `--deterministic-subject` to build a credential-free run
through the real reference runtime before executing a plane. This is test
evidence, not a human release approval or a live-provider compatibility claim.
Contract mode without `--system` validates fixture shape only and cannot claim
runtime coverage.

Passing all planes is an automated release recommendation. A source release
still needs one maintainer-owned exact-SHA release record containing the
approval, date and rationale. The record is checked against the proof and
source hashes; it is not inferred from the automated recommendation.

## Eight planes

| Plane | Blocking condition |
|---|---|
| `retrieval` | Required source class absent, or counter-position recall zero |
| `grounding` | Any unsupported material factual claim not explicitly marked |
| `citation` | Any fabricated citation or unresolved laundering risk |
| `scholarly` | Discipline rubric threshold missed |
| `governance` | Missing audit trail or policy breach |
| `regression` | Degradation against the previous release baseline |
| `memory_contamination` | A seeded false prior accepted as fact |
| `adversarial` | A successful injection or an undetected laundering case |

`not_run` counts as `fail`. An unrun gate is an unmet gate.

## Fixture layout

```
evals/
  harness/run_evals.py      the runner
  fixtures/
    golden/                 one per discipline pack, minimum
    adversarial/            injection, laundering, over-association, false originality
    regression/             baseline snapshots per release
    memory/                 seeded false priors
  rubrics/                  scored rubrics with thresholds
  metrics.md                metric definitions
```

## Why fixtures are metadata-only

Fixtures contain claims, citations, metadata and **rights-cleared excerpts
only** - never copyrighted source text. A fixture asserting that a passage does
not support a claim needs the claim, the citation and a bounded excerpt. It does
not need the paper.

## Anti-gaming

1. **Hidden test sets** held by the evaluation owner, outside this repository.
   Schema and generation method are public; contents are not.
2. **Rotating rubrics** - four releases maximum before re-derivation.
3. **Pairwise expert review** against expert-written work, periodically.
4. **Separation of duties** - the evaluation owner and contract owner are
   different people.

## Priority

Evidence from published scholarly-synthesis work is consistent:

* Citation verification is the **minimum bar**, not perfectionism.
* **Reranking is the highest-leverage component** - fix retrieval before adding
  reviewer agents.
* **Coverage beats fluency** in expert preference studies. Optimise evidence
  breadth before prose polish.
