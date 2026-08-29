# SWOS v2 Portability Acceptance

This directory defines the hard portability gate for SWOS v2.

> **SWOS owns the scholarly process. Models provide capabilities.**

The six execution cases in `matrix-v1.json` all run the same canonical request and are judged by the same SWOS scholarly and governance contracts. The resulting articles may differ. Textual identity is not a portability requirement.

## Canonical case

`Can an AI-operated machine be a witness in court?`

- 2,500 words
- intelligent general reader
- scholarly-natural
- rigorous

## Required governed equivalence

Every PASS record must prove:

- a valid Evidence Matrix;
- a valid Argument Graph;
- verified citations and source metadata;
- verified limitation/counter-evidence;
- completed governed review;
- correct Scholarly State transitions;
- no release while blocker/major findings or governance failures remain;
- the complete required audit package;
- a valid integrity chain and run manifest;
- provider/model/adapter provenance that matches the execution environment;
- `APPROVED` only when the SWOS release requirements pass.

Different models may produce different research plans, source sets, arguments and prose. Portability means equivalent **governed outcomes**, not identical text.

## Gates

### G-HOST — Host Independence Gate

Both must PASS:

1. `openai_api`
2. `codex_chatgpt_subscription`

The Codex subscription run must have `OPENAI_API_KEY` absent, `api_key_used=false`, and `paid_api_calls=0`. With no provider API credential available, purchased API credits cannot be used by the SWOS run.

### G-PORT — Cross-Host Portability Gate

All must PASS:

1. `claude_code_subscription`
2. `replay_host_bundle`
3. `api_provider_changed`
4. `model_changed_same_provider`

The Claude Code run must be a real subscription-host execution with `ANTHROPIC_API_KEY` absent, not an API call relabelled as a host run.

## Recording evidence

A real execution environment runs the canonical case, validates the complete run package with `tools/validate_autonomous_run.py --canonical`, then produces a small evidence record with `tools/record_portability_acceptance.py`.

Evidence records belong in:

`acceptance/portability/evidence/<case-id>.json`

The record contains the immutable run-manifest hash, final integrity-chain hash, canonical-request fingerprint, execution provenance, environment/credential assertions and validator result. The full run package may be retained as a CI/release artefact; it does not need to be committed merely to make the matrix readable.

Do not hand-author a PASS record. The recorder refuses to create one unless the canonical SWOS validator passes first.

## Enforcement

`tools/check_portability_acceptance.py` has two modes:

- `--definitions-only`: validates the frozen matrix and any evidence records that are present. This runs during normal development.
- `--release`: requires all six cases to have valid PASS evidence and requires both G-HOST and G-PORT to pass. A ready-for-review v2 PR must satisfy this mode.

Replay evidence cannot substitute for either live host acceptance case.
