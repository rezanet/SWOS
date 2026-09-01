# ADR-0012: Research Grade discipline profile and v1 migration

- Status: accepted for the v2 implementation
- Decision date: 2026-09-01
- Scope: the nine Research Grade discipline packs

The v2 profile uses the stable `https://swos.example.org/discipline/` IRIs and
one reviewed pack per supported discipline. `enterprise_reporting` remains a
frozen v1 compatibility value; it is not mapped to `interdisciplinary` and v2
rejects it with an explicit migration error.

The v1 profile is retained for one minor release as a warning window. A
reversible migration records the original v1 value, source schema version,
target pack, and migration tool digest. A reverse migration restores the
original value from that record. Migration is data transformation only; it
does not claim that a v1 decision was made under the v2 ontology.

Pack authors must keep Turtle as the canonical source, use stable IRIs, declare
weights in the closed interval `(0, 1]`, provide required relationships and
failure modes, and add a reviewed positive, negative, boundary, and
cross-discipline fixture. Extensions require an explicit version and mapping.

Approval requires this ADR plus two maintainers. The release manifest and
compiled profile digest are retained with every downstream decision.
