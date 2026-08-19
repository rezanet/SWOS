# Non-Functional Requirements

| ID | Requirement | Measure | Target |
|---|---|---|---|
| **NFR-1** | **Portability.** No host, model, retriever or store is mandatory | Core skills pass the six-field constraint; every adapter ships a capability matrix | 100% |
| **NFR-2** | **Provenance interoperability.** EPG round-trips to a PROV serialisation without loss | Round-trip test on every release | Lossless |
| **NFR-3** | **Auditability.** Every claim links to a provenance node | `provenance_completeness` | 1.0 at release |
| **NFR-4** | **Decision traceability.** Every mandatory decision trigger has an SDL entry | `mandatory_decisions_with_sdl_entry` | 1.0 |
| **NFR-5** | **Tamper evidence.** SDL and frozen EPG bundles are append-only with hash chaining | Chain verification on read | Verified |
| **NFR-6** | **Reproducibility.** Any retrieval can be replayed from its EPG activity record | Replay test on a sample | 100% of sampled |
| **NFR-7** | **Determinism of gates.** The same artefacts produce the same gate results | Gate re-evaluation | Identical |
| **NFR-8** | **Fail-closed verification.** Verification-chain tools never fail open | Tool registry constraint, enforced by schema | 100% |
| **NFR-9** | **Data minimisation.** No raw sensitive payloads in durable audit or memory | Audit record inspection | Zero payloads above `public` |
| **NFR-10** | **Bounded review.** Review loops terminate | Iteration count per role | Max 3, then escalate |
| **NFR-11** | **Skill discovery budget.** Skills load within the host's listing budget | Token count of name plus description | ~100 tokens per skill |
| **NFR-12** | **Activation budget.** SKILL.md body fits the activation stage | Token count of body | Under 5,000 |
| **NFR-13** | **Offline capability.** Core reasoning works without network | Local-only tool profile | Plan, argue, review, edit available |
| **NFR-14** | **Tenant isolation.** Multi-tenant deployments do not share memory or provenance | Isolation test | Enforced (Product-Grade) |
| **NFR-15** | **Cost transparency.** Cost per accepted draft is measurable | Telemetry | Reported per work |

## On NFR-13, offline capability

This is deliberate. Without retrieval, SWOS **degrades to plan-and-critique
mode**: it can plan research, structure arguments from supplied evidence, run the
argument, method and editorial reviewers, and audit internal consistency. What it
will not do is fabricate sources to compensate for missing retrieval. The skill
`compatibility` fields state this explicitly, because a silent degradation from
"verified" to "plausible" is the exact failure this platform exists to prevent.

## On NFR-7, determinism of gates

Gates must be deterministic even though the system they evaluate is not. A gate
whose result varies across runs on identical artefacts cannot block a release,
because the next run might pass. Every gate is a pure function of the artefacts
plus the policy version.

## Performance

Deliberately unspecified as absolute latency targets. SWOS is a governance and
reasoning layer over an operator-selected model and retriever; publishing latency
targets would describe someone else's infrastructure. What is specified:

* Gate evaluation must not require a model call - gates are deterministic checks
  over artefacts.
* The blast-radius query must complete as a graph traversal, not a scan.
* Review is bounded, so worst-case review cost is `roles x 3` passes, not
  unbounded.
