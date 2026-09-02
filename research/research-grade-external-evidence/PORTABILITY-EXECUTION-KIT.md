# Six-Case Portability Execution Kit

Status: PREPARATION / REAL PASS RECORDS ABSENT
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`
Verified: 2026-09-03

Authority remains `acceptance/portability/matrix-v1.json` and `acceptance/portability/README.md` on current main.

## Shared canonical request

Topic: `Can an AI-operated machine be a witness in court?`
Length: 2500
Audience: `intelligent general reader`
Style: `scholarly-natural`
Depth: `rigorous`

Every case must first produce a genuine complete SWOS run directory, then pass:

```bash
python tools/validate_autonomous_run.py <RUN_DIR> --canonical
```

Only then may the recorder run:

```bash
python tools/record_portability_acceptance.py <CASE_ID> <RUN_DIR>
```

The recorder re-validates the run, checks environment constraints and comparison dependencies, and refuses evidence on failure. Never hand-author PASS records.

## Case 1 — openai_api

Current main already contains the exact GitHub Actions reference workflow `.github/workflows/autonomous-swos-acceptance.yml`.

Reference execution:

```bash
swos research-write \
  --adapter openai-api \
  --topic "Can an AI-operated machine be a witness in court?" \
  --length 2500 \
  --audience "intelligent general reader" \
  --style scholarly-natural \
  --depth rigorous \
  --output <RUN_DIR> \
  --json

python tools/validate_autonomous_run.py <RUN_DIR> --canonical
python tools/record_portability_acceptance.py openai_api <RUN_DIR>
```

The checked-in workflow currently uses `gpt-5.6-luna`. OpenAI's current API documentation confirms `gpt-5.6-luna` is a valid GPT-5.6 family model ID, so this model slug is not presently a blocker.

Required execution evidence includes `execution_mode=direct_api`, `api_key_used=true`, actual provider/model/config provenance and no secret material in the committed evidence.

## Case 2 — model_changed_same_provider

Run after `openai_api`, because the recorder loads the baseline evidence record.

Use the same OpenAI provider/host but a different model. Current OpenAI API documentation exposes at least `gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna` as distinct models.

The cleanest comparison is:

- baseline: `gpt-5.6-luna`;
- model-swap: `gpt-5.6-terra` or `gpt-5.6-sol`;
- otherwise same canonical request and governed contract.

The recorder must observe identical provider/host identity and a different model identity.

## Case 3 — codex_chatgpt_subscription

This is not a disguised OpenAI API run.

Current adapter authority requires:

- real Codex/ChatGPT host-native subscription execution;
- `OPENAI_API_KEY` absent;
- `execution_mode=host_native_subscription`;
- `api_key_used=false`;
- `paid_api_calls=0`;
- adapter identity containing `codex`.

After the host-native run produces a canonical SWOS run directory:

```bash
python tools/validate_autonomous_run.py <RUN_DIR> --canonical
python tools/record_portability_acceptance.py codex_chatgpt_subscription <RUN_DIR>
```

Important implementation fact: the regular `swos research-write` CLI on this baseline exposes only `--adapter openai-api`; therefore the Codex case must genuinely run through the host-native Codex adapter/work-order path, not the normal direct-API CLI command.

## Case 4 — claude_code_subscription

Current adapter authority requires:

- real Claude Code subscription host execution;
- `ANTHROPIC_API_KEY` absent;
- `execution_mode=host_native_subscription`;
- `api_key_used=false`;
- `paid_api_calls=0`;
- adapter family `claude-code`.

Then:

```bash
python tools/validate_autonomous_run.py <RUN_DIR> --canonical
python tools/record_portability_acceptance.py claude_code_subscription <RUN_DIR>
```

A direct Anthropic API run cannot be relabelled as this case.

## Case 5 — replay_host_bundle

This must use the real frozen replay/host-bundle path with both provider API credentials absent.

Required record properties:

- `execution_mode=replay`;
- `api_key_used=false`;
- `paid_api_calls=0`;
- exact replay bundle digest/provenance;
- full canonical validator PASS.

Then:

```bash
python tools/validate_autonomous_run.py <RUN_DIR> --canonical
python tools/record_portability_acceptance.py replay_host_bundle <RUN_DIR>
```

Replay cannot substitute for either subscription-host case.

## Case 6 — api_provider_changed

### Current implementation gap found

The frozen matrix requires a second `direct_api` execution whose adapter differs from `openai_api`.

Current repository inspection found:

- architecture documentation explicitly contemplates `anthropic-api` and `local-model` behind the provider-neutral boundary;
- the current `adapters/` directory contains `openai-api`, Codex, Claude Code, CLI, MCP, IDE and Agent Skills adapters, but no checked-in `anthropic-api` direct API adapter;
- the current `swos research-write` CLI exposes only `--adapter openai-api`.

Therefore `api_provider_changed` does not currently have an obvious executable second direct-API adapter on this baseline.

This is a genuine pre-execution portability blocker, not missing human evidence.

Because provider replacement is already a frozen T127 acceptance requirement and host-independence architecture explicitly permits provider-specific adapters, the appropriate repair is the minimum conforming second direct-API adapter, not a new scholarly-policy feature.

Before any PASS attempt, the implementation builder should either:

1. identify an already implemented conforming second direct-API path that current research missed; or
2. implement the smallest provider-neutral-contract-compliant second direct API adapter (the architecture names `anthropic-api` as an example), with tests proving it cannot change SWOS scholarly policy.

Then the actual run must use a provider/adapter different from the `openai_api` evidence and satisfy the canonical validator before recorder output is allowed.

## Final release check

Only after all six genuine recorder-produced records exist:

```bash
python tools/check_portability_acceptance.py --release
```

must pass both G-HOST and G-PORT.

## Security/evidence hygiene

- never commit API keys/tokens/subscription secrets;
- never paste secret-bearing logs into evidence;
- retain full run packages as immutable CI/release artifacts when appropriate;
- bind evidence to run-manifest hash and final integrity-chain hash;
- an unavailable environment stays NOT_RUN, never simulated PASS;
- model/provider differences may change prose, source selection and argument structure; equivalence is governed outcome equivalence, not text equality.