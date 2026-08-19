# Contributing to SWOS

SWOS is contract-first. The contracts and schemas are the product; prompts are
packaging. Contributions are evaluated against that hierarchy.

## Developer Certificate of Origin (mandatory)

Every commit must be signed off:

```bash
git commit -s -m "feat(discipline-packs): add archaeology reasoning module"
```

`Signed-off-by:` asserts DCO 1.1. Unsigned commits are rejected by CI. A CLA is
**not** required.

## What we want

| Priority | Contribution | Review path |
|---|---|---|
| Highest | Evaluation fixtures, especially adversarial and citation-laundering cases | 2 maintainers + evaluation owner |
| High | Discipline packs and discipline ontologies | 1 maintainer + 1 discipline steward |
| High | Reviewer packs with sharper pass/fail criteria | 1 maintainer + evaluation owner |
| Medium | Host adapters for new runtimes | 1 maintainer + portability owner |
| Medium | Documentation, worked examples, ADRs | 1 maintainer |
| Case-by-case | Schema changes | ADR + 2 maintainers + deprecation plan |

## What we will reject

* Additions to `contracts/master-prompt-contract/` that could live in a schema, a
  tool, an evaluation or a governance policy. **Rule #2 is enforced in review.**
* Any core `skills/*/SKILL.md` frontmatter key outside the six specification
  fields. Host-specific keys belong in `adapters/`.
* Executable scripts in skills without an entry in `SECURITY.md` script
  inventory and a sandbox declaration.
* Copyrighted source text in `examples/` or `evals/fixtures/`. Metadata,
  identifiers and rights-cleared excerpts only.
* New agents where a discipline pack, a rubric or a tool would do. Complexity
  must earn its keep.

## Schema change policy

Schemas under `schemas/` are **frozen at v1.0.0**.

* **Additive optional field** - minor version. Allowed.
* **New enum value** - minor version. Requires a fixture proving the new value is
  distinguishable from existing ones.
* **Required field, removed field, changed type, narrowed enum** - major version.
  Requires an ADR, a migration under `tools/migrations/`, and one minor release
  of deprecation warnings.

Every schema change ships with updated fixtures, a passing `make validate`, and a
regression run showing no degradation.

## Discipline pack checklist

A discipline pack is not accepted until it defines all seven:

1. Reasoning module - what kind of reasoning this discipline actually performs.
2. Evidence hierarchy - what counts as strong evidence in this field.
3. Proof standard - what discharges the burden for a claim.
4. Required analysis moves - the moves a competent scholar always makes.
5. Failure modes - how output in this discipline typically goes wrong.
6. Rubric - scored, with pass thresholds.
7. Acceptance test - at least one fixture in `evals/fixtures/golden/`.

Use [`discipline-packs/_template/PACK.md`](discipline-packs/_template/PACK.md).

## Local checks before opening a PR

```bash
make validate
make lint-skills
make eval
```

## Review standard

Reviewers apply the discipline SWOS applies to scholarship: claims in a PR
description should be supported, marked uncertain, or removed. "This improves
quality" without a fixture is not evidence.
