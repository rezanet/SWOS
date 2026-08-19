# ADR-0006: MIT licence for code, separate licensing for data

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

Scholarly tools ingest protected material. An MIT licence on the repository does not confer redistribution rights over third-party sources, and a repository that ships copyrighted text under MIT is a rights failure regardless of intent.

## Decision

MIT covers code, schemas, contracts, specifications and templates. A licence boundary notice in `LICENSE` states explicitly what is not covered. Example corpora carry their own `DATA-LICENCE.md`. Fixtures and examples contain metadata, identifiers, provenance records and rights-cleared excerpts only - never source full text.

## Consequences

* The repository is publishable without a rights review of every fixture.
* Fixtures are less realistic than full text would allow; they compensate with precise metadata and bounded excerpts.
* The source-rights gate governs the repository by the same rule it applies at runtime.
* Contributors must understand the boundary; `CONTRIBUTING.md` states it explicitly.

## Alternatives considered

Rejected: ship a realistic example corpus. Rejected as an unmanageable and unnecessary rights liability.
