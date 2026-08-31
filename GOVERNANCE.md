# Project Governance

## Roles

| Role | Responsibility | Count |
|---|---|---|
| Maintainer | Merge rights, release authority, ADR approval | 3-7 |
| Contract owner | Owns `contracts/` and `schemas/`; approves any schema change | 1 |
| Evaluation owner | Owns `evals/`; approves any change to gates or thresholds | 1 |
| Governance owner | Owns `governance/`; approves policy and approval-matrix changes | 1 |
| Portability owner | Owns `adapters/` and the six-field frontmatter constraint | 1 |
| Discipline steward | Domain authority for one discipline pack | 1 per pack |

No single person may hold both **contract owner** and **evaluation owner**. The
role that defines correctness must not also certify it.

## Decision-making

1. **Lazy consensus** for docs, examples and fixtures: merge after 72 hours with
   no objection and one approval.
2. **Two-maintainer approval** for contracts, skills, adapters and governance.
3. **ADR required** for anything that changes a frozen schema, adds a first-class
   component, adds an agent, or changes a release gate.
4. **Veto.** The governance owner may block any change that removes an audit
   trail, weakens an approval requirement or bypasses a release gate. A veto must
   cite the specific control in `governance/`.

## Trusted contributor policy

Discipline packs and evaluation fixtures carry outsized influence: a bad rubric
silently degrades every downstream output, and a bad golden fixture bakes an
error in as ground truth.

* New contributors may propose fixtures; only a discipline steward or maintainer
  may promote a fixture into `evals/fixtures/golden/`.
* Hidden test sets are maintained by the evaluation owner and are **not** in the
  public repository, to limit evaluation gaming. Their schema and generation
  method are public; their contents are not.
* Rubrics rotate. A rubric in continuous use for four releases must be
  re-derived or re-sampled.

## Release process

See `docs/operations-and-lifecycle-playbook.md`. A source release requires a
green `make validate`, a green `make eval` with no plane regressed, an exact-SHA
release record, a concise SBOM/provenance record, retained source/citation
hashes, and known limitations. The record contains the maintainer approval and
rationale. Package signing is optional until SWOS distributes packages or gains
multiple maintainers.

## Retirement

Components may be retired. Retirement requires an ADR, a migration note and
archival of the component's provenance bundle. Deleting history is not
retirement.
