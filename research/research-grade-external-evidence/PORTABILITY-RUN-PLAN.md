# Six-Case Portability Run Plan

Status: RESEARCH/PREPARATION ONLY
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`
Authority: `acceptance/portability/matrix-v1.json`

## Canonical request

`Can an AI-operated machine be a witness in court?`

Required governed equivalence is outcome-level, not identical prose.

Every PASS case must produce a complete run package, pass:

`python tools/validate_autonomous_run.py <RUN_DIR> --canonical`

and then be recorded only with:

`python tools/record_portability_acceptance.py ...`

Never hand-author PASS evidence.

## Recommended execution order

### 1. replay_host_bundle

Purpose: cheapest deterministic validation of the replay/host-bundle path.

Requirements:

- no OpenAI/Anthropic API keys;
- no paid API calls;
- use the canonical request/run bundle;
- preserve replay bundle digest;
- validate complete governed package;
- record `acceptance/portability/evidence/replay_host_bundle.json` only through recorder.

This does not substitute for any live host case.

### 2. openai_api

Purpose: direct-API reference case.

Requirements:

- real OpenAI API execution;
- `api_key_used=true`;
- record exact adapter/provider/model/config and run provenance without exposing secret;
- validate canonical run;
- record `acceptance/portability/evidence/openai_api.json`.

This case becomes the comparison anchor for provider/model variation.

### 3. model_changed_same_provider

Purpose: prove model substitution within the same provider.

Requirements:

- provider must match `openai_api`;
- model must differ;
- same SWOS governed outcome contract;
- execution mode can follow the frozen matrix constraints;
- record `acceptance/portability/evidence/model_changed_same_provider.json` through recorder.

### 4. codex_chatgpt_subscription

Purpose: prove host-native subscription execution without API billing.

Requirements:

- execute through the real Codex/ChatGPT subscription host adapter;
- `OPENAI_API_KEY` absent;
- `api_key_used=false`;
- `paid_api_calls=0`;
- adapter family `codex`;
- canonical run validation must pass;
- record `acceptance/portability/evidence/codex_chatgpt_subscription.json`.

Do not relabel an OpenAI API run as this case.

### 5. claude_code_subscription

Purpose: second host-native subscription environment.

Requirements:

- real Claude Code subscription execution;
- `ANTHROPIC_API_KEY` absent;
- `api_key_used=false`;
- `paid_api_calls=0`;
- adapter family `claude-code`;
- canonical validator PASS;
- recorder-produced `acceptance/portability/evidence/claude_code_subscription.json`.

Do not relabel an Anthropic API run as a subscription run.

### 6. api_provider_changed

Purpose: prove provider replacement without policy/governance drift.

Requirements:

- direct API execution;
- provider/adapter must differ from `openai_api`;
- real required provider credential may be used but never persisted/logged;
- canonical governed outcome must pass;
- recorder-produced `acceptance/portability/evidence/api_provider_changed.json`.

## Common PASS contract

All six must prove, as applicable:

- valid Evidence Matrix;
- valid Argument Graph;
- verified citations/source metadata;
- required counter-evidence/limitations;
- completed governed review;
- correct scholarly state transitions;
- no release under blocking findings/governance failures;
- complete audit package;
- valid integrity chain/run manifest;
- provider/model/adapter provenance matching the actual environment;
- APPROVED only when SWOS requirements actually pass.

Different research plans, sources, arguments and article prose are allowed.

## Release check

After all six recorder-produced records exist:

`python tools/check_portability_acceptance.py --release`

must pass G-HOST and G-PORT.

## Evidence hygiene

- never commit API keys, tokens, subscription secrets or secret-bearing logs;
- retain full run packages as immutable CI/release artifacts if too large for Git;
- bind every evidence record to run-manifest hash, integrity-chain hash, canonical request fingerprint and execution provenance;
- if any run is incomplete or environment identity cannot be proven, leave it absent/NOT_RUN rather than fabricating a record.