# T070 acquisition record — 2026-09-05

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
  returned `CC BY 4.0`. The 178 admitted OLH source families retain their
  article rights URI, exact licence URI/version, attribution, exact
  acquired-copy URI, SHA-256, and a third-party-rights warning. Each admitted
  OLH DOI is read from the acquired XML article metadata rather than derived
  from the OLH API primary key.
- The Elsevier archive records only the dataset-level `openaccess=Full` marker
  for the selected 315 source records. That marker is retained as an
  unresolved acquisition lead; it is not article-level rights verification.
  The runtime rejects those records before copying source bytes or generating
  packets, pending inspection of each article licence or rights notice.

The bulk archive and acquired article copies are machine-local under
`C:\GitHub\SWOS-t070-acquisition-cache`; no raw source bytes are committed.

## Prepared candidate set

- 493 catalog source records (catalog SHA-256
  `85f2ce90da9f216b321f3f50097511ba439b79d877cca682548f3865869081e4`): 315 Elsevier records with unresolved rights and
  178 OLH source families admissible pending human review. Only the 178
  article-level rights-screened OLH source families enter the packet manifest.
- 1,200 source-authored claim families and exactly 6,000 candidate pairs.
- Candidate pairs by discipline are: art_criticism 825, art_history 905,
  engineering 0, humanities 850, interdisciplinary 875, materials_science 0,
  philosophy 840, psychology 810, and technical_writing 895. Zero-count
  disciplines are reported explicitly because their rights-cleared source
  profiles are not yet available.
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
- The publication-year histogram for the 178 admitted packet source families
  is: `2016: 3`, `2017: 1`, `2018: 26`, `2019: 26`, `2020: 16`,
  `2021: 11`, `2022: 11`, `2023: 10`, `2024: 10`, `2025: 36`, `2026: 28`.
- The 2020 boundary was selected from corpus availability and pre-annotation
  benchmark viability only: 50 in-domain source families / 273 claim families
  / 1,365 pairs; 122 temporal source families / 748 claim families / 3,740
  pairs; and 6 OOD source families / 179 claim families / 895 pairs. It retains a
  useful later holdout while leaving substantial in-domain material for train,
  calibration, and locked-test. No human labels or model performance were
  consulted, and changing the boundary requires a new semantic policy version.
- Pair counts by discipline `(in_domain, temporal, ood)` are: art_criticism
  `(385, 440, 0)`, art_history `(285, 620, 0)`, engineering `(0, 0, 0)`,
  humanities `(0, 850, 0)`, interdisciplinary `(135, 740, 0)`,
  materials_science `(0, 0, 0)`, philosophy `(235, 600, 0)`, psychology
  `(325, 485, 0)`, and technical_writing `(0, 0, 895)`. Each stratum S1–S5
  has `(273, 748, 179)` pairs in `(in_domain, temporal, ood)`.
- 1,200 isolated canonical claim groups; no group crosses a semantic partition
  or generated split.
- 185 candidate families were rejected during deterministic collision checking;
  no duplicate `(source, claim, exact quote)` tuple remains in the emitted set.
- Article XML extraction includes only JATS `abstract` and `body` prose and
  excludes front/back matter before sentence generation.
- 0 support labels, 0 annotator identities, and 0 adjudications are present.
  Each packet reserves two blank independent annotation records and one blank
  independent-adjudication record.

## Human and release boundary

All 178 admitted sources are `ADMISSIBLE_PENDING_REVIEW`, never `APPROVED`; the
315 Elsevier records are `REJECTED_UNRESOLVED_LICENCE` and have no acquired
copy in the packet output. All 6,000 packets are unlabelled candidates, not
evaluation truth. Independent source-rights review, two competent independent
annotators per pair, independent adjudication, locked-test construction, and
the remaining Research Grade release gates are still required. T073
training/calibration/locked evaluation remains fail-closed until those
human-reviewed labelled and locked artefacts exist.

Machine-readable details and output digests are in
`acquisition-report.json`; the source and packet contracts are in the two v2
schemas under `schemas/research-grade/`. The regenerated catalog SHA-256 is
`85f2ce90da9f216b321f3f50097511ba439b79d877cca682548f3865869081e4`.
The regenerated manifest SHA-256 is
`b138e4e03dc3ad3138caec1ec9f2c46c7ef8594fbf73338b0f4580591afbb39b`, and the
unlabelled packet SHA-256 is
`ce4ef919e09c4c95918a3e8ced74764e2e1c7c8f9eb1aac8cf417034dc249433`.
The acquisition report SHA-256 is
`a18b6928cdd51a34985644498de803f3d88652d2004c3d2bd5dec523c5f224eb`.
