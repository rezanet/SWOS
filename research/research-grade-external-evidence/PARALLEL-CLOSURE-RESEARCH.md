# SWOS Research Grade — Parallel External-Evidence Research

Status: RESEARCH HANDOFF / NOT RELEASE EVIDENCE
Baseline main SHA: `1f5135969f04a104d4a99764f921d1743d22710f`
Research date: 2026-09-03

This file records external research and concrete preparation recommendations for the remaining Research Grade closure work so future sessions do not have to rediscover the same sources. It does not complete any frozen task, supply human approval, or authorize release/deployment.

## T079 — source-diversity packet acquisition

Frozen requirement: separate tuning material plus at least ten locked human-reviewed diversity packets per supported discipline using the frozen category set. The minimum is ten locked packets per discipline, not ten packets multiplied by every category.

### Recommended acquisition substrate

Use open scholarly metadata rather than copyrighted full text wherever packet semantics permit.

Primary discovery/metadata sources:

1. OpenAlex — dataset is CC0; supports source/work/publisher/topic/geography/language and location-level licence discovery.
   - https://github.com/ourresearch/openalex-docs/blob/main/license.md
   - https://help.openalex.org/data/licenses/
2. Crossref — bibliographic metadata/references are generally factual/public-domain; Crossref-generated data is CC0. Abstracts remain publisher/author copyrighted and should not be assumed reusable.
   - https://www.crossref.org/documentation/retrieve-metadata/
3. OpenCitations — dataset content is available under CC0.
   - https://opencitations.net/what-we-do/
4. DOAJ — journal/article metadata is CC0; underlying article rights remain separate.
   - https://doaj.org/terms/

### Packet construction recommendation

Prepare at least 12 candidate packets per discipline (108 candidates across nine disciplines) so human review can reject/repair some while preserving the >=10 locked floor.

Each discipline candidate pool should deliberately cover the existing packet categories:

- balanced;
- concentrated;
- sparse;
- narrow;
- multilingual;
- historical;
- method-monoculture;
- duplicate;
- fake-diversity/provider-renaming.

Do not pre-label a packet as "adequate" solely from the generator. Generate the intended stress pattern and require an independent reviewer to lock the expected material gaps and adequacy judgment.

For each source family preserve enough metadata to exercise the v2 dimensions:

- canonical work/family identity;
- publisher/issuing owner;
- venue;
- author/institution cluster;
- geography/jurisdiction;
- language;
- publication period;
- methodology;
- source type;
- access mode;
- stance/source role;
- metadata evidence state (`observed`, `externally_verified`, `inferred`, `unknown`).

Provider identity is provenance only and must not count as diversity.

### Human boundary

T079 still requires genuine human-reviewed locks. Automated generation may prepare packet candidates, expected stressors and source-family metadata, but it must not self-approve them.

## T093/T094/T095 — PROV fixture/oracle/performance corpus

### Authoritative standards and test seed material

W3C PROV family:

- PROV overview: https://www.w3.org/TR/prov-overview/
- PROV-N: https://www.w3.org/TR/prov-n/
- PROV-CONSTRAINTS: https://www.w3.org/TR/prov-constraints/
- PROV-JSON Member Submission: https://www.w3.org/submissions/prov-json/
- W3C implementation report notes 280 PROV-CONSTRAINTS test cases.

W3C test-suite licensing guidance:

- https://www.w3.org/copyright/test-suites-licenses/
- Current W3C test suites may be distributed under either the W3C Test Suite License or 3-clause BSD when the suite carries the relevant dual-licence statement. Licence status must be recorded for each actual fixture source; do not infer a modern licence for an old unlabelled test file.

Recommendation:

- use clearly licensed W3C examples/test cases as seed valid/invalid cases when their exact licence permits it;
- copy unchanged tests when using a no-derivatives W3C test-suite licence for performance/conformance claims;
- use BSD/software-licensed cases where modifications/adversarial mutations are needed;
- create SWOS-original fixtures for extension fields, hostile blank-node graphs, resource-limit and round-trip edge cases where upstream rights are ambiguous.

