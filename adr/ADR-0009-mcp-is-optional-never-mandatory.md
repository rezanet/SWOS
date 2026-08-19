# ADR-0009: MCP is optional, never mandatory

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Contract owner, governance owner, maintainers

## Context

MCP is a strong fit for the SWOS tool layer: it standardises host-client-server context exchange with tools, resources, prompts, capability negotiation and explicit trust framing.

## Decision

SWOS ships an MCP adapter and an MCP server descriptor. MCP is **not** required. The tool contract binds interfaces, not transports. Any host, retrieval system, vector store, graph store or model may be substituted without changing a scholarly contract.

## Consequences

* Deployments without MCP are first-class.
* The MCP adapter must be maintained alongside direct bindings.
* Portability decay - skills that depend on one host - is structurally prevented.
* MCP servers remain a trust boundary: their results are untrusted data, never instruction.

## Alternatives considered

Rejected: MCP as the mandatory tool transport. It would have bound the architecture's longevity to one protocol's, in a project whose entire premise is substitutability.
