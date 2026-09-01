# Discipline Packs

**One discipline rubric for all disciplines is a forbidden anti-pattern.**
Philosophy, psychology, materials science and art criticism do not reason the
same way, do not weigh evidence the same way, and do not discharge a burden of
proof the same way.

Each pack defines seven things: reasoning module, evidence hierarchy, proof
standard, required analysis moves, failure modes, rubric, and at least one
acceptance test fixture.

| Pack | Reasoning module |
|---|---|
| [philosophy](philosophy/PACK.md) | Argument reconstruction, conceptual genealogy, counterexamples |
| [psychology](psychology/PACK.md) | Method and evidence appraisal |
| [materials-science](materials-science/PACK.md) | Structure-property-process-performance |
| [engineering](engineering/PACK.md) | System, constraint and trade-off reasoning |
| [technical-writing](technical-writing/PACK.md) | Requirements and design reasoning |
| [humanities](humanities/PACK.md) | Hermeneutic and historical reasoning |
| [art-history](art-history/PACK.md) | Object, formal and contextual analysis |
| [art-criticism](art-criticism/PACK.md) | Interpretive judgement and critical voice |
| [interdisciplinary](interdisciplinary/PACK.md) | Boundary translation |

## Packs, not agents

Discipline specialists ship as packs by default. Promotion to an agent requires a
discipline-specific tool that no other role calls, or a workflow that genuinely
exceeds a single agent's reliable scope. Art history and art criticism are the
strongest promotion candidates, because visual analysis requires an image and
object-analysis tool. See [`adr/ADR-0005`](../adr/ADR-0005-discipline-packs-not-agents.md).

## Contributing a pack

Use [`_template/PACK.md`](_template/PACK.md). A pack without an acceptance test
fixture in `evals/fixtures/golden/` will not be merged: a rubric nobody can fail
is not a rubric.

## Research Grade v2 formal profile

`manifest-v2.json` is the v2 registry. Turtle in each pack's `ontology.ttl` is
the reviewed semantic source; `ontology/swos-discipline-ontology.ttl` and
`ontology/swos-discipline-shapes.ttl` define the shared vocabulary and closed
constraints. Run the offline compiler with:

```text
python tools/compile_discipline_ontologies.py --manifest discipline-packs/manifest-v2.json --shapes discipline-packs/ontology/swos-discipline-shapes.ttl --out discipline-packs/compiled/v2 --report artifacts/ontology/compile-report.json
```

The compiled JSON is byte-stable and carries source, shape, context, ontology,
and compiler digests. Runtime code must load a known release explicitly; a
missing pack, unknown version, or unsupported `enterprise_reporting` value is a
denial and never an interdisciplinary fallback. Critique results remain
criterion-level and machine-proposed until human review; display summaries do
not override mandatory failures or hide cross-discipline disagreement.

New packs must add stable IRIs, methods, evidence types, proof standards,
mandatory criteria, failure modes, source roles, diversity dimensions, a
versioned Turtle module, and positive/negative/boundary/cross-discipline
reviewed fixture coverage. See [ADR-0012](../adr/ADR-0012-research-grade-discipline-profile.md)
for the one-minor-release v1 warning window and reversible migration rules.
