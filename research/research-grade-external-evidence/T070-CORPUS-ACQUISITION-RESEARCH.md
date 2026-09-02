# T070 Corpus Acquisition Research — SWOS Research Grade

Status: RESEARCH HANDOFF / NOT RELEASE EVIDENCE
Baseline main SHA: `1f5135969f04a104d4a99764f921d1743d22710f`
Research date: 2026-09-03

This note persists the external research performed for T070 so it does not need to be rediscovered from chat history. It is not an approval, not a completed corpus, and not evidence that T070 has passed.

## Frozen T070 requirements to preserve

T070 requires a licensed, bounded, human-adjudicated claim/exact-passage corpus that passes the existing builder and release floors. The current frozen floors are:

- at least 6,000 adjudicated pairs total;
- at least 600 per support label;
- at least 300 per supported discipline;
- at least 1,500 locked-test pairs;
- at least 150 per label in locked test;
- at least 75 per discipline in locked test;
- at least 300 locked adversarial non-direct pairs.

The five labels are:

- `directly_supports`
- `partially_supports`
- `context_only`
- `contradicts`
- `not_supported`

The nine v2 disciplines are:

- `art_history`
- `art_criticism`
- `engineering`
- `humanities`
- `interdisciplinary`
- `materials_science`
- `philosophy`
- `psychology`
- `technical_writing`

Each pair requires two independent discipline-competent annotations and an independent adjudicator with a rationale. Pair/source identity, stable URI, exact source content SHA-256, licence, permitted split uses and independent source approval must remain explicit.

## Recommendation

Build a purpose-built SWOS corpus rather than treating any existing fact-checking dataset as sufficient.

Recommended working name:

`SWOS Citation Support Corpus v2 — CCBY-6K`

Recommended strategy:

1. use clearly reusable CC BY / CC0 scholarly full text as the evidence-source backbone;
2. generate atomic claim families and bounded candidate passages;
3. deliberately retrieve candidates likely to exercise all five semantic relations;
4. treat those relations only as acquisition strata, never pre-assigned ground-truth labels;
5. double-annotate every pair independently;
6. adjudicate every pair independently;
7. freeze train/calibration/locked-test/temporal/OOD only after provenance, rights and leakage checks pass.

## Recommended source stack

### Primary backbone — Elsevier OA CC-BY Corpus

Dataset: Elsevier OA CC-BY Corpus
DOI: `10.17632/zm33cdndxs.2`
Reference: https://researchcollaborations.elsevier.com/en/datasets/elsevier-oa-cc-by-corpus/

Why use it:

- 40,001 open-access CC-BY full-text articles;
- created specifically to support cross-disciplinary NLP/ML research;
- useful scale for engineering, materials science, psychology, interdisciplinary and some humanities examples;
- full text is preferable to abstract-only sources for exact bounded evidence spans.

Recommended role: primary bulk source, not sole source.

### Primary humanities/art supplement — Open Library of Humanities

Publisher: Open Library of Humanities
Policy: https://olh.openlibhums.org/media/journals/2/OLH_Publisher_Policies_Nov_2022.pdf
Example article with XML/PDF download and CC BY 4.0 licence: https://olh.openlibhums.org/articles/10.16995/olh.6407/

Why use it:

- OLH states that it uses CC BY 4.0;
- articles expose XML/PDF and stable DOI metadata;
- provides better domain material for humanities, art history, art criticism and philosophy than forcing those disciplines into generic science abstracts.

Recommended role: primary source for art/humanities/philosophy coverage.

### Controlled supplements

#### MDPI

Rights: https://www.mdpi.com/authors/rights
Open-access policy: https://www.mdpi.com/about/openaccess

Current MDPI policy states articles are generally CC BY 4.0 and may be reused/text-mined with attribution. Article-level licence and third-party-material notices must still be checked.

Recommended role: recent engineering, materials-science, interdisciplinary and humanities gap-fill.

#### Frontiers

Copyright statement: https://www.frontiersin.org/legal/copyright-statement

Frontiers states that current articles are CC BY 4.0; articles from July 2012 onward are CC BY, with older articles requiring article-level checking. Third-party material can carry separate restrictions.

