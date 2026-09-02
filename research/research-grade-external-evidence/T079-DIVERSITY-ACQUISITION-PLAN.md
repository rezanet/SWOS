# T079 Diversity Packet Acquisition Plan

Status: RESEARCH/PREPARATION ONLY
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`

## Goal

Prepare genuine source-diversity packet candidates for independent human review without marking T079 complete.

Frozen T079 requires separate tuning packets plus at least ten locked human-reviewed packets per each of the nine supported disciplines, using the frozen stress-category set.

## Candidate quantity

Prepare 12 candidate packets per discipline (108 total) to allow human rejection/repair while preserving the >=10 locked floor.

Do not multiply the required packet count by category. Instead distribute the 12 candidates so each discipline exercises the category set across the cohort.

Suggested 12-packet pattern per discipline:

- 2 balanced/adequate controls;
- 2 concentrated cases;
- 1 sparse case;
- 1 legitimate narrow-corpus case;
- 1 multilingual case;
- 1 historical/period-skew case;
- 1 method-monoculture case;
- 1 duplicate-edition/mirror case;
- 1 provider-renaming/fake-diversity case;
- 1 mixed hard case combining unknown metadata + missing required strata.

These are generator intentions, not human truth labels.

## Data sources

Prefer open metadata:

- OpenAlex CC0 dataset: https://github.com/ourresearch/openalex-docs/blob/main/license.md
- OpenAlex licence vocabulary: https://help.openalex.org/data/licenses/
- Crossref bibliographic metadata: https://www.crossref.org/documentation/retrieve-metadata/
- OpenCitations CC0: https://opencitations.net/what-we-do/
- DOAJ CC0 article/journal metadata: https://doaj.org/terms/

Do not ingest copyrighted abstracts merely because bibliographic metadata is open.

## Per-source-family fields

Preserve:

- source/family IDs;
- DOI/ISBN/canonical work identifier;
- title;
- author/institution cluster;
- publisher/owner;
- venue;
- geography/jurisdiction;
- language;
- publication year/period;
- methodology;
- source type;
- access mode;
- stance/source role;
- retrieval provider(s) as provenance only;
- metadata evidence state (`observed`, `externally_verified`, `inferred`, `unknown`);
- exact metadata-source URI and acquisition date.

Duplicate editions, mirrors, preprints/finals and provider copies that belong to one canonical work family must remain one family for the diversity gate.

## Packet preparation rules

Each packet should contain:

- discipline;
- research question;
- frozen pre-retrieval diversity requirement;
- candidate source-family records;
- admitted-claim/source edges used for claim-exposure measurement;
- intended stress condition;
- machine-computed source-count and claim-exposure distributions;
- machine prediction of expected gap/status;
- blank independent reviewer fields;
- immutable source and packet digests.

The machine prediction is diagnostic only. The reviewer determines the locked expected material gaps and adequacy outcome.

## Human review boundary

Independent reviewer must record:

- reviewer identity;
- packet digest;
- whether source-family canonicalization is correct;
- whether metadata evidence states are justified;
- material gaps actually present;
- whether a narrow-corpus exception is justified;
- expected benchmark outcome;
- rationale;
- disposition.

The builder must not fill these fields itself.

## Completion boundary

This plan can produce T079 candidate packets, but T079 remains OPEN until at least ten packets per discipline are genuinely reviewed, locked, manifest-bound and independently approved.