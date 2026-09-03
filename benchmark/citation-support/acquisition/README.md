# T070 citation candidate acquisition

This directory describes the pre-annotation workflow. Its outputs are not the
approved final source manifest and cannot be promoted into the frozen citation
corpus without independent source-rights review, two competent annotators per
pair, and an independent adjudicator.

The workflow is deliberately resumable and keeps acquired source bytes outside
the repository by default. Use a machine-local cache directory for `--out-dir`;
commit the small manifests, reports, and unlabelled packets only when the
project owner has approved their storage and redistribution terms.

Example:

```powershell
python tools/prepare_t070_catalog.py `
  --elsevier-archive C:\path\to\zm33cdndxs-v2.zip `
  --cache-dir C:\path\to\swos-t070-cache `
  --catalog C:\path\to\citation-source-catalog.json

python tools/acquire_citation_candidates.py `
  --catalog C:\path\to\citation-source-catalog.json `
  --out-dir C:\path\to\swos-t070-cache `
  --max-pairs 6000 `
  --seed 0
```

The catalog must record an exact article-level licence, rights URI, permitted
uses, stable source identity, and a content URI. Only CC BY 4.0, CC0 1.0, and
public-domain records are eligible for acquisition. Unknown, proprietary,
NC/ND, free-to-read, and otherwise unresolved terms are recorded as rejected;
the workflow never turns a dataset-level notice into article-level approval.

Outputs are:

- `source-candidate-manifest.json`: source identity, rights, exact acquired-copy
  URI, bytes hash, rejection state, and pending human approval;
- `unlabelled-candidate-pairs.jsonl`: five-stratum candidate packets with blank
  annotation/adjudication fields and no support labels. Packets carry opaque
  `S1`–`S5` codes; the retrieval-stratum meanings are retained only in the
  acquisition report/tool so annotators cannot infer retrieval intent;
- `acquisition-report.json`: counts, semantic split evidence, cache reuse, and
  the explicit human-review boundary;
- `.acquisition-state.json` and `sources/`: resumable local acquisition cache.

Temporal membership is semantic and predeclared by policy
`T070-TEMPORAL-LATER-YEAR-V1` (`2.0.0`) as
`publication_year >= 2020` when the source is not independently declared OOD.
OOD membership requires an explicit catalog-declared held-out-domain flag and
takes precedence over the date rule. The 2020 boundary was frozen from the
admitted-candidate publication-year histogram and pre-annotation benchmark
viability before annotation; labels and model outcomes were not consulted.
Hashing is used only to balance in-domain groups across train, calibration, and
locked-test; it never defines temporal or OOD membership.

The official Elsevier v2 dataset is an acquisition lead, not automatic release
admission. Pin its version/DOI and exact returned archive, inspect article-level
rights and third-party notices, preserve attribution, and record the resulting
SHA-256 before generating candidates. See the persisted source verification note
at `research/research-grade-external-evidence/T070-SOURCE-VERIFICATION-2026-09-03.md`.
