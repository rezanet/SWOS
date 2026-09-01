# SWOS Research Grade citation-support model card

Status: `NOT_RUN` for the release model in this checkout. The model, calibration,
locked-test predictions, human adjudication, and external approval are not
available here; no model quality or release gate is claimed.

The contract is a five-class claim/exact-passage classifier: `directly_supports`,
`partially_supports`, `context_only`, `contradicts`, and `not_supported`.
Inputs are bounded to the claim, exact quote, context, discipline/method IRIs,
source role, and provenance. Provider, publisher prestige, citation count, and
admission outcome are prohibited predictive features.

Deterministic existence, metadata, rights, quote/span, retraction, and provenance
checks run first. Temperature scaling and selective thresholds are bound to the
model, dataset, ontology, and label-order digests. Invalid, uncertain, corrupt,
out-of-distribution, or unsupported-version inputs abstain. Only a calibrated,
non-abstained `directly_supports` decision that passes the core checks can enter
verified evidence; predictions are immutable evidence and overrides are separate
SDL records.

The required release floor is 6,000 reviewed pairs, a 1,500-pair locked test,
per-label/per-discipline minima, grouped work/claim splits, two independent
annotations, adjudication, and explicit source licences. Release gates include
macro-F1 >= 0.85, contradiction recall >= 0.95, ECE <= 0.05, selective error <=
0.02, selective coverage >= 0.70, direct precision safety bounds, and 100%
laundering/invalid-citation rejection. These values remain unverified until the
immutable corpus and locked evaluation are supplied.

Prohibited uses: autonomous source admission from an unverified prediction,
publisher/provider prestige scoring, unsupported citation laundering, identity
or originality claims, and treating an abstention as a negative scholarly label.
