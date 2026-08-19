# Source Rights and Licence Policy

Scholarly tools ingest protected material. This gate runs **before** evidence is
stored and **before** any artefact is exported.

## Gate: `source_rights`

Triggers on `before_store` and `before_export`.

| Check | Requirement |
|---|---|
| Licence identified | Every `source_instance` carries a licence or `unknown` |
| Access status | One of open access, subscription, licensed, internal, restricted, unknown |
| Redistribution flag | Explicit boolean; `unknown` licence implies `false` |
| Excerpt limit | Character limit for stored quotations, per licence |
| Attribution requirement | Recorded where the licence requires it |

## Rules

1. **Never store full text** of a source SWOS does not have redistribution rights
   for. Store metadata, identifiers, provenance and excerpts within the limit.
2. **Never bypass a paywall.** A paywalled source is cited from metadata, and the
   access limitation is reported in the coverage report - it is a real limit on
   the work and concealing it is a coverage-bias failure.
3. **`unknown` licence defaults to most restrictive.** No redistribution, minimum
   excerpt limit, no export.
4. **Export is a separate decision from storage.** Rights to retrieve are not
   rights to redistribute. The gate runs twice.
5. **Third-party corpora require due diligence** before connection: licence
   review, data-handling review and a recorded connector risk assessment.

## Repository application

This policy also governs the repository itself. `examples/` and
`evals/fixtures/` contain **metadata, identifiers and rights-cleared excerpts
only**. Never copyrighted source text. Each example corpus carries its own
`DATA-LICENCE.md`. MIT covers the code; it does not launder the data.
