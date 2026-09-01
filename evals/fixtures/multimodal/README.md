# Multimodal evaluation corpus

`manifest.json` records the release minima and the current corpus status. It is
intentionally `not_run` in this checkout because no checksummed, rights-cleared
and human-reviewed corpus has been supplied. The evaluator must not manufacture
cases to satisfy the minima.

A future `ready` manifest must enumerate cases through the production
`ImageAnalysisProvider` interface and include the per-asset rights and
attribution records described in `DATA-LICENCE.md`. The required strata are
object/work identity, six media/material classes, three mediation conditions,
both art disciplines, regions, cross-modal support, accessibility, and
adversarial invented-detail/originality/over-association cases.
