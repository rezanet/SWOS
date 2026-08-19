---
pack: swos-discipline-psychology
version: 1.0.0
discipline: psychology
---

# Discipline Pack: Psychology

## 1. Reasoning module

Method and evidence appraisal. The central question is not what a study found but what its design licenses it to claim. Sample, measurement, power, confounds and analytic flexibility determine the size of the claim the evidence can carry.

## 2. Evidence hierarchy

Pre-registered replications and well-powered multi-site studies outrank single laboratory studies. Meta-analyses outrank narrative reviews, but only where heterogeneity is reported. Single studies with small samples are weak evidence irrespective of p-value or journal. Effect sizes with confidence intervals outrank significance statements at every tier.

## 3. Proof standard

An empirical psychological claim is discharged by evidence from a design capable of supporting it, at adequate power, with a validated measure of the construct actually named, and with the causal language matched to the design. **Correlational designs never discharge causal claims.**

## 4. Required analysis moves

* State the construct and the measure, and whether the measure is validated for that construct
* Report sample size, composition and the population to which it generalises
* Report effect size and confidence interval, not significance alone
* Identify plausible confounds
* Match causal language to design; qualify explicitly where the design is correlational
* Note replication status and any known failed replications
* Flag analytic flexibility, multiple comparisons and outcome switching where visible
* State ethical constraints where the design bears on them

An output in this discipline that omits a required move is incomplete regardless
of how well written it is.

## 5. Failure modes

* Causal overreach: an association reported as an effect
* Construct drift: measuring one thing, claiming another
* Generalisation beyond the sampled population, especially across culture and age
* Significance-only reporting that hides a trivial effect size
* Citing a single striking study without its replication record
* Treating a meta-analysis as authoritative without checking heterogeneity or publication bias

## 6. Rubric

| Dimension | Weight | Pass threshold |
|---|---|---|
| Construct and measurement validity | 0.20 | Measure named and validated for the construct |
| Sampling and generalisation | 0.15 | Population stated; over-generalisation absent |
| Statistical interpretation | 0.20 | Effect sizes and intervals reported |
| Causal-claim licensing | 0.25 | Zero unlicensed causal claims |
| Confound and bias identification | 0.10 | Plausible confounds named |
| Replication awareness | 0.10 | Replication status stated for load-bearing findings |

## 7. Acceptance test

`evals/fixtures/golden/psychology-method-critique.json`. **Pass condition:** the output flags weak measurement, sampling limits and causal overreach in the supplied study, rather than reporting its headline finding.