### Independent oracle

ProvToolbox upstream:

- repository: https://github.com/lucmoreau/ProvToolbox
- latest GitHub release currently reported as `ProvToolbox-2.2.2`;
- tag licence file grants MIT-style unrestricted software rights with attribution/copyright notice.

Do not freeze only the string `2.2.2`. T094 should pin:

- exact release/tag;
- exact artifact/JAR coordinates or approved archive;
- downloaded artifact SHA-256;
- licence text/digest;
- invocation command;
- Java/runtime fingerprint;
- independent maintainer/steward approval.

The independent release oracle must be ProvToolbox (or the frozen approved external identity), not SWOS's own converter.

### T093 corpus structure recommendation

Build a rights-recorded fixture manifest containing at least these strata:

- valid minimal core relations;
- valid named bundles;
- typed and language-tagged literals;
- qualified relations;
- extension namespace/unknown-extension preservation;
- intentionally invalid ordering/type/bundle/relation constraints;
- malformed syntax;
- cross-format semantic-equivalence cases;
- blank-node identity/canonicalization cases;
- hostile but bounded graph shapes;
- large 1k and 10k assertion cases;
- resource-limit expected failures.

### T095 performance recommendation

Make the 1k/10k and hostile blank-node corpus generator deterministic and commit the generated-case manifests/digests or exact generator inputs. Do not use "whatever the current machine can handle" as the limit. CPU, memory and wall-clock bounds must be explicit inputs to the benchmark and recorded alongside runner identity.

## T111 — rights-cleared multimodal corpus

Frozen minima include:

- >=60 distinct objects/works;
- >=96 rights-cleared renditions;
- >=80 atomic region-grounding claims across >=20 assets;
- >=120 cross-modal pairs;
- >=48 discipline tasks across >=24 works;
- >=96 adversarial cases;
- >=6 media/material classes;
- >=3 mediation conditions;
- both art disciplines;
- accessibility manifests and human review;
- per-asset source/right URI, digest, allowed-use and attribution.

### Recommended open-access institutional source stack

#### Smithsonian Open Access

- https://www.si.edu/openaccess/faq
- https://www.si.edu/openaccess/devtools
- https://3d.si.edu/collections/openaccesshighlights

Smithsonian designates millions of 2D/3D digital assets as CC0. The Open Access API exposes public-domain/CC0 media; 3D open-access files can include glTF/glb/obj and provide a useful distinct mediation condition.

#### National Gallery of Art, Washington

- https://www.nga.gov/artworks/free-images-and-open-access
- https://www.nga.gov/terms-and-notices

The NGA states that open-access images of public-domain works are released under CC0 and are available for commercial or non-commercial reuse. The collection covers painting, sculpture, photography, drawing, decorative arts and prints.

#### Cleveland Museum of Art

- https://www.clevelandart.org/open-access-api
- https://www.clevelandart.org/open-access

CMA exposes >60k records and tens of thousands of image assets under its open-access/CC0 program; only use image URLs actually associated with CC0 works.

#### Art Institute of Chicago

- https://api.artic.edu/docs/

The API exposes `is_public_domain`; public-domain works have IIIF manifests/images. Most API data is CC0; the description field is CC BY. Filter to public-domain artworks before acquiring images.

### Suggested corpus mix

Use multiple institutions to avoid a single-institution benchmark and to create genuine mediation variation.

Provisional target before human review:

- 20 NGA works;
- 15 Smithsonian 2D works;
- 10 Smithsonian 3D objects with multiple render/view assets where permitted;
- 10 CMA works;
- 10 Art Institute public-domain works.

This yields 65 candidate works and margin above the 60-work floor. Acquire more than 96 candidate renditions so rights or review rejections do not drop the corpus below the floor.

Media/material classes should deliberately include at least:

- painting;
- drawing/watercolour;
- print;
- sculpture;
- decorative/functional object;
- photograph;
- manuscript/textile/ceramic/metalwork as additional classes where available.

