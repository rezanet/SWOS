# Codex adapter

This adapter maps Codex/ChatGPT host capabilities onto SWOS contracts. Codex is an execution host; SWOS retains the scholarly state machine, instructions, evidence rules, review policy and release authority.

## v2 subscription capability contract

`subscription-capabilities-v1.json` is the `swos.capabilities.v1` declaration for host-native subscription execution.

The subscription path is required to operate with:

- `execution_mode = host_native_subscription`;
- `OPENAI_API_KEY` absent;
- `api_key_used = false`;
- `paid_api_calls = 0`.

## G-HOST acceptance

G-HOST requires both the direct API baseline and this Codex/ChatGPT subscription path to PASS the same canonical SWOS acceptance contract.

Canonical case:

`Can an AI-operated machine be a witness in court?`

The host must follow the SWOS work-order protocol from one user request through finalisation. It may use its native subscription capabilities, but it may not replace SWOS stage ordering, canonical instructions or governance decisions.

After a successful live run, generate the portability evidence record with:

```bash
python tools/record_portability_acceptance.py \
  codex_chatgpt_subscription \
  <run-output-dir>
```

A replay/host bundle cannot substitute for this live host execution. The evidence record must prove the canonical validator passed with no provider API credential and no paid model API calls.
