# ADR-0003: Six-field frontmatter constraint for core skills

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

The Agent Skills specification defines six frontmatter fields. Individual hosts add useful extensions. Using a host extension where the specification is enforced produces a hard validation error, not a warning.

## Decision

Core skills in `skills/` use only `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`. Host extensions live in adapter overlay files applied at install time. `tools/lint_skills.py` enforces this in CI.

## Consequences

* SWOS skills install unmodified across every conformant host.
* Host-specific capability requires an adapter change, not a skill change.
* Some host ergonomics are available only after applying an overlay.
* Portability decay becomes detectable by a linter rather than by a user's failed upload.

## Alternatives considered

Rejected: maintain per-host skill variants. Rejected because it multiplies the surface that must stay semantically identical, and divergence would be silent.
