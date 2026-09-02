# T079 Verified Metadata Source Registry

Status: RESEARCH/PREPARATION ONLY
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`
Verified: 2026-09-03

This registry records source-level rights and suitability research for preparing T079 diversity packets. It is not human review and does not complete T079.

## OpenAlex

Use: primary discovery and structured source-family metadata substrate.

Verified points:

- OpenAlex states that its dataset is released under CC0/public-domain terms.
- OpenAlex licences are location-specific: each scholarly copy can carry its own licence.
- `cc-by`, `public-domain`, and other explicit licence values are distinguishable from catch-all `other-oa` and `publisher-specific-oa`.
- OpenAlex full-text PDFs retain their original copyright; OpenAlex does not grant additional rights to the PDF/content.

Operational rule:

Use OpenAlex metadata for T079 freely. Do not treat OpenAlex metadata licensing as permission to copy underlying article text. For any later full-text use, bind the exact location/copy and its actual licence separately.

Authoritative references:

- https://help.openalex.org/data/how-its-built/
- https://help.openalex.org/data/licenses/
- https://help.openalex.org/access/fulltext/

## Crossref

Use: DOI identity, bibliographic metadata, publisher/venue/year, references, licence metadata where deposited.

Verified points:

- Crossref states that almost all bibliographic metadata is reusable without restriction.
- Crossref-generated data is CC0/public domain.
- Bibliographic metadata including references is treated as factual metadata.
- Abstracts remain under publisher/author copyright and are not automatically reusable merely because Crossref distributes them.

Operational rule:

Use Crossref bibliographic/reference metadata in T079 packet construction. Do not ingest abstracts into the T079 evidence corpus unless the underlying abstract/article licence separately permits it.

Authoritative references:

- https://www.crossref.org/documentation/retrieve-metadata/
- https://www.crossref.org/documentation/retrieve-metadata/rest-api/

## OpenCitations

Use: citation-network metadata and independent citation-edge corroboration.

Verified points:

- OpenCitations states that data in its datasets is available under CC0.
- Website text is CC BY 4.0; software is ISC licensed.

Operational rule:

Use OpenCitations citation metadata to test source-family/citation diversity and to construct stress packets. Provider count remains provenance only and must never improve the diversity gate.

Authoritative reference:

- https://opencitations.net/what-we-do/

## DOAJ

Use: journal/article OA metadata and licence discovery/corroboration.

Verified points:

- DOAJ journal-level and article-level metadata are available under CC0.

Operational rule:

Use DOAJ metadata freely for packet construction. Treat the licence field as metadata about the article, not a substitute for verifying the actual content copy when copyrighted text is later required.

Authoritative reference:

- https://doaj.org/terms/

## T079 acquisition policy

For the 108 candidate packet target:

1. discover candidate works through OpenAlex;
2. reconcile DOI/venue/publisher/year via Crossref;
3. enrich citation graph and duplicate/family stress cases with OpenCitations;
4. corroborate OA/journal licence metadata with DOAJ where relevant;
5. canonicalize editions, mirrors, preprints/finals and provider copies into source families before diversity scoring;
6. record metadata evidence state as `observed`, `externally_verified`, `inferred`, or `unknown`;
7. never let `inferred` or `unknown` metadata improve a score;
8. keep provider identity provenance-only;
9. preserve all machine-generated expected outcomes as diagnostic only until independent human review locks each packet.

## Human boundary

This registry makes automated packet preparation legally and technically clearer. It does not satisfy the T079 requirement for genuine independent human review of at least ten locked packets per discipline.