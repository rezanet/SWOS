# T111 Rights-Cleared Multimodal Corpus Plan

Status: RESEARCH/PREPARATION ONLY
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`

## Frozen minima

- >=60 distinct objects/works;
- >=96 rights-cleared renditions;
- >=80 atomic region-grounding claims across >=20 assets;
- >=120 cross-modal pairs;
- >=48 discipline tasks across >=24 works;
- >=96 adversarial cases;
- >=6 media/material classes;
- >=3 mediation conditions;
- both `art_history` and `art_criticism`;
- accessibility manifests;
- per-asset source/right URI, digest, allowed-use and attribution;
- genuine human review.

## Recommended institutional source stack

### Smithsonian Open Access

- https://www.si.edu/openaccess/faq
- https://www.si.edu/openaccess/devtools
- https://3d.si.edu/collections/openaccesshighlights

Smithsonian Open Access designates eligible 2D/3D assets CC0. Its 3D assets are particularly useful for a distinct mediation condition.

### National Gallery of Art, Washington

- https://www.nga.gov/artworks/free-images-and-open-access
- https://www.nga.gov/terms-and-notices

NGA states that qualifying open-access images of public-domain works are released under CC0 and available for commercial/non-commercial use.

### Cleveland Museum of Art

- https://www.clevelandart.org/open-access-api
- https://www.clevelandart.org/open-access

CMA provides CC0 collection data and tens of thousands of open-access public-domain image assets. Use only records whose image asset is actually designated open access/CC0.

### Art Institute of Chicago

- https://api.artic.edu/docs/

AIC exposes `is_public_domain` and IIIF manifests/images for public-domain artworks. Most API data is CC0; the `description` field is CC BY. Filter to public-domain artworks for image acquisition and preserve the field-level licence distinction.

## Candidate-work target

Acquire at least 70 candidate works and at least 115 candidate renditions before human review so rights/quality/review rejection does not drop the final corpus below 60/96.

Suggested starting distribution:

- 20 NGA works;
- 15 Smithsonian 2D works;
- 10 Smithsonian 3D objects;
- 15 Cleveland Museum works;
- 10 Art Institute public-domain works.

Institution counts are acquisition targets, not frozen benchmark quotas.

## Media/material coverage

Deliberately cover at least six classes, preferably more:

- painting;
- drawing/watercolour;
- print;
- sculpture;
- decorative/functional object;
- photography;
- ceramic/metalwork/textile/manuscript as additional classes where rights allow.

## Mediation conditions

Use at least three genuinely different conditions:

1. primary 2D collection image / IIIF rendition;
2. alternate view/detail or explicitly permitted deterministic derivative/crop, with lineage to the original asset digest;
3. 3D or multi-view object representation from Smithsonian CC0 assets.

Do not count a crop as a new object. Do not create derivatives unless `transform` / `create_derivative` rights are explicitly permitted by the recorded rights statement.

## Per-asset record

Preserve:

- institution;
- object ID/accession;
- object page/source URI;
- asset/media URI;
- rights URI;
- rights designation and version;
- permitted actions (`view`, `analyse`, `transform`, `create_derivative`, `cache`, `export`, `redistribute` as evidenced);
- attribution/credit line;
- source byte SHA-256;
- dimensions/file type;
- object/material/medium metadata;
- acquisition timestamp;
- derivative lineage where used;
- accessibility source/origin.

Do not infer permissions not granted by the source.

## Annotation/review package

Prepare blank independent human-review packets for:

- rights confirmation;
- object/asset identity;
- region-grounding labels;
- cross-modal support pairs;
- art-history/art-criticism tasks;
- accessibility short/long alternatives and purpose;
- false originality/attribution adversarial cases;
- over-association adversarial cases;
- multi-view limitations.

Machine-generated observations can be candidates, but may not be counted as human truth or accessibility review.

## Adversarial design priorities

- visually similar but different object/artist/material;
- detail from same object attributed to wrong region/view;
- plausible but unsupported iconographic interpretation;
- over-association from stylistic resemblance;
- false originality/authorship claim;
- text source contradicts visual inference;
- image-only assertion requiring textual provenance;
- incomplete view treated as whole-object evidence;
- derivative with stale accessibility text;
- rights-denied transformation attempted as allowed.

## Completion boundary

Research and automated acquisition can prepare candidate assets, rights records, digests and annotation packets. T111 stays OPEN until the complete frozen minima are met by genuinely rights-cleared assets and independent human-reviewed labels/records, and the production evaluation passes.