Recommended role: psychology, interdisciplinary and science gap-fill.

#### PLOS

Current terms: https://plos.org/terms-of-use/
Open-science policies: https://plos.org/open-science-policies/

PLOS states article content is generally CC BY or a comparably unrestricted licence, with attribution.

Recommended role: psychology/interdisciplinary/scientific-reasoning and recent temporal cases.

#### PubMed Central Open Access subset

Current AWS guidance: https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/

PMC divides OA material into `oa_comm`, `oa_noncomm` and other collections. `oa_comm` includes CC BY and CC0 material. For the SWOS core corpus, still verify the actual article-level licence and admit only explicitly permitted copies.

Recommended role: selective psychology/science supplement, not blind bulk import.

## Seed / discovery sources — use with caution

### SciFact

Repository: https://github.com/allenai/scifact
Licence: https://github.com/allenai/scifact/blob/master/LICENSE.md

SciFact claims and evidence annotations are CC BY 4.0, but its abstracts are sourced from S2ORC and licensed at the dataset layer under ODC-By 1.0.

Recommended role:

- seed claims;
- adversarial-pattern inspiration;
- benchmark structure inspiration.

Do not automatically admit SciFact evidence passages into SWOS solely because the annotation layer is CC BY. Establish the underlying scholarly-copy rights independently.

### S2ORC

Repository: https://github.com/allenai/s2orc

Current S2ORC is distributed under ODC-By 1.0 and explicitly asks users to verify that intended usage of the underlying contents is permissible.

Recommended role: discovery only unless the exact underlying scholarly copy has a separately verified permissible licence.

### OpenAlex

Licence reference: https://help.openalex.org/data/licenses/
OpenAlex dataset licence: CC0 (except its separate MAG-format snapshot).

Useful capabilities:

- filter works by location-level `cc-by` or public-domain licence;
- discover candidate papers and exact licensed locations;
- source family and discipline discovery.

Recommended role: discovery/licence triage. OpenAlex metadata is not itself permission to ingest a scholarly full-text copy whose article licence is unclear.

### DOAJ

Terms: https://doaj.org/terms/

DOAJ article/journal metadata is CC0, while copyright in the underlying article remains separate.

Recommended role: discovery and licence metadata cross-checking.

### Crossref / OpenCitations

Crossref metadata guidance: https://www.crossref.org/documentation/retrieve-metadata/
OpenCitations: https://opencitations.net/what-we-do/

Recommended role: bibliographic/citation metadata enrichment and duplicate/source-family checking. Do not treat copyrighted abstracts as unrestricted content merely because bibliographic metadata is open.

## Conservative licence policy for the core corpus

Preferred automatic-admission classes:

- CC BY 4.0 (or an explicitly equivalent unrestricted attribution licence);
- CC0 / public domain;
- clearly documented government/public-domain material where reuse is genuinely unrestricted.

Do not automatically admit:

- `other-oa`;
- `publisher-specific-oa` without reviewing the actual terms;
- CC BY-NC variants;
- CC BY-ND variants;
- standard arXiv licence material without article-level permission;
- database-layer ODC licences where underlying content rights are not established;
- free-to-read material;
- unknown or proprietary material.

CC BY-SA may be legally usable in some circumstances, but the core T070 recommendation is to avoid adding share-alike compatibility questions when sufficient CC BY/CC0 material exists.

For every admitted source, preserve at minimum:

- source ID;
- DOI/stable URI;
- exact acquired file/canonical byte source;
- SHA-256;
- article/work title and authors;
- publisher/source;
- licence name and canonical licence URI/version;
- attribution;
- acquisition timestamp;
- permitted SWOS uses (`train`, `calibration`, `locked_test`, `temporal`, `ood` as applicable);
- independent source/licence approval.

## Proposed 6,000-pair construction

A practical acquisition shape is:

- 1,200 atomic claim families;
- five candidate evidence passages per family;
- 6,000 total pairs.

The five retrieval strata should seek:

1. complete/direct support candidate;
2. partial-support candidate;
3. same-topic/context-only candidate;
4. contradiction candidate;
5. hard negative/not-supported candidate.