Three mediation conditions can be constructed without inventing rights:

1. direct 2D collection image / IIIF rendition;
2. alternate view/detail/crop derived under explicit transform permission;
3. 3D model or multi-view object representation from Smithsonian CC0 assets.

Do not treat a derived crop as a new distinct object. Preserve lineage from original asset digest to derivative digest.

### Human boundary

Human review remains required for rights confirmation, region-grounding truth, cross-modal labels, accessibility completeness, adversarial truth and provider-output judgment. Model-generated labels cannot count as human review.

## Six portability cases

Frozen matrix is `acceptance/portability/matrix-v1.json` and the canonical request is:

`Can an AI-operated machine be a witness in court?`

Required cases:

1. `openai_api`
2. `codex_chatgpt_subscription`
3. `claude_code_subscription`
4. `replay_host_bundle`
5. `api_provider_changed`
6. `model_changed_same_provider`

A valid case must run the real canonical workflow, pass `tools/validate_autonomous_run.py --canonical`, and then be recorded by `tools/record_portability_acceptance.py`. Hand-authored PASS JSON is forbidden.

Recommended order:

1. `replay_host_bundle` first — cheapest deterministic sanity check but cannot substitute for live host cases;
2. `openai_api` — establishes baseline provider/model provenance;
3. `model_changed_same_provider` — reuse provider setup with a different model;
4. `codex_chatgpt_subscription` — must run without `OPENAI_API_KEY` and with zero paid API calls;
5. `claude_code_subscription` — must run without `ANTHROPIC_API_KEY` and with zero paid API calls;
6. `api_provider_changed` — execute a genuinely different API/provider adapter than `openai_api`.

Do not attempt to manufacture the subscription-host evidence from API calls. Different article text is allowed; governed outcome equivalence is what must pass.

## T127 — approvals + exact-head portability/review

Frozen T127 requires all of the following external evidence on one exact frozen head:

- ADR + two-maintainer schema approval;
- maintainer + discipline-steward ontology approval;
- two-maintainer + evaluation-owner fixture approval;
- maintainer + portability-owner provider-adapter approval;
- reviewer-criteria approval;
- all six portability PASS records;
- green hosted CI;
- independent exact-head review with every thread resolved.

These approvals should remain immutable PR/workflow records; do not add post-review commits merely to record them.

Practical preparation that can be done before the final review:

- create one approval checklist mapping each required identity/disposition to an exact artifact digest;
- ensure candidate fixture/model/oracle/adapter manifests expose stable digests before asking for approval;
- do not request final exact-head review until T070/T073/T079/T080/T093/T094/T095/T111 evidence has stopped changing the candidate.

## T128 — external immutable audit pack

The current pre-freeze `artifacts/research-grade/audit-pack.json` names `reports/coverage.json` with a historical pre-freeze digest, while the current checkout does not contain that path. Verification therefore fails closed.

Recommendation:

- do not create a dummy `reports/coverage.json`;
- regenerate coverage at the final exact candidate head using the authoritative coverage command/workflow;
- preserve raw coverage artifact + runner/workflow identity + exact source SHA;
- assemble T128 only after all external review/approval/portability/oracle evidence is immutable;
- if review changes repository content, repeat the frozen-head sequence as T128 requires.

## T129 — owner decision

No research agent/builder can satisfy T129.

Only after every prior frozen gate passes should the owner issue one explicit external exact-head merge decision containing:

- exact candidate head;
- owner identity;
- disposition;
- timestamp;
- confirmation that named no-production/no-merge gates remained in force through the decision.

This research branch must never be treated as that approval.

## Current priority order

1. T070 candidate corpus preparation (parallel with T079/T093/T111 acquisition preparation)
2. T079 human-review packet preparation
3. T093/T095 fixture/performance corpus + T094 oracle pin preparation
4. T111 rights-cleared candidate corpus preparation
5. execute six portability cases when their actual environments are available
6. only then stage T127 exact-head approvals/review
7. T128 immutable audit pack
8. T129 explicit owner decision
