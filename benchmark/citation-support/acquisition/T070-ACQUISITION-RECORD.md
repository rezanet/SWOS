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

- 517 unique pending source families: 321 Elsevier and 196 OLH.
- 1,200 source-authored claim families and exactly 6,000 candidate pairs.
- Candidate pairs by discipline are: art_criticism 675, art_history 625,
  engineering 675, humanities 655, interdisciplinary 655, materials_science
  700, philosophy 650, psychology 650, and technical_writing 705.
- Exactly 1,200 candidates in each acquisition stratum: direct candidate,
  partial candidate, same-topic/context, contradiction candidate, and hard
  negative.
- Semantic policy `2.0.0`, criterion `T070-TEMPORAL-LATER-YEAR-V1`: temporal
  membership uses the predeclared later-window rule
  `publication_year >= 2020 and catalog_declared_held_out_domain is not true`.
  OOD is the complete predeclared `technical_writing` domain
  (`technical-writing-held-out-v1`) and takes precedence over the date rule;
  it is not an ordinal or hash bucket. Hashing balances in-domain groups only
  and defines neither temporal nor OOD membership.
- Discipline assignment uses `T070-DISCIPLINE-SOURCE-METADATA-V1`: official
  source subject metadata plus auditable title/keyword/section/abstract
  evidence. Each assignment records the fields inspected, discipline rule
  terms, matched terms, matched subject codes, and any explicit corpus-scope
  fallback; unresolved Elsevier `ARTS` records are excluded rather than being
  assigned to `art_history`. Every assignment remains pending human review.
- The frozen publication-year histogram for the 517 admitted source families is:
  `2014: 27`, `2015: 46`, `2016: 56`, `2017: 45`, `2018: 101`, `2019: 97`,
  `2020: 33`, `2021: 11`, `2022: 12`, `2023: 11`, `2024: 14`, `2025: 36`,
  `2026: 28`.
- The 2020 boundary was selected from corpus availability and pre-annotation
  benchmark viability only: 366 in-domain source families / 814 claim families
  / 4,070 pairs; 145 temporal source families / 245 claim families / 1,225
  pairs; and 6 OOD source families / 141 claim families / 705 pairs. It retains a
  useful later holdout while leaving substantial in-domain material for train,
  calibration, and locked-test. No human labels or model performance were
  consulted, and changing the boundary requires a new semantic policy version.
- Pair counts by discipline `(in_domain, temporal, ood)` are: art_criticism
  `(425, 260, 0)`, art_history `(400, 225, 0)`, engineering `(630, 45, 0)`,
  humanities `(395, 260, 0)`, interdisciplinary `(560, 95, 0)`,
  materials_science `(640, 60, 0)`, philosophy `(490, 160, 0)`, psychology
  `(530, 120, 0)`, and technical_writing `(0, 0, 705)`. Each stratum S1–S5
  has `(814, 245, 141)` pairs in `(in_domain, temporal, ood)`.
- 1,200 isolated canonical claim groups; no group crosses a semantic partition
  or generated split.
- 0 support labels, 0 annotator identities, and 0 adjudications are present.
  Each packet reserves two blank independent annotation records and one blank
  independent-adjudication record.

## Human and release boundary

All 517 sources are `ADMISSIBLE_PENDING_REVIEW`, never `APPROVED`. All 6,000
packets are unlabelled candidates, not evaluation truth. Independent source-rights
review, two competent independent annotators per pair, independent adjudication,
locked-test construction, and the remaining Research Grade release gates are
still required. T073 training/calibration/locked evaluation remains fail-closed
until those human-reviewed labelled and locked artefacts exist.

Machine-readable details and output digests are in
`acquisition-report.json`; the source and packet contracts are in the two v2
schemas under `schemas/research-grade/`.
