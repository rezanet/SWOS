# T111 Verified Institutional Rights Sources

Status: RESEARCH/PREPARATION ONLY
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`
Verified: 2026-09-03

This file records institution-level rights-policy verification for candidate T111 acquisition. It does not replace per-asset rights verification and does not complete T111.

## Smithsonian Open Access

Verified:

- Smithsonian Open Access identifies eligible digital assets as CC0.
- Eligible assets may be used, transformed and shared without Smithsonian permission.
- Both 2D and 3D formats are available, including JPG/TIFF and glTF/glb/obj where provided.
- Smithsonian warns that third-party/legal restrictions can still apply even when Smithsonian uses CC0.

Acquisition rule:

Only ingest assets carrying the actual CC0 designation. Preserve object ID/accession, asset URI, CC0 status, byte digest, dimensions/format and any third-party restriction note. Do not treat `no known copyright restriction` as equivalent to CC0.

Reference:
https://www.si.edu/openaccess/faq

## National Gallery of Art, Washington

Verified:

- NGA releases factual collection data under CC0.
- NGA's open-access policy makes digital images of works it believes are in the public domain available under CC0 for commercial and non-commercial use without permission.

Acquisition rule:

Use only object-page/download assets covered by the NGA public-domain/open-access policy. Preserve the object page, image source URI, rights-policy URI, asset digest and credit/identifying metadata.

References:
https://www.nga.gov/artworks/free-images-and-open-access
https://www.nga.gov/terms-and-notices

## Cleveland Museum of Art

Verified:

- CMA provides more than 64,000 artwork records for unrestricted commercial/non-commercial use.
- It provides image assets for more than 37,000 works under its open-access initiative.
- CMA states that, to the extent possible under law, the dataset is dedicated under CC0.

Acquisition rule:

Use only image assets actually included in the CMA open-access dataset/API. Preserve the exact record, image URL, rights status, source byte digest and object identity. The presence of metadata for copyrighted objects does not make every possible external image of those objects reusable.

Reference:
https://www.clevelandart.org/open-access-api

## Art Institute of Chicago

Verified:

- AIC's API exposes `is_public_domain` and IIIF image identifiers.
- AIC explicitly recommends that developers use images from artworks tagged `is_public_domain=true` for open image reuse.
- Most API artwork data is CC0; the `description` field is CC BY 4.0.
- The IIIF service can also expose non-public-domain images, so image availability alone is not rights evidence.
- AIC asks bulk image users to throttle downloads rather than scrape concurrently.

Acquisition rule:

Filter candidate artworks to `is_public_domain=true`. Preserve field-level licence distinctions. Do not assume every IIIF-resolvable image is reusable. Use a sequential/throttled downloader and preserve exact IIIF/image identifiers plus bytes/digest.

Reference:
https://api.artic.edu/docs/

## Recommended acquisition allocation

Prepare a larger candidate pool than the frozen 60/96 floor:

- 20 NGA works;
- 15 Smithsonian 2D works;
- 10 Smithsonian 3D/multi-view objects;
- 15 CMA works;
- 10 AIC public-domain works.

Target: >=70 candidate works and >=115 candidate renditions before human review.

## Per-asset admissibility rule

Institution-level policy is necessary but not sufficient. A T111 asset is `RIGHTS_CLEARED` only when the exact asset record contains:

- institution and object/accession ID;
- object page URI;
- exact asset/media URI;
- exact rights URI/designation;
- documented permitted actions;
- attribution/credit record even when attribution is not legally required;
- byte SHA-256;
- dimensions/file format;
- acquisition timestamp;
- derivative lineage if transformed;
- third-party restriction status;
- reviewer disposition where required.

Reject or hold assets whose rights state is ambiguous. Do not infer transform/create-derivative permission from mere public web visibility.

## Human boundary

This research substantially narrows the legally usable acquisition pool, but machine collection cannot substitute for the required human review of rights, grounding, accessibility, cross-modal pairs, discipline tasks and adversarial truth labels. T111 remains OPEN.