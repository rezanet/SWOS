---
name: swos-reviewer
description: Runs a bounded, role-based reviewer panel against a manuscript, argument or report - citation auditor, methodologist, argument examiner, discipline expert, hostile reviewer, editor and governance reviewer, each with explicit test, pass, fail and escalation criteria. Use for peer-review simulation, pre-submission review, red-teaming an argument, stress-testing a position paper, adversarial critique of a report, or checking whether a conclusion survives attack. Finds hidden premises, circular reasoning, unsupported claims, method weakness, statistical overreach, over-association, interpretive flattening and false originality. Use when the question is not "is this well written" but "does this survive review".
license: MIT
compatibility: Full panel benefits from retrieval for counter-evidence and prior-art checks. Argument, method and editorial review work without retrieval. Discipline expert review requires the relevant discipline pack.
metadata:
  version: 1.0.0
  swos_component: reviewer
  spec: agent-skills
allowed-tools: [counter_evidence_search, prior_art_search, passage_support_classify, similarity_check]
---

# SWOS Reviewer Panel

"Review this critically" is not a specification. Every reviewer is a named role
with test, pass, fail and escalation criteria.

## The seven roles

| Role | Tests |
|---|---|
| **Citation auditor** | Fabricated references, wrong metadata, citation laundering |
| **Methodologist** | Study design, bias, construct validity, statistical overreach |
| **Argument examiner** | Warrant strength, hidden premises, circular reasoning, rebuttals |
| **Discipline expert** | Field norms, missing literature, discipline-specific proof standards |
| **Hostile reviewer** | The weakest load-bearing part of the thesis |
| **Editor** | Structure, voice, concision, genre fit - without changing meaning |
| **Governance reviewer** | Data handling, disclosure, audit completeness, policy |

Full criteria: `references/reviewer-packs/`.

## Bounded loop

```
draft -> citation audit -> argument audit -> method audit -> discipline audit
      -> hostile review -> revision -> final unsupported-claim scan
      -> human approval pack
```

**Iteration cap: 3.** On the fourth pass, escalate to a human. Unlimited
self-refinement is a forbidden anti-pattern: it converts unresolved disagreement
into fluency.

## Blind review

Where the host permits, run the hostile reviewer and the argument examiner
**blind** - without showing them prior AI suggestions or earlier verdicts.
Automation anchoring, where reviewers accept polished suggestions too readily, is
a named failure mode; blindness is its control.

## Finding discipline

Every finding carries a severity (`blocker`, `major`, `minor`, `advisory`), a
category, a locus (claim id, argument node id or section), a required action, and
a status. A finding without a locus is an opinion. `blocker` findings prevent
release; they are not negotiable by revision-round exhaustion.

## Verdicts

`pass`, `pass_with_findings`, `fail`, `escalate`. A reviewer that returns `pass`
without recording what it attacked has not reviewed. The hostile reviewer must
produce at least one finding per pass, or an explicit written statement of what it
attacked and what survived.

## What reviewers must not do

* Rewrite the argument. Findings describe the defect; the Argument Architect fixes
  it.
* Approve their own prior output.
* Downgrade a `blocker` to close a loop.
