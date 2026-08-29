# SWOS Capability Layer

SWOS core asks for capabilities, never vendor identities.

The frozen v1 vocabulary is defined in `contracts/capability-contract/capabilities-v1.json` and implemented by `swos_runtime/capabilities.py`.

For every capability the contract fixes five things: input shape, output shape, assurance requirements, provenance requirements, and failure behaviour. Adapters declare whether they can satisfy the contract at `full`, `native`, `sandboxed`, `external_required`, `host_dependent`, or `unsupported` level.

A core gate may therefore ask:

> Did `semantic_rerank` execute under `swos.semantic-rerank.v1` with the required assurance evidence?

It may not ask:

> Was this OpenAI? Was this Claude? Was this GPT-5.6?

Vendor/model/access metadata remains visible in provenance for reproducibility, cost, risk and audit purposes, but it has no authority to redefine scholarly validity.
