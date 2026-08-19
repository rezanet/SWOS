# Research Plan

**Work id:** work-4f3a91c2 · **State at creation:** `planned` · **Discipline:** psychology
**Contribution type:** critique · **Audience:** researchers · **Classification:** public

## Primary research question

Does the available evidence support a **causal** claim that intervention X improves
outcome Y in older adults?

## Sub-questions

1. What designs exist in this literature, and what do they license?
2. What is the sampled population in each study, and how far does it generalise?
3. Have the primary findings been replicated, and in what populations?
4. What opposing or null results exist?

## Scope

**In scope:** adults aged 65+, studies from 2015 onward, any design.
**Out of scope:** adults under 65 (imports evidence answering a different
question); animal models (domain transfer risk not justifiable for this question).

## Evidence standard

Psychology discipline pack. A causal claim is discharged only by a design capable
of supporting it, at adequate power, with a validated measure of the named
construct. **Correlational designs never discharge causal claims.**

## Search strategy

| Component | Detail |
|---|---|
| Corpora | OpenAlex (open scholarly index) |
| Primary queries | intervention X + outcome Y + older adults |
| **Counter-evidence queries** | intervention X + (null result OR failed replication OR no effect) - run as a **separate named step** |
| Seminal-work walk | Backward and forward citation traversal from the highest-cited primary study |
| Date bounds | 2015 onward |
| Languages reached | English only |
| Access | Open access only in this run |

## Declared coverage limits

Stated **in advance**, per the coverage-bias control:

* English-language only. Non-English literature on this intervention is not reached.
* Open access only. Subscription-only literature is not reached; it will be cited
  from metadata if identified but cannot be passage-verified.
* Two regions expected to dominate (North America, Western Europe).

Coverage limits declared in advance are scholarship. Discovered afterwards they
are excuses.

## Evidence budget

| Epistemic type | Requirement before assertion |
|---|---|
| `observed_fact` | One primary source, passage-level span |
| `source_backed_claim` | One source at `directly_supports` |
| Causal claim | A design licensing causation **plus** replication |
| `critical_assessment` | Two independent sources |

## Rival thesis candidates

1. Intervention X causes improved outcomes in older adults.
2. Intervention X has no effect.
3. The effect is real but population-bounded.

## Known uncertainties, declared before evidence gathering

* `method_uncertainty` - the literature is expected to be predominantly
  observational.
* `domain_transfer_risk` - findings may be bounded to specific cohorts.
* `source_bias` - open-access-only retrieval may skew the evidence base.

## Reviewer plan

Citation auditor, methodologist (**mandatory** - the question is a design-licensing
question), argument examiner, discipline expert (psychology), hostile reviewer.
