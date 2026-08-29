# Research Notes: SWOS v1.1 Runtime Reconciliation

## Exact evidence baseline

- Reconciliation base: `5eec89e88e11e9659299d51c1bbf8289b81e464f`.
- PR #41 merge: `156e2b7faa70f9affce2ed93d7dc3cb6e19b938e`.
- PR #44 foundation merge: `5eec89e88e11e9659299d51c1bbf8289b81e464f`.
- Historical `v1.1` roadmap source: `docs/roadmap.md` at PR #41 merge.
- Current programme authority: `docs/roadmap.md` at the reconciliation base.

## Verified findings

1. PR #41 implemented a provider-neutral orchestrator, persistent work-order
   protocol, capability contracts, canonical stage instructions, OpenAlex and
   Crossref adapters, generated audit artifacts, a CLI, host-bundle replay and
   deterministic tests.
2. The runtime's semantic reranker is an OpenAI Responses joint scoring call. It
   is not a local or independently identified cross-encoder implementation.
3. OpenAlex/Crossref records include title, author, date and DOI metadata, but the
   runtime has no retraction or licence-status resolver. Generated EPG entries
   explicitly report `not_checked`, `unknown` and no redistribution permission.
4. Exact quotation containment and enumerated claim-support judgements are
   fail-closed before evidence rows survive.
5. EPG, SDL, RPM, Evidence Matrix and Argument Graph documents are generated for
   a run. EPG/SDL/RPM are snapshots, not persistent stores with correction,
   supersession and per-store hash-chain operations. The RPM snapshot is empty.
6. A general run integrity chain and manifest verification exist and have
   tamper tests.
7. The end-to-end `swos` CLI is implemented, but no deterministic runtime CLI
   test exercises `research-write` or the work-order subcommands.
8. The eight-plane `autonomous-swos` adapter evaluates fixtures through functions
   in `evals/harness/autonomous_sut.py`; it does not execute
   `AutonomousSWOS.run`, so the real runtime path is not yet bound to all planes.
9. Manual live workflows define canonical runs, but no checked-in exact-head
   evidence certifies `v1.1`. Ordinary PRs correctly do not require paid calls.
10. Human-approval policies exist, but the runtime has no human approval-record
    ingestion and validation path for public release certification.

## Reconciliation decision

Retain all proved PR #41 substrate. The next implementation slice begins with a
real cross-encoder and completes retrieval/citation assurance around the already
implemented public scholarly adapters. Stores, real-SUT evaluation, human
approval and public release remain later dependency-ordered slices.
