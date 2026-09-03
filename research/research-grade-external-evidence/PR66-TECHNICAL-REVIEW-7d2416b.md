# PR #66 technical review — head `7d2416bff6c5a3f0021b5c7f16243752449a7df9`

Status: TECHNICAL REVIEW / CHANGES REQUIRED / NOT CONTRACTUAL INDEPENDENT APPROVAL
Reviewed: 2026-09-03
Base: `1f5135969f04a104d4a99764f921d1743d22710f`

This review is a pre-merge engineering/evidence review. It must not be counted as the independent source-rights approval, independent human corpus review, T070 completion, Research Grade certification, or owner release approval.

## What is now correct

- The earlier temporal-direction defect has been repaired. The corrected policy uses a later holdout: non-OOD sources with `publication_year >= 2020` are temporal.
- OOD has precedence over the temporal date rule.
- Hash/proportion assignment is limited to in-domain train/calibration/locked-test and cannot define temporal/OOD membership.
- The candidate corpus remains unlabelled: two blank annotation slots and one blank adjudication slot are enforced; top-level label/retrieval-intent fields are rejected.
- Candidate/source binding includes exact acquired-copy URI, source SHA-256, attribution and licence.
- Candidate sources cannot be promoted to APPROVED by the acquisition validator; approval stays pending.
- The final adjudicated-pair validator still rejects the pre-annotation packets.

## P1-1 — discipline assignment is not trustworthy enough for a frozen per-discipline corpus

The current catalog contains obvious semantic misclassification. In the first `art_history` block, for example, the catalog labels these as `art_history`:

- `Collective strategies to cope with work related stress among nurses in resource constrained settings: An ethnography of neonatal nursing in Kenya`;
- `The social construction of 'dowry deaths'`;
- `Are public-private partnerships a healthy option? A systematic literature review`.

These are not art-history sources by ordinary disciplinary meaning. The root cause is visible in `classify_elsevier()`: an Elsevier `ARTS` subject-area hit is collapsed to `art_history` unless a few criticism tokens appear. Elsevier's broad Arts and Humanities classification is not equivalent to SWOS `art_history`.

Why this blocks the pre-human corpus slice:

- T070 has frozen per-discipline floors;
- the annotation contract requires discipline-competent annotators;
- discipline slices later feed locked evaluation and reporting;
- a numerically balanced but semantically wrong discipline assignment would make the 665–670-per-discipline preparation counts misleading and force expensive relabelling/reacquisition after human annotation.

Required repair before merge:

1. Treat publisher subject areas as candidate metadata, not final SWOS discipline truth.
2. Replace broad `ARTS -> art_history` and similar weak mappings with a stricter taxonomy/crosswalk.
3. Require a deterministic auditable discipline-assignment basis per source, e.g. explicit journal/subject taxonomy + title/abstract evidence, with `assignment_method`, evidence values and confidence/review state.
4. Sources that cannot be assigned confidently should be `discipline_pending_review` or excluded from per-discipline floor counts rather than forced into a discipline.
5. Rebuild the 536-source catalog / 6,000 candidate pairs after the corrected mapping and re-check all nine candidate margins.
6. Add regressions with negative examples so social/health-policy papers cannot enter art_history solely because a broad Arts/Humanities code is present.

No human labels are needed for this repair; this is source taxonomy/provenance hardening.

## P1-2 — OOD selection is ordinal sampling, not a genuine out-of-distribution domain rule

`_semantic_assignment()` currently marks every third eligible `technical_writing` source as OOD using `ordinal % 3 == 0`, while assigning `domain_id = technical-writing-held-out-v1`.

This is predeclared and deterministic, but the membership rule is not semantic: ordinal position within a candidate list does not make one technical-writing source out of distribution relative to the adjacent technical-writing sources. It is effectively a sampling rule disguised as a domain criterion.

The frozen T070 research requirement was that OOD be selected by a predeclared domain/source/task criterion, not by hash/random/ordinal partitioning.

Required repair before freezing the corpus:

1. Define a coherent OOD criterion independent of source order. Examples: a genuinely held-out source class, journal/venue family, methodology family, document genre, language, or another explicit domain characteristic not represented in the in-domain training pool.
2. Persist the OOD feature/evidence used for each admitted OOD source.
3. If a sufficiently large genuine OOD slice cannot be produced from this 536-source pool, leave OOD acquisition incomplete and add a supplementary rights-cleared source pool rather than manufacturing OOD by ordinal.
4. Add regression tests proving reordering the source catalog cannot change OOD membership.

## Rights note — not promoted to a defect in this review

Elsevier records are tagged `article_level_verified` using the official v2 OA-CCBY article-ID set plus `metadata.openaccess=Full`, while retaining a third-party-content warning on every Elsevier source. That is a reasonable acquisition-screening basis for PRE-ANNOTATION use, but it is not the required independent rights approval. All sources correctly remain `ADMISSIBLE_PENDING_REVIEW`; the final rights review must inspect the exact article/copy and any third-party content before promotion.

## Disposition

`CHANGES_REQUIRED` for the pre-annotation slice because the discipline mapping and OOD membership directly affect the expensive human-review corpus that would follow.

Do not start annotation against this exact head. Fix these two source-assignment defects, regenerate, rerun counts/isolation/binding/schema/tests, then commission a fresh exact-head technical review. T070 remains OPEN regardless.