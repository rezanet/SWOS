# T070 acquisition record — 2026-09-03

Status: `READY_FOR_HUMAN_ANNOTATION`; T070 remains open and Research Grade is
not certified. This record describes a pre-annotation candidate set only.

## Pinned source acquisition

- Elsevier OA CC-BY Corpus v2, DOI `10.17632/zm33cdndxs.2`:
  `https://elsevier.digitalcommonsdata.com/datasets/zm33cdndxs/2`
- Exact archive route used:
  `https://elsevier.digitalcommonsdata.com/public-api/zip/zm33cdndxs/download/2`
- Acquired archive SHA-256:
  `877ac30109eb1333965a1c912e7e1b7b422542990cdc5b4658feb8d978d5bce2`
- Open Library of Humanities article API:
  `https://olh.openlibhums.org/api/articles/`
- Article-level OLH XML galleys were fetched only when the official article API
  returned `CC BY 4.0`. Every source retains its article rights URI, exact
  licence URI/version, attribution, exact acquired-copy URI, SHA-256, and a
  third-party-rights warning.

The bulk archive and acquired article copies are machine-local under
`C:\GitHub\SWOS-t070-acquisition-cache`; no raw source bytes are committed.

## Prepared candidate set

- 536 unique pending source families: 328 Elsevier and 208 OLH.
- 1,200 source-authored claim families and exactly 6,000 candidate pairs.
- 665–670 candidates per supported discipline.
- Exactly 1,200 candidates in each acquisition stratum: direct candidate,
  partial candidate, same-topic/context, contradiction candidate, and hard
  negative.
- Semantic partitions: 4,875 in-domain, 915 temporal, and 210 OOD. Temporal
  membership uses the predeclared rule `publication_year <= 2015`; OOD requires
  a named catalog-declared held-out domain. Hashing balances in-domain groups
  only and defines neither temporal nor OOD membership.
- 1,200 isolated canonical claim groups; no group crosses a semantic partition
  or generated split.
- 0 support labels, 0 annotator identities, and 0 adjudications are present.
  Each packet reserves two blank independent annotation records and one blank
  independent-adjudication record.

## Human and release boundary

All 536 sources are `ADMISSIBLE_PENDING_REVIEW`, never `APPROVED`. All 6,000
packets are unlabelled candidates, not evaluation truth. Independent source-rights
review, two competent independent annotators per pair, independent adjudication,
locked-test construction, and the remaining Research Grade release gates are
still required. T073 must not start from this candidate set.

Machine-readable details and output digests are in
`acquisition-report.json`; the source and packet contracts are in the two v2
schemas under `schemas/research-grade/`.
