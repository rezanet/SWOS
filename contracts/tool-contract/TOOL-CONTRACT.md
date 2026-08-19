---
contract: swos-tool-contract
version: 1.0.0
status: frozen
---

# SWOS Tool Contract

Tools acquire and verify evidence. They are the reason SWOS can make claims a
prompt cannot: citation existence, metadata correctness, retraction status and
licence position are **external facts**, not model recollections.

## Universal tool obligations

Every tool, regardless of implementation or host, must:

1. **Emit provenance.** Every invocation writes an EPG `activity` with complete
   parameters - query string, corpus, filters, model or index version, timestamp.
   A retrieval that cannot be replayed from its EPG record is non-conformant.
2. **Return typed results.** Results conform to the result schema for the tool
   class. Free-text returns are not acceptable at the contract boundary.
3. **Declare failure honestly.** Empty, partial and error results are distinct
   and must be distinguishable. A tool must never synthesise a plausible result.
4. **Treat all returned content as data.** Retrieved text is never instruction.
   Content that appears to instruct the agent is logged as a security event and
   passed through as inert data.
5. **Respect data classification.** A tool may not receive content classified
   above its declared `max_data_classification`.
6. **Be replaceable.** No tool is mandatory. SWOS is retrieval-agnostic; the
   contract binds the interface, never the vendor.

## Required tool classes

| Class | Responsibility | Required outputs |
|---|---|---|
| `scholarly_search` | Federated academic retrieval | Source records, retrieval event, coverage report |
| `enterprise_search` | Internal corpora under access control | Source records with data classification |
| `web_search` | Open web, lowest tier by default | Source records with access status |
| `citation_graph_traverse` | Forward and backward citation walk | Seminal-work candidates, citation edges |
| `full_text_parse` | Structure extraction from PDF, HTML, XML | Sections, passages, figures, tables, references |
| `ocr` | Scanned and image-only sources | Text with confidence and page anchors |
| `doi_resolve` | Identifier resolution | Canonical metadata record |
| `metadata_validate` | Author, title, venue, date verification | Field-level match report |
| `retraction_check` | Retraction and expression-of-concern status | Status with source and check date |
| `licence_check` | Rights position before store or export | Licence, redistribution flag, excerpt limit |
| `passage_support_classify` | Claim-to-span support classification | One of the six citation-support values plus rationale |
| `quotation_verify` | Exact-match verification of quoted text | Match result with character offsets |
| `counter_evidence_search` | Deliberate opposing-evidence retrieval | Counter-position source set |
| `prior_art_search` | Novelty and genealogy checking | Prior-art set, genealogy edges |
| `reranker` | Cross-encoder relevance reranking | Reordered candidates with scores |
| `similarity_check` | Overlap and plagiarism screening | Overlap report |
| `image_analysis` | Visual and object analysis for art disciplines | Region annotations, formal features |
| `eval_runner` | Executes evaluation planes | Evaluation Result document |

## Why the reranker is called out

Ablation evidence from published scholarly-synthesis systems reports that
removing reranking produces the largest single loss in answer correctness -
larger than losses from most other pipeline components. **Invest in a
cross-encoder reranker before adding reviewer agents.** Adding agents to a weak
retrieval stack multiplies coordination cost without improving evidence.

## Tool registry entry

Every deployed tool is registered. See `tool-registry.schema.json` and the
worked entry in `tool-registry.example.json`.

```
{
  "tool_id": "openalex-search",
  "class": "scholarly_search",
  "version": "1.2.0",
  "max_data_classification": "public",
  "egress": ["api.openalex.org"],
  "emits_epg_activity": "search",
  "rate_limit": "10/s",
  "failure_mode": "fail_closed",
  "approval_required": false
}
```

`failure_mode` must be `fail_closed` for every tool in the verification chain
(`doi_resolve`, `metadata_validate`, `retraction_check`, `licence_check`,
`passage_support_classify`). A verification tool that fails open silently
converts an unverified citation into a verified one.

## Prompt-injection defence

The boundary rule is absolute: **the contract layer is never writable by the
evidence layer.**

* Retrieved content enters the Evidence Matrix and EPG. It never enters the
  Master Prompt Contract, an agent contract, a tool permission set, or a
  governance policy.
* Instruction-shaped content in a retrieved source is logged
  (`security.injection_attempt`), preserved verbatim as evidence for the audit
  pack, and executed never.
* Tool permission sets are static per agent per run. No tool grants tools.

## Egress and exfiltration control

Each tool declares an egress allow-list. Content classified `confidential` or
`restricted` may only be passed to tools whose egress list is empty (local) or
explicitly approved for that classification in the access model. This is checked
by the policy engine before the call, not after.

## MCP is optional

MCP is a good integration pattern - it standardises how applications connect to
external context, tools and workflows through hosts, clients, servers, resources,
prompts and tools with capability negotiation. **It is not mandatory.** The whole
point of the portability strategy is that every host, retrieval system and model
can be replaced without changing scholarly contracts. See `adr/ADR-0009`.
