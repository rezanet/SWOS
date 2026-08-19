---
contract: swos-evaluation-contract
version: 1.0.0
status: frozen
---

# SWOS Evaluation Contract

The evaluation harness is a **product subsystem, not a testing afterthought**.
It is the mechanism by which "this output is trustworthy" becomes a checkable
statement rather than an assertion.

Evaluation is decomposed because the failures are decomposed. Fluent prose over
irrelevant sources, correct sources supporting the wrong claim, and a rigorous
argument with an unauditable trail are three different failures with three
different controls. One aggregate score hides all of them.

## Eight planes

| # | Plane | Measures | Release gate |
|---|---|---|---|
| 1 | **Retrieval** | Context precision, context recall, hit rate@k, MRR, nDCG, source diversity, seminal-source recall, counter-position recall | Fails if a required source class for the discipline is absent, or counter-position recall is zero |
| 2 | **Grounding** | Faithfulness, unsupported-claim rate, overclaim rate, evidence-span coverage | Fails on any unsupported material factual claim not explicitly marked |
| 3 | **Citation** | Citation existence rate, metadata correctness, citation precision, recall and F1, laundering-detection rate, quotation accuracy | Fails on any fabricated citation or unresolved laundering risk |
| 4 | **Scholarly quality** | Contribution clarity, argument validity, method rigour, originality, coverage, interpretive plausibility, counterargument handling, audience fit | Requires discipline rubric pass |
| 5 | **Governance** | Access compliance, data-classification compliance, auditability, provenance completeness, approval-evidence coverage, disclosure presence | Fails on missing audit trail or any policy breach |
| 6 | **Regression** | Deltas across prompt, schema, agent, tool, model and retriever changes | Fails on degradation against the previous release baseline |
| 7 | **Memory contamination** | False-prior rejection rate, contradiction-detection rate, unsupported-write rejection rate | Fails if a seeded false prior is accepted as fact |
| 8 | **Adversarial** | Injection resistance, citation-laundering detection, over-association detection, false-originality detection, red-team pass rate | Fails on any successful injection or undetected laundering case |

Planes 1-3 derive their metric vocabulary from established RAG evaluation
practice, which separates retrieval context quality, faithful use of context and
answer relevance rather than collapsing them. Plane 4 uses discipline rubrics.
Planes 5-8 are SWOS-specific and are the planes most systems omit.

## Gate semantics

| Result | Meaning | Effect |
|---|---|---|
| `pass` | Every metric met its threshold | Plane does not block |
| `warn` | Non-blocking metric below threshold | Recorded; triggers review at Operate |
| `fail` | A blocking metric failed | **Release blocked** |
| `not_run` | Plane not executed | Treated as `fail` for a release decision |

`not_run` is deliberately not neutral. An unrun gate is an unmet gate.

## Anti-gaming controls

Evaluation gaming - optimising for the rubric rather than for scholarship - is a
named risk with three named controls, all mandatory:

1. **Hidden test sets.** Maintained by the evaluation owner outside the public
   repository. Schema and generation method are public; contents are not.
2. **Rotating rubrics.** A rubric in continuous use for four releases must be
   re-derived or re-sampled.
3. **Pairwise expert review.** Periodic blind pairwise comparison against
   expert-written work, not only absolute scoring.

A fourth control is structural: the evaluation owner and the contract owner must
be different people. The role that defines correctness cannot also certify it.

## Priority guidance

Empirical work on scholarly synthesis is consistent on where effort pays:

* **Citation verification is the minimum bar, not perfectionism.** Frontier
  general-purpose models fabricate citations in the large majority of scientific
  queries. Rule #5 is what makes the difference between competitive and
  disqualifying.
* **Reranking is the highest-leverage single component.** Ablations report the
  largest correctness losses from removing reranking. Fix retrieval before adding
  reviewers.
* **Coverage matters more than fluency.** In expert pairwise-preference studies,
  coverage and relevance dominate the stated reasons for preferring one answer
  over another; organisation and citation accuracy matter less; prose polish
  least. Optimise coverage and evidence breadth before style.

## What a release requires

```
release_permitted =
      all(plane.gate_result == "pass" for plane in required_planes)
  and provenance_completeness == 1.0
  and open_blocker_findings == 0
  and human_approver_recorded_where_required
  and audit_pack_complete
```

Any `false` blocks. Overrides are possible and are recorded as a governance
waiver with a reason, an approver and an expiry - never as a silent exception.
