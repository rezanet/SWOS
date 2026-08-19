# Reviewer Packs

**"Review this critically" is not a specification.** Every reviewer is a named
role with explicit test, pass, fail and escalation criteria.

| Role | Tests |
|---|---|
| [Citation auditor](citation-auditor.md) | Fabricated references, wrong metadata, citation laundering |
| [Methodologist](methodologist.md) | Study design, bias, construct validity, statistical overreach |
| [Argument examiner](argument-examiner.md) | Warrant strength, hidden premises, circular reasoning, rebuttals |
| [Discipline expert](discipline-expert.md) | Field norms, missing literature, discipline proof standards |
| [Hostile reviewer](hostile-reviewer.md) | The weakest load-bearing part of the thesis |
| [Editor](editor.md) | Structure, voice, concision, genre fit - without changing meaning |
| [Governance reviewer](governance-reviewer.md) | Data handling, disclosure, audit completeness, policy |

## Bounded loops

**Iteration cap: 3.** On the fourth pass, escalate to a human.

Group-chat and maker-checker orchestration patterns need clear acceptance
criteria, iteration caps and escalation behaviour, or they refine indefinitely.
Unlimited self-refinement is a forbidden anti-pattern: it converts unresolved
disagreement into fluency, which is exactly the failure SWOS exists to prevent.

## Blind review

The hostile reviewer and argument examiner run blind where the host supports it -
without prior AI suggestions or earlier verdicts in context. **Automation
anchoring**, where reviewers accept polished suggestions too readily, is a named
failure mode; blindness is its control. Adapters that cannot fork context declare
`blind_review: unsupported`, and the resulting risk is recorded in the SDL rather
than ignored.

## No self-review

No reviewer may review its own prior output. The Citation Auditor does not audit
citations it introduced; the Editor does not clear its own edits.
