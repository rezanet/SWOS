# Research Grade multimodal boundary

SWOS v2.0 treats a physical object, a media asset, an inspection activity, a
visual observation, and a scholarly interpretation as different records. A
surrogate or rendition is never the object itself. Every asset carries a
lowercase SHA-256 byte identity, dimensions, format, acquisition/source URI,
capture and mediation limits, lineage, content-credential state, accessibility
record, and purpose-specific rights.

## Rights and selectors

The runtime evaluates `view`, `analyse`, `transform`, `create_derivative`,
`quote`, `cache`, `export`, and `redistribute` separately. Analysis does not
grant transformation or derivative permission. Unknown or expired rights deny
the affected action. A derivative requires `view` and `analyse` plus an
applicable `transform` or `create_derivative` grant; inherited rights remain at
the restrictive parent state unless a separate evidence-bound grant says
otherwise. Export redacts barred bytes but retains identity and limitations.

Supported region selectors are IIIF Image API 3 pixel and percentage
coordinates and bounded Web Annotation SVG rectangles. Normalization binds the
selector to the exact asset digest and dimensions, rejects malformed,
ambiguous, oversized, executable, or out-of-bounds input, and records a stable
selector digest. The implemented scope is bounded 2D image analysis; it is not
3D reconstruction, biometric identification, face recognition, or general
computer vision.

## Observation, interpretation, and accessibility

Provider output is an observation, not a verified claim. Observations record a
reproducible selector, object and asset identity, modality, provider/model,
uncertainty, and provenance. Interpretations are separate and must link to
observations and/or external textual evidence before they can be considered by
human review. Cross-modal support retains asset-to-object,
observation-to-claim, and source-to-claim legs and uses the weakest leg.
Attribution, identity, originality, intention, and influence are never
established from pixels alone; unsupported or over-associated readings remain
blocked or limited.

Accessibility is structured as decorative, functional, or evidentiary purpose,
short alternative, conditional long description, labelled regions, a text
fallback, origin, language, review state, and the exact asset digest. A pixel
or semantic derivative invalidates inherited accessibility text until it is
re-reviewed. Machine-only or stale records do not satisfy the completeness
gate.

## Provider and orchestration boundary

`ImageAnalysisProvider` is provider-neutral and returns only `complete`,
`partial`, `insufficient`, `denied`, or `error`. The deterministic fake is
offline and bounded for ordinary CI. The OpenAI image-input adapter is opt-in,
requires explicit enablement and `OPENAI_API_KEY`, sends only rights-allowed
assets, and records request/config/response/runtime evidence. Missing
credentials or live access is `NOT_RUN`; no empty success is synthesized.

The permitted specialist sequence is art-history pack assistance followed by
art-criticism pack assistance. Both specialist agent contracts are versioned,
default-disabled, least privilege, and retain an executable pack-only fallback.
No provider or agent can set verified claim state. Direct physical inspection
remains a separately provenance-bound activity.

## Promotion gate

Promotion is default-off. Baseline and candidate evidence must bind the same
exact source head, cases, provider/model, non-agent configuration, prompts,
seed, and predetermined draws; only specialist routing may differ. A candidate
needs at least 0.08 absolute paired improvement, a positive lower 95% confidence
bound, no safety regression, exact artifact identity, successful live exact-head
evidence, human quorum, role separation, rollback rehearsal, and pack-only
fallback. Expired, mismatched, absent, or `NOT_RUN` evidence disables promotion.
Rollback returns to pack-only while preserving the evidence and reopening
review.

The current repository manifest at
`evals/fixtures/multimodal/manifest.json` is intentionally `not_run` because a
real rights-cleared, stratified, human-reviewed corpus is not present. This is
an explicit release blocker, not a claim that the multimodal release thresholds
have passed.
