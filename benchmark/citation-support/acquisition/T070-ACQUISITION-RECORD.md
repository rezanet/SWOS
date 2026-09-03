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
- Semantic policy `2.0.0`, criterion `T070-TEMPORAL-LATER-YEAR-V1`: temporal
  membership uses the predeclared later-window rule
  `publication_year >= 2020 and catalog_declared_held_out_domain is not true`.
  OOD requires a named catalog-declared held-out domain and takes precedence
  over the date rule. Hashing balances in-domain groups only and defines
  neither temporal nor OOD membership.
- The frozen publication-year histogram for the 536 admitted source families is:
  `2014: 27`, `2015: 51`, `2016: 60`, `2017: 45`, `2018: 112`, `2019: 91`,
  `2020: 34`, `2021: 11`, `2022: 13`, `2023: 12`, `2024: 16`, `2025: 36`,
  `2026: 28`.
- The 2020 boundary was selected from corpus availability and pre-annotation
  benchmark viability only: 380 in-domain source families / 899 claim families
  / 4,495 pairs; 149 temporal source families / 252 claim families / 1,260
  pairs; and 7 OOD source families / 49 claim families / 245 pairs. It retains a
  useful later holdout while leaving substantial in-domain material for train,
  calibration, and locked-test. No human labels or model performance were
  consulted, and changing the boundary requires a new semantic policy version.
- Pair counts by discipline `(in_domain, temporal, ood)` are: art_criticism
  `(385, 285, 0)`, art_history `(505, 165, 0)`, engineering `(625, 45, 0)`,
  humanities `(440, 225, 0)`, interdisciplinary `(565, 100, 0)`,
  materials_science `(610, 55, 0)`, philosophy `(485, 180, 0)`, psychology
  `(530, 135, 0)`, and technical_writing `(350, 70, 245)`. Each stratum S1–S5
  has `(899, 252, 49)` pairs in `(in_domain, temporal, ood)`.
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
