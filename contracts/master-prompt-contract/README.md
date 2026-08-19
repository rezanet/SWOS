# Master Prompt Contract

`MASTER-PROMPT-CONTRACT.md` is the constitutional layer of SWOS. It is the
renamed and reduced successor to the original `Prompt-for-SWOS-v01.txt`.

## What changed from the original prompt

The original prompt was directionally correct but concentrated too much
architectural weight inside prompt text. It reached into JSON schema design, EPG
entity modelling, decision-ledger fields, memory governance, discipline
ontologies, reviewer criteria, evaluation categories, repository structure and
adapter design. Those requirements were right; their **location** was wrong.

| Original prompt section | New home |
|---|---|
| Schema design (9 schemas) | `schemas/` |
| Provenance model | `schemas/provenance-graph/` + `docs/architecture/` |
| Decision ledger fields | `schemas/decision-ledger/` |
| Research Program Memory | `schemas/memory/` + `contracts/memory-contract/` |
| Knowledge & Reasoning Specification | `docs/knowledge-and-reasoning-spec.md` |
| Specialist agents | `contracts/agent-prompt-pack/` |
| Reviewer simulation | `reviewer-packs/` |
| Evaluation harness | `evals/` + `contracts/evaluation-contract/` |
| Repository structure & adapters | repository itself + `adapters/` |
| Discipline behaviour | `discipline-packs/` |

What **stayed** in the contract: mission, operating principles, the seven rules,
the input contract, the workflow contract, claim and citation discipline,
abstention rules, agent handoff rules, the output contract and the forbidden
anti-patterns.

## The test for adding anything here

> Can this requirement be satisfied deterministically, persistently, or
> measurably outside the prompt?

If yes, it does not belong in this file. That is Rule #2, and it is enforced in
pull-request review.

## Token budget

The contract is designed to sit inside a skill activation budget. Target: under
5,000 tokens for the body loaded at activation. Sections 4-7 and 10 are the
mandatory core; sections 12-13 may be loaded on demand by hosts with tighter
budgets, because they are also enforced structurally.
