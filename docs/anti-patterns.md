# Forbidden Anti-Patterns

Normative prohibitions. Each names where it is prevented.

| # | Anti-pattern | Prevented by |
|---|---|---|
| 1 | One giant prompt pretending to be architecture | Rule #1 and #2; contract-first repository structure; PR review |
| 2 | Draft-first workflows | Rule #3; state transition `argument_constructed -> draft_generated` |
| 3 | Citations added after writing | Drafting reads only from the verified Evidence Matrix |
| 4 | "Critical analysis" without an argument graph | Argument Graph required before `draft_generated` |
| 5 | One discipline rubric for all disciplines | Nine discipline packs, each with its own hierarchy and proof standard |
| 6 | No distinction between fact, inference and interpretation | Epistemic typology; `epistemic_type` is a required field |
| 7 | Reviewer agents with no pass/fail criteria | Every reviewer pack declares test, pass, fail and escalation criteria |
| 8 | Unlimited self-refinement loops | Iteration cap of 3, enforced in the schema (`maximum: 3`) |
| 9 | Unverified memory writes | Memory-write policy: EPG support, SDL rationale, owner, expiry |
| 10 | Raw sensitive data in memory | Data-classification policy; metadata-first audit model |
| 11 | Hidden source gaps | Coverage report; source-diversity index; declared access gaps |
| 12 | Style polish masking weak evidence | Editor contract forbids meaning change; every edit diffed against the matrix |
| 13 | False originality claims | Prior-art search; genealogy; Adversarial Reviewer novelty check |
| 14 | Confidence language without evidence | Contract section 8; confidence language requires high confidence from independent sources |

## The failure modes these produce

Left unchecked, the anti-patterns above produce a specific and well-documented set
of failures: false originality, citation laundering, coverage bias,
over-association, method blindness, interpretive flattening, tacit judgement gaps,
evaluation gaming and automation anchoring.

Every one of these is in the risk register with a named control and a named
detection method. See [`governance/risk-register.md`](../governance/risk-register.md).

## The meta-anti-pattern

**Governance theatre**: controls that are documented, respected in principle, and
never actually block anything.

Its detection signal is unusual and worth stating plainly: a release history
containing **zero blocked releases** is evidence of failure, not success. Either
the gates are not gating, or the thresholds are set where nothing can fail them.