These are candidate strata only. Human annotators assign the actual five-class label. If a candidate intended as contradiction is adjudicated as context-only, retain the human label and reacquire another candidate later if needed to meet class floors.

### Discipline allocation

Starting target:

- 120 claim families per each of the nine disciplines = 1,080 claim families / 5,400 pairs;
- 120 additional claim families / 600 pairs reserved for temporal, OOD and especially difficult adversarial coverage.

This gives useful margin above the frozen per-discipline floor because adjudication will change the intended class distribution.

Suggested source emphasis:

| Discipline | Preferred source pool |
| --- | --- |
| art_history | OLH + explicitly CC-BY art/heritage journals + Elsevier Arts & Humanities |
| art_criticism | OLH + openly licensed criticism/critical-theory journals |
| engineering | Elsevier OA CC-BY + MDPI + clearly licensed institutional material |
| humanities | OLH + Elsevier Arts/Social Sciences |
| interdisciplinary | Elsevier cross-disciplinary + PLOS + Frontiers + MDPI |
| materials_science | Elsevier OA CC-BY + MDPI |
| philosophy | OLH + explicitly CC-BY philosophy/humanities journals |
| psychology | Elsevier + Frontiers + PLOS + filtered PMC CC BY/CC0 |
| technical_writing | openly licensed technical/scientific communication scholarship + selected public-domain institutional writing |

## Adversarial cases

The locked 300 adversarial non-direct pairs should attack realistic evidence failures, not trivial topic mismatch.

Priority patterns:

- quantifier inflation (`some` -> `all`);
- modal inflation (`may` -> `does`);
- association -> causation;
- local sample -> whole object/population;
- analytical signal -> compound/material identity;
- method capability -> object-specific assertion;
- non-detection -> absence;
- historical/versioned fact -> present-current fact;
- threshold/range narrowing beyond source support;
- abstract/summary stronger than inspected passage;
- citation laundering where the cited source merely cites another work;
- source supports neighbouring mechanism but not the retained claim.

## Temporal and OOD split issue discovered

The current frozen corpus builder correctly requires five partitions:

- `train`
- `calibration`
- `locked_test`
- `temporal`
- `ood`

and correctly groups by canonical work/claim family to avoid cross-split leakage.

However, the current `grouped_split()` implementation is a deterministic proportion-based assignment of groups. That alone does not make the resulting `temporal` split temporally held out or the `ood` split genuinely out of distribution.

Before freezing T070, verify and, if necessary, correct the execution path so that:

- temporal groups are deliberately selected from a predeclared later publication/acquisition window or other frozen temporal criterion;
- OOD groups are deliberately selected from a predeclared out-of-distribution domain/source/task criterion;
- canonical work and claim families remain isolated across every partition;
- no random/hash assignment can silently turn ordinary in-distribution examples into the semantic temporal/OOD holdouts.

This is an implementation/execution integrity issue, not permission to change the frozen release floors.

## What the builder should automate

Automate as much pre-human work as possible:

- source discovery via OpenAlex/DOAJ/Crossref where useful;
- article-level licence verification and rejection logging;
- downloading only permitted source copies;
- SHA-256 generation;
- bibliographic/source-family canonicalization;
- exact-passage extraction;
- atomic-claim preparation;
- candidate passage retrieval for the five acquisition strata;
- duplicate/edition/mirror detection;
- candidate packet generation for annotators;
- temporal/OOD preassignment using frozen criteria;
- manifest generation;
- post-adjudication leakage and floor reports.

Do not automate away the frozen human requirement:

- two independent annotations per pair;
- independent adjudication with rationale;
- independent dataset/source approval.

At the 6,000-pair floor this means at least 12,000 independent annotation decisions plus 6,000 adjudications. No synthetic or model-generated labels may be counted as that human evidence.

## Immediate next action

Builder should create a source-candidate manifest and acquisition workflow from this source stack, prepare the 6,000 unlabeled candidate pairs, and stop at the human-annotation boundary if genuine reviewers are not yet available.

T070 remains OPEN until actual licensing, annotations, adjudication, approval, leakage checks, frozen splits and release floors pass.