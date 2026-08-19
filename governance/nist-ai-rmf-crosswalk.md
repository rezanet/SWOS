# NIST AI RMF 1.0 Crosswalk

The AI RMF Core organises into four functions - **Govern, Map, Measure and
Manage** - with **Govern** designed as a cross-cutting function infused
throughout the other three. SWOS adopts that framing directly and uses the
category numbering as an audit map.

## GOVERN (cross-cutting)

| RMF category | SWOS implementation |
|---|---|
| GOVERN 1.1-1.2 - policies and legal requirements | `governance/policy-model.md`, `source-rights-policy.md`, policy-as-code with default deny |
| GOVERN 1.3 - risk management processes | `risk-register.md`, eight named risks with controls and detection |
| GOVERN 2.1-2.3 - accountability structures | `GOVERNANCE.md` roles; separation of contract and evaluation owners; `access-model.md` separation of duties |
| GOVERN 3.2 - human oversight | `approval-matrix.md`; human accountability for final judgement as an operating principle |
| GOVERN 4.1-4.3 - safety-first culture, information sharing | `incident-and-correction.md`; every high incident closes with an evaluation fixture |
| GOVERN 5.1-5.2 - external feedback | Reviewer findings, contributor governance, public schemas and rubrics |
| GOVERN 6.1-6.2 - third-party risk | Connector due diligence in `source-rights-policy.md`; tool registry with declared egress |

## MAP

| RMF category | SWOS implementation |
|---|---|
| MAP 1.1-1.6 - context established | Intake and classification stage; input contract; discipline pack selection |
| MAP 2.1-2.3 - categorisation, capabilities, scope | Work classifier; contribution type; capability matrices per adapter |
| MAP 3.1-3.5 - benefits and costs | Evidence budget; abstention rules; declared coverage limits |
| MAP 4.1-4.2 - third-party and IP risks | Source-rights gate; licence checks before store and export |
| MAP 5.1-5.2 - impact characterisation | Data classification; approval matrix; disclosure requirements |

## MEASURE

| RMF category | SWOS implementation |
|---|---|
| MEASURE 1.1-1.3 - methods identified and applied | Eight-plane evaluation harness; `contracts/evaluation-contract/` |
| MEASURE 2.1-2.3 - test sets and evaluation | Golden, adversarial and regression fixtures; hidden sets |
| MEASURE 2.5-2.7 - validity, reliability, security | Retrieval, grounding and citation planes; injection-resistance testing |
| MEASURE 2.8-2.10 - transparency, privacy | Provenance completeness; metadata-first audit; disclosure text |
| MEASURE 2.11-2.13 - fairness and effectiveness | Source diversity index; coverage-bias controls; minority-position retrieval |
| MEASURE 3.1-3.3 - tracking over time | Regression plane; baseline comparison; drift monitoring |
| MEASURE 4.1-4.3 - feedback from domain experts | Pairwise expert review; rotating rubrics; discipline steward review |

## MANAGE

| RMF category | SWOS implementation |
|---|---|
| MANAGE 1.1-1.4 - risk prioritisation and response | Risk register severity; blocker findings; release gate |
| MANAGE 2.1-2.4 - resource allocation, deactivation | Retirement checklist; supersession; rollback in the release playbook |
| MANAGE 3.1-3.2 - third-party risks managed | Connector risk assessment; egress allow-lists |
| MANAGE 4.1-4.3 - monitoring, recovery, communication | Operate-phase telemetry; incident and correction workflow; downstream notification via EPG blast-radius query |

## Using this as an audit map

An auditor asking "how does this system discharge MEASURE 2.7?" gets a specific
answer: the citation and adversarial planes, their fixtures, their thresholds, and
the Governance Gate records showing the result of each run. Every gate record
carries its `nist_ai_rmf_refs` for exactly this purpose.
