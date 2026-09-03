# Research Grade human-review infrastructure

Status: PREPARATION / BLANK FORMS ONLY / NOT HUMAN EVIDENCE

These forms reduce reviewer overhead without manufacturing the human judgments required by T070, T079/T080 and T111. A model, builder, repository maintainer or this preparation agent must not pre-fill reviewer identities or final judgments and then count them as independent evidence.

## Shared independence rules

- Reviewer identity must refer to the real person who performed the review.
- Required roles must be distinct where the frozen contract requires independence.
- A reviewer must declare relevant competence and conflicts.
- Every judgment binds to immutable input identifiers/digests; edits after review invalidate the review unless the contract explicitly permits a bounded non-semantic change.
- `pending`, blank and unavailable are valid preparation states; guessed approval is not.
- Machine predictions/hints may be stored in a separate diagnostic field but should be hidden during blind review when they could bias the judgment.
- Adjudication resolves recorded human disagreement; it is not a way to fabricate a second annotation.

## T070 workflow

### Stage A — source-rights review

Review the exact acquired copy before annotation. Confirm source/work identity, article-level licence, permitted corpus uses, attribution, exact SHA-256, and any third-party material that falls inside candidate passages. A dataset-level licence alone does not prove that separately licensed embedded material is reusable.

Use `T070-SOURCE-RIGHTS-REVIEW-TEMPLATE.json`.

Source disposition values:

- `approved_for_candidate_annotation`
- `approved_with_exclusions`
- `rejected_rights`
- `rejected_identity`
- `needs_more_evidence`

### Stage B — prepare and distribute two blind independent worksets

After the PR #66 integrity blockers are repaired, run `T070-PREPARE-BLIND-ANNOTATION-WORKSETS.py` against the regenerated `unlabelled-candidate-pairs.jsonl`. The preparation tool refuses duplicate pair IDs, duplicate `(source_id, claim_family_id, exact_quote)` semantic spans, non-blank annotation/adjudication slots and malformed source digests. It hides acquisition stratum, candidate pattern, semantic partition, the other annotator decision and machine prediction.

Annotators receive the atomic claim, exact bounded passage, necessary source context, discipline and source identity. Bind the corresponding completed source-rights review before annotation begins.

Allowed labels:

- `directly_supports`
- `partially_supports`
- `context_only`
- `contradicts`
- `not_supported`

Every annotation records a rationale focused on what the passage establishes, not whether the claim seems plausible from outside knowledge.

### Stage C — independent adjudication

The adjudicator must not be annotator A or B. They receive both completed annotations and the same immutable claim/passage packet. The adjudicator records one final label and a rationale addressing the disagreement or confirming the agreed label.

No T070 pair becomes release truth until both annotations, adjudication, source approval and all final corpus checks pass.

## T079 / T080 workflow

Use `T079-INDEPENDENT-REVIEW-TEMPLATE.json` for each locked candidate packet.

Reviewer checks:

- source-family canonicalisation is semantically correct;
- mirrors/editions/providers do not create fake families;
- every pre-retrieval required dimension/stratum is declared before scoring;
- metadata marked `observed` or `externally_verified` is supported by the cited metadata record;
- `inferred`/`unknown` values are not allowed to improve diversity;
- claim-exposure edges deduplicate `(claim_id, canonical_family_id)`;
- provider identity is provenance only;
- seeded construction intention (balanced, concentrated, sparse, narrow, multilingual, historical, method_monoculture, duplicate, fake_diversity, missing_strata) is genuinely represented by the packet;
- expected raw disposition and the four T080 benchmark-truth booleans are recorded independently of any machine prediction.

For a packet locked into T080, the human reviewer must explicitly supply `benchmark_truth.material_gap`, `adequate`, `justified_narrow`, and `seeded_fake_or_missing_strata`. Automation must not infer those values from the construction category or machine result.

The reviewer may reject or require repair rather than force a packet into the intended category. If a locked candidate is rejected, generate and independently review a replacement so each supported discipline still has at least ten genuinely locked packets.

After real review, use `T080-BUILD-LOCKED-BENCHMARK-INPUT.py` to import and validate the exact bound human records. Only then run the production `tools/run_source_diversity_benchmark.py` path.

## T111 workflow

Use `T111-INDEPENDENT-REVIEW-TEMPLATE.json` together with the generated `T111-REVIEW-CANDIDATE-MANIFEST.json` and `T111-ALTERNATE-VIEW-MANIFEST.json`.

Human review has separable legs:

1. exact-asset rights/identity confirmation;
2. region-grounding truth for bounded selectors;
3. cross-modal claim/evidence relation;
4. accessibility description quality/accuracy;
5. discipline-task answer/critique truth where required;
6. adversarial case disposition.

The prepared candidate corpus supplies exact primary/crop/alternate-view asset bindings and blank review slots. It does not supply human truth. A rights-cleared object is not automatically a correct grounding case, and a visually plausible model answer is not automatically a supported art-historical/material attribution.

## Import discipline

- Preserve original blank packet IDs and source/media digests.
- Import reviewer results as separate records; do not mutate source bytes or candidate truth silently.
- Reject duplicate reviewer identity where independence is required.
- Reject records whose input digest no longer matches.
- Preserve timestamps, competence declaration, conflict declaration and rationale.
- Keep rejected/invalid reviews in the audit trail with disposition; do not delete them to improve agreement statistics.

These forms are deliberately neutral. They do not make T070, T079, T080 or T111 complete merely by being filled; the production validators and required independent approvals remain authoritative.
