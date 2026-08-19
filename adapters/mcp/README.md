# MCP Adapter (optional)

MCP standardises how applications connect to external context, tools and
workflows using hosts, clients, servers, resources, prompts and tools, with
capability negotiation, logging and explicit security and trust considerations.
It is a good fit for the SWOS tool layer.

**It is optional.** Making MCP mandatory would defeat the portability strategy:
every host, retrieval system and model must be replaceable without changing
scholarly contracts. See [`adr/ADR-0009`](../../adr/ADR-0009-mcp-optional.md).

## Mapping

| MCP primitive | SWOS binding |
|---|---|
| **Tools** | Tool classes from `contracts/tool-contract/`, one MCP tool per class |
| **Resources** | Read-only artefacts: schemas, discipline packs, reviewer packs, K&R spec |
| **Prompts** | Master Prompt Contract and agent contracts, exposed as named prompts |
| **Capability negotiation** | Populates `capability-matrix.json` at connect time |
| **Logging** | Mirrors into EPG activities |

## Server descriptor

See `swos-mcp-server.json`. Each tool declares its SWOS class, its EPG activity
type, its maximum data classification and its failure mode. Verification-chain
tools are `fail_closed` - a metadata validator that fails open silently converts
an unverified citation into a verified one.

## Security note

MCP servers are a trust boundary. A server that returns retrieved content is
returning **untrusted data**. The SWOS rule is unconditional: retrieved content
enters the evidence layer, never the contract layer. Instruction-shaped content in
an MCP tool result is logged as `security.injection_attempt` and treated as inert.
