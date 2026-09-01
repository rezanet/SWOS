# Citation-support dataset card

The release corpus is a grouped claim-span dataset for the nine v2 discipline
profiles. Groups are canonical work plus claim family, so editions, mirrors,
preprints, and paraphrases cannot cross train, calibration, locked-test,
temporal, or OOD splits. The release floor is 6,000 adjudicated pairs, 600 per
label, 300 per discipline, with a locked test of 1,500 pairs including 300
adversarial non-direct cases. Counts are release gates, not targets to be
filled with synthetic rows.

The current checkout records corpus acquisition and human adjudication as
`NOT_RUN` until licensed source manifests and independent review are supplied.
