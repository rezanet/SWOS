# Citation Audit

**Auditor:** Citation Auditor v1.0.0 · **Completed:** 2026-01-06T12:05:00Z

## Summary

| Check | Result |
|---|---|
| Citations checked | 5 claim-citation pairs across 3 sources |
| Existence verified | 3 of 3 (100%) |
| Metadata verified | 3 of 3, all fields matched |
| Retraction checked | 3 of 3, all clean |
| Quotations verified | 4 of 4 exact match within excerpt limits |
| Fabricated references | 0 |
| **Unresolved laundering risks** | **0** |
| Invalid citations | 0 |

## Support classification

| Claim | Source | Support level | Note |
|---|---|---|---|
| clm-00000001 | [synthetic] Urban cohort study, p. 6 Table 2 | `directly_supports` | Passage states exactly the bounded association claimed |
| **clm-00000002** | [synthetic] Urban cohort study, p. 6 Table 2 | **`partially_supports`** | **See below** |
| clm-00000002 | [synthetic] Rural replication, p. 11 | `contradicts` | Recorded as counter-evidence |
| clm-00000003 | [synthetic] Urban cohort study, p. 4 Methods | `directly_supports` | Design statement licenses the assessment |
| clm-00000003 | [synthetic] Rural replication, p. 11 | `directly_supports` | |
| clm-00000003 | [synthetic] Narrative review, p. 2 | `context_only` | **Contributes no support** |

## The `partially_supports` classification on clm-00000002

This is the audit's substantive finding, and it is recorded here because it is the
case that most easily passes unnoticed.

The claim was *"Intervention X causes improved outcomes in older adults
generally."* The citation is real, the DOI resolves, the metadata is correct, the
source is not retracted, the venue is appropriate, and the topic is directly on
point. Every check except one passes.

The passage reports an **association**, within **one age band**, in **one urban
cohort**. The claim asserts **causation**, across **older adults generally**. Two
distinct scope failures.

Classifying this `directly_supports` would have been **citation laundering**: a
real, correctly cited, topically adjacent source attached to a claim its passages
do not support. This is precisely why document-level support assertions are
forbidden and support must be classified at passage level.

Recorded as SDL decision `dec-00000002`, reversibility `locked`.

## The `context_only` citation on clm-00000003

The narrative review is relevant background and was consulted. It contributes
**no support**. It is recorded rather than dropped, so the audit shows what was
considered and rejected as support, not only what was accepted.

A claim supported only by `context_only` citations is unsupported. clm-00000003
has two `directly_supports` citations independently of it.
