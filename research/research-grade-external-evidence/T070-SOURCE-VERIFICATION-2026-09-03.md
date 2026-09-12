# T070 source verification — 2026-09-03

Status: bounded primary-source check only. No corpus files, labels, manifests, approvals, or T070 task markers were created or changed.

## Elsevier OA CC-BY Corpus, DOI `10.17632/zm33cdndxs.2`

The [Elsevier Research Collaborations record](https://researchcollaborations.elsevier.com/en/datasets/elsevier-oa-cc-by-corpus/) identifies the dataset as version 2, published 4 August 2020, with 40,001 OA CC-BY articles and the DOI `10.17632/zm33cdndxs.2`. The [Elsevier Data Repository record](https://elsevier.digitalcommonsdata.com/datasets/zm33cdndxs/2) repeats the version/DOI and displays `Licence: CC BY 4.0` and a `Download All` control. The current page-generated archive route is `https://elsevier.digitalcommonsdata.com/public-api/zip/zm33cdndxs/download/2`; the repository also points users to the [Mendeley Data API documentation](https://data.mendeley.com/api/docs/).

This establishes a credible acquisition lead, not admission of every byte into SWOS. The public record exposed the dataset-level licence and download control, but this check did not download the archive or independently observe a stable file inventory, per-file hashes, article DOI list, or article-level notices. The [Elsevier website terms](https://www.elsevier.com/legal/elsevier-website-terms-and-conditions) reserve rights in service content and state that open-access material is governed by the relevant licensing terms. Therefore acquisition must pin the exact returned version/copy, hash the acquired bytes, inspect each article and embedded third-party component, preserve attribution, and reject any item whose article-level reuse rights are unclear. The [CC BY 4.0 deed](https://creativecommons.org/licenses/by/4.0/) is the canonical licence reference; the repository label alone is not independent approval for the SWOS release corpus.

## Open Library of Humanities (OLH)

The [OLH Publisher Policies, revised March 2023](https://olh.openlibhums.org/media/journals/2/OLH_Publisher_Policies_Mar_2023.pdf), state that authors retain copyright, grant third parties reuse under a Creative Commons licence, and that OLH uses CC BY 4.0; they also expressly allow a more restrictive licence where reproduced third-party material cannot be licensed more openly. The policy says article pages identify the licence and DOI and provide XML/PDF downloads where those files exist. This is suitable for a humanities/art candidate pool, subject to article-level review and exclusion of separately restricted material.

Representative record: [Calado, “Encoding Queer Erasure in Oscar Wilde’s *The Picture of Dorian Gray*” (DOI `10.16995/olh.6407`)](https://olh.openlibhums.org/articles/10.16995/olh.6407/). The official article record reports CC BY 4.0, peer review, and XML/PDF download options (including page-reported MD5 values). Direct automated retrieval encountered the site’s anti-bot challenge during this check, so the article files were not downloaded and their current bytes were not hashed.

For machine-readable discovery, the [Janeway API documentation](https://janeway.readthedocs.io/en/latest/dev/api.html) documents OAI-PMH with `oai_dc` and JATS metadata and identifies OLH’s live endpoint as [`https://olh.openlibhums.org/api/oai/`](https://olh.openlibhums.org/api/oai/). A direct `ListMetadataFormats` request returned both prefixes during this check. OAI-PMH supplies metadata/discovery; it does not replace verification of the article page’s licence or rights in included third-party content.

## T070 disposition

Both sources remain `ADMISSIBLE_PENDING_REVIEW` candidates only. No source is `APPROVED`, no source content was acquired, and T070 remains open. The next bounded acquisition step is to record the exact downloaded copy, licence evidence, attribution, third-party-rights result, timestamp, and SHA-256 in the separate pre-annotation candidate manifest before any passage preparation.
