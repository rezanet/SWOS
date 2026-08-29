# G-Prose95 Implementation Plan

> **Historical record.** This plan belongs to the completed G-Prose95 effort. The
> authoritative current programme plan is [`docs/roadmap.md`](../docs/roadmap.md);
> this file is retained for provenance and is not an active v1.1 task plan.

This is the execution plan for the single G-Prose95 goal. It is not a sequence of
independent milestones or release claims; all gates converge on one exact branch
head and one final builder report.

## Phase 0 — baseline and threat model

- Pin base `2004efd5ac444e5eb639ac77e7eebcbabb6573a6` and preserve the two
  pre-existing untracked M1 reports.
- Record current public API/CLI, M1 repair contract, historical benchmark `0.3.0-m1`, and
  G2 quality/CI substrate.
- Threat model trust boundaries: source/context/benchmark text, LLM rewrite and
  verifier output, provider metadata, CLI input, and generated provenance.
- Abuse cases: prompt injection in source/context, context-only claim leakage,
  material change hidden by a fluent rewrite, diagnostics false abstention,
  repair span escape, malformed structured output, token/cost unboundedness, and
  secret leakage.

## Phase 1 — contract-first behavior

- Add failing tests for mode/preset validation, result serialization, and backward
  compatibility before changing the implementation.
- Add failing tests for each mode's objective and each preset's policy payload.
- Add failing tests for diagnostics abstention/abstention refusal and context traps.
- Add failing tests for hard-invariant bypass, repair bounds, re-verification, and
  provenance accounting across all modes.

## Phase 2 — implementation

- Generalise the existing rewrite plan and OpenAI adapter to the three modes and
  five presets without weakening existing polish behavior.
- Keep one common pipeline: diagnose → generate once → deterministic checks →
  independent verifier → at most two local repairs → re-verify → release or
  source fallback.
- Add explicit context mapping/guard checks and preserve unknown context as a
  fail-closed condition.
- Extend the CLI/API/skill and packaging metadata additively.

## Phase 3 — benchmark and evidence

- Add reviewed fixtures in a new versioned active corpus; retain the 56 historical
  M1 cases and identify every new fixture deterministically.
- Extend the runner/report schema for modes, presets, context safety, repair
  accounting, stability distributions, token/cost/latency measurements, and
  exact identity.
- Run deterministic benchmark validation first, then live campaigns only when
  credentials and the explicit live gate are available.

## Phase 4 — full validation and delivery

- Run tests, coverage, formatting/lint, schema/skills/governance/evaluation
  planes, benchmark contract, SCA, SAST, and clean setup replay.
- Commit coherent DCO-signed changes; never rewrite history or force-push.
- Push the exact branch head, create/update one PR for G-Prose95, inspect hosted
  CI, and perform exact-head adversarial review. Fix and re-run any finding.
- Write `G-PROSE95-FINAL-BUILDER-REPORT.md` only after final evidence is known,
  distinguish code/evidence head from any report-only docs head, and stop.
