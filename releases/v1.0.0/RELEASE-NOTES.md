# SWOS v1.0.0 — Specification Lock

**Release status:** candidate — publication is blocked until the release-record PR passes all SWOS CI gates, the release SDL is approved, and the provenance bundle is frozen.

**Release date:** 2026-08-20

SWOS v1.0.0 is the first public governed release of the Scholarly Writing Operating System. It freezes the contract and schema layer at 1.0.0 and establishes the repository as a host-agnostic, model-agnostic scholarly reasoning platform built around explicit evidence, provenance, decision records, governance and evaluation.

## Release scope

This release includes:

- frozen v1.0.0 contracts for master prompt behaviour, agents, tools, memory, host adapters and evaluation;
- frozen JSON Schemas for the Evidence Matrix, Argument Graph, Evidence Provenance Graph, Scholarly Decision Ledger, Research Program Memory, reviewer findings, evaluation results, governance gates and scholarly state;
- the Knowledge & Reasoning Specification;
- governance policies, approval thresholds, risk register and NIST AI RMF crosswalk;
- eight-plane evaluation harness and fixtures;
- host adapters for Agent Skills, Claude Code, Codex, MCP, CLI and IDE environments;
- discipline packs, reviewer packs, worked examples and operations documentation;
- event-aware, fail-closed DCO enforcement for pull requests and pushes.

## Compatibility and version boundary

`VERSION` remains `1.0.0`. No contract or schema file changed between the original publication commit `d9256688c6b5707c739596b23f0a9fb0023a8e1b` and the release-audit base `bcf096fe87585121729d80e32e672ba772eb06f5`. The intervening changes are CI wiring and DCO-enforcement hardening only.

Semantic versioning applies to contracts and schemas. Documentation-only corrections and release records do not alter the 1.0.0 contract/schema boundary.

## Known gaps carried to 1.1

These are declared limitations, not silent omissions:

- no reference retrieval corpus is bundled; corpus choice remains an operator responsibility;
- the cross-encoder reranker is specified but has no reference implementation;
- novelty estimator, gap detector and theory builder remain outside the 1.0.0 specification-lock scope.

## Validation

Final publication requires the release-record PR to pass:

- schema and contract conformance;
- Agent Skills six-field constraint;
- governance policy check;
- all eight evaluation planes;
- hardened DCO sign-off verification.

The evaluation harness in v1.0.0 runs in **contract mode** when no system under test is bound. A passing contract-mode run verifies fixture/gate conformance; it does not claim empirical model quality.

## Governance records

The release audit pack is stored under `releases/v1.0.0/`:

- `RELEASE-AUDIT.md`
- `release-provenance-bundle.json`
- `release-sdl.json`
- `BACKOUT.md`

The release must not be tagged until `release-sdl.json` is approved and `release-provenance-bundle.json` has `frozen: true`.

## Authorisation

The repository owner explicitly authorised the final v1.0.0 release audit and publication workflow through the authenticated GitHub-connected session on 2026-08-20. Final approval remains conditional on the release SDL and final CI.

**Approver:** `github:rezanet` — repository owner / governance approver
