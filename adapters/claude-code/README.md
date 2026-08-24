# Claude Code adapter

This adapter maps Claude Code host capabilities onto SWOS contracts. Claude Code is an execution host; it is not part of the SWOS scholarly authority layer.

## v2 subscription capability contract

`subscription-capabilities-v1.json` declares the host-native subscription capabilities required by `swos.capabilities.v1`.

The declaration is intentionally conservative:

- `execution_mode = host_native_subscription`;
- `api_key_used = false`;
- `paid_api_calls = 0`;
- citation/reviewer independence is `limited`;
- `blind_review_supported = false` until a real acceptance run proves a stronger property.

A separate context is not automatically called an independent reviewer.

## G-PORT acceptance

Claude Code is the required second-host proof for SWOS v2 portability. The canonical case is:

`Can an AI-operated machine be a witness in court?`

The host must execute the SWOS work-order protocol with `ANTHROPIC_API_KEY` absent. The resulting run must pass the same full governed outcome validator used for the API and Codex cases.

After a successful live run, generate the evidence record with:

```bash
python tools/record_portability_acceptance.py \
  claude_code_subscription \
  <run-output-dir>
```

The evidence record is committed under `acceptance/portability/evidence/`. It must not be hand-authored or inferred from the adapter declaration alone.

## Existing compatibility files

`capability-matrix.json` and `overlay.yaml` remain compatibility/installation metadata. They do not override the frozen SWOS capability contracts or the G-PORT acceptance standard.
