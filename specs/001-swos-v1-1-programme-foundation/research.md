# Research Notes: SWOS v1.1 Programme Foundation

## Research inputs

The three supplied files were reviewed as non-normative research inputs. Their
repository authority is deliberately limited to informing synthesis; the
constitution, frozen contracts, schemas, governance policies and canonical
roadmap remain authoritative.

| Input | Role | Derived canonical documents |
|---|---|---|
| `SWOS_Roadmap_and_Implementation_Plan.md` | Programme sequencing and implementation research | `VISION.md`, `docs/roadmap.md`, feature spec |
| `SWOS_Strategic_Roadmap.docx` | Strategic scope, delivery horizon and boundary research | `VISION.md`, `docs/roadmap.md` |
| `Research on Enterprise-Grade Writing Skills.docx` | Epistemic writing, evidence and governance research | `VISION.md`, constitution, `docs/roadmap.md` |

The exact SHA-256 values and recording date are maintained in
`docs/document-manifest.json`; absolute source paths are intentionally omitted.

## Decisions

### Adopt Spec Kit for bounded programme changes

**Decision:** Use Spec Kit v1.0.1 for roadmap milestones, architecture,
governance controls, frozen contracts/schemas, public interfaces and release
gates. Exempt routine fixes, formatting, dependency maintenance that preserves
contracts and editorial corrections.

**Rationale:** These changes have multiple independently testable outcomes and
need a durable contract across humans and agents. Requiring the same ceremony
for a typo would add noise rather than control.

### Keep version tracks separate

**Decision:** Keep Core/specification at `1.0.0`, target the reference runtime as
`v1.1`, and reserve Research Grade for `v2.0`.

**Rationale:** The contracts can remain stable while an implementation matures.
Separating tracks prevents a runtime milestone or research experiment from
silently becoming a promise to every host and consumer.

### Centralize philosophical reasoning

**Decision:** Make root `VISION.md` the long-form philosophical record, keep a
concise README pointer, and make the architecture vision a technical derivative.

**Rationale:** A single canonical explanation reduces narrative drift while
keeping implementation documentation useful to engineers.

### Separate deterministic and live evidence

**Decision:** Ordinary PR/push workflows are deterministic and provider-free.
Live compatibility is manual, exact-SHA, fail-closed and non-required.

**Rationale:** Provider credits, availability and stochastic behavior are
operational evidence, not ordinary merge prerequisites. A failed live provider
must not make a deterministic PR ambiguous, and a skipped live test must not
become a compatibility claim.

### Use a JSON document manifest

**Decision:** Store authority metadata in JSON with a Draft 2020-12 schema and a
stdlib-oriented validator.

**Rationale:** JSON is already used by SWOS contracts, is easy to validate in
CI, and avoids adding a YAML parser solely for the manifest. Semantic checks
remain in Python because corpus coverage and reciprocal links are repository
relationships rather than JSON shape alone.
