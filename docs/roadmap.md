# Roadmap

## v1.0.0 - Specification Lock (this release)

Freeze the contracts and schemas. This is the release the architecture assessment
called for: *do not spend the next milestone polishing prompt wording or adding
agents - spend it extracting contracts.*

Shipped: Master Prompt Contract, Agent Prompt Pack (9 agents), Tool Contract,
Memory Governance Contract, Host Adapter Contract, Evaluation Contract; nine
frozen schemas; the Knowledge & Reasoning Specification; nine discipline packs;
seven reviewer packs; seven policy-as-code controls; the eight-plane harness; six
adapters; ten ADRs.

## v1.1 - Reference Implementation

* Reference orchestrator and state store
* Reference EPG, SDL and RPM stores with hash chaining
* Cross-encoder reranker reference implementation - **highest-leverage single
  component**, ahead of any new agent
* Corpus adapters for open scholarly indexes
* Working CLI end to end
* Full harness bound to a system under test, replacing contract mode

Sequencing note: the reranker precedes every capability addition. Ablation
evidence is consistent that removing reranking costs more correctness than almost
any other component. Adding reviewer agents to a weak retrieval stack multiplies
coordination cost and improves nothing.

## v2.0 - Research Grade

* Research Program Memory in production use across projects
* Discipline ontologies formalised beyond rubrics
* Citation-support scoring as a trained classifier, not a heuristic
* Source-diversity controls with measured targets
* Method-critique depth per discipline
* Provenance bundles with full PROV round-trip certification
* Promotion of art history and art criticism to agents, with the image and
  object-analysis tool that justifies it
* Multimodal scholarly reasoning: artworks, diagrams, microscopy, spectra,
  charts, manuscripts

## v3.0 - Product Grade

* Enterprise identity, RBAC and ABAC
* Tenant isolation
* Observability dashboards and drift monitoring
* Incident workflow automation
* Compliance reporting
* Cost controls and service management

## Deferred deliberately

| Capability | Why it waits |
|---|---|
| Novelty estimator | Requires prior-art coverage v1 retrieval does not guarantee. Premature novelty estimation manufactures false originality - the second-named risk in the register. |
| Gap detection at programme scale | Requires RPM history across many works. |
| Multi-disciplinary theory builder | Highest false-originality and over-association risk in the system. Built after the planes that catch both. |
| Concept synthesis and analogy discovery | Requires a mature knowledge graph. Premature synthesis is over-association wearing a lab coat. |
| Automated peer-review response drafting | Requires reviewer-lesson history in RPM. |

The sequencing principle is explicit: **capabilities whose failure mode is false
originality or over-association are built after the evaluation planes that detect
them, never before.** Building the theory builder first would produce a system
that generates confident novel-sounding syntheses with no means of telling whether
they are novel or true.

## What "done" looks like

SWOS is finished for v1 when a reviewer can take an output, open the audit pack,
and answer four questions without asking anyone: *what supports this claim, where
did it come from, why was this judgement made, and who approved the release.*

Everything in this roadmap serves those four questions.
