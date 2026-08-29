# Technical Vision Derivative

> The canonical philosophical vision is [`VISION.md`](../../VISION.md). This
> document is its technical derivative; it keeps the architecture concise and
> does not duplicate the long-form reasoning.

## Technical interpretation

SWOS is a portable, governed scholarly reasoning platform. The reference
architecture treats evidence, claims, arguments, provenance, decisions,
uncertainty, review and release as explicit artefacts with machine-checkable
boundaries.

| Vision commitment | Architectural consequence |
|---|---|
| Evidence before prose | Research planning and evidence artefacts precede manuscript generation. |
| Typed support | Evidence Matrix entries distinguish claim status, citation identity and support relationship. |
| Arguments as structures | Argument Graph stores claims, warrants, objections, rebuttals and rival readings. |
| Provenance as justification | EPG, SDL and RPM preserve source, transformation, decision and correction lineage. |
| Continuous governance | Lifecycle gates, policy checks, approvals and audit packs span the whole run. |
| Human responsibility | Release requires a human approval record and separated review roles. |
| Host independence | Contracts and schemas sit below replaceable hosts, models, retrievers and adapters. |
| Minimal reference runtime | The initial implementation proves a local, reproducible file-backed path before breadth. |

## Boundary

The architecture is an assurance layer, not a chatbot, giant prompt, hosted SaaS
product, autonomous publisher, central memory service or enterprise identity
platform. Those non-goals are defined philosophically in [`VISION.md`](../../VISION.md)
and enforced technically through the contracts, governance policies and
portability checks.

## Delivery sequence

The architecture follows **Proof → Portability → Ecosystem → Standardisation**.
The current programme targets the reference runtime track `v1.1`; Core/specification
remains `1.0.0`, and Research Grade remains a future `v2.0` track.

## Source of authority

This file explains how the vision maps to components. It does not redefine the
constitution, frozen contracts or schemas. Changes that alter those boundaries
require the Spec Kit workflow and a manifest update.
