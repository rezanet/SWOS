---
pack: swos-discipline-materials-science
version: 1.0.0
discipline: materials_science
---

# Discipline Pack: Materials Science

## 1. Reasoning module

Structure-property-processing-performance reasoning. Every claim about a material's behaviour must be traceable through the tetrahedron: how it was made, what structure resulted, what property that structure produces, and how it performs in service. A claim that skips a vertex is an unsupported leap.

## 2. Evidence hierarchy

Characterised experimental studies reporting synthesis route, microstructure and measurement conditions outrank modelling studies without experimental validation. Standards-body test data outrank vendor datasheets. A property reported without its measurement conditions is not evidence; it is a number.

## 3. Proof standard

A materials claim is discharged when the processing route, the resulting microstructure, the characterisation method and the measurement conditions are stated, and the proposed mechanism is consistent with all four. **Property values without conditions do not discharge anything.**

## 4. Required analysis moves

* State the materials class and specific composition
* State the synthesis or processing route including thermal history
* State the resulting microstructure and the characterisation method that established it
* State measurement conditions for every property value: temperature, atmosphere, rate, geometry
* Propose a mechanism linking structure to property
* State the property trade-offs the route imposes
* Report uncertainty, sample count and batch variability
* Distinguish laboratory performance from service performance

An output in this discipline that omits a required move is incomplete regardless
of how well written it is.

## 5. Failure modes

* Property cited without measurement conditions
* Structure-property link asserted with no characterisation evidence
* Modelling result presented as measured behaviour
* Ignoring the trade-off: reporting the improved property, omitting what degraded
* Extrapolating from a single batch
* Transferring a mechanism across a materials class boundary without justification

## 6. Rubric

| Dimension | Weight | Pass threshold |
|---|---|---|
| Processing route completeness | 0.15 | Route and thermal history stated |
| Structure characterisation | 0.20 | Method stated; structure evidenced |
| Property reporting rigour | 0.20 | All conditions stated |
| Mechanism plausibility | 0.20 | Mechanism consistent with structure and processing |
| Trade-off treatment | 0.15 | Degraded properties reported |
| Uncertainty and variability | 0.10 | Sample count and spread reported |

## 7. Acceptance test

`evals/fixtures/golden/materials-structure-property.json`. **Pass condition:** the output links processing, structure, property and performance explicitly, and flags any claim where a vertex of the tetrahedron is missing.

