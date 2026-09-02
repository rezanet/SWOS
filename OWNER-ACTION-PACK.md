# SWOS Research Grade Closure — Owner Action Pack

Status: `PREPARATION_ONLY / RELEASE BLOCKED`
Baseline head: `1f5135969f04a104d4a99764f921d1743d22710f`
Authority: [evidence-closure-matrix.json](artifacts/research-grade/evidence-closure-matrix.json)

This pack names the external work still required for the 11 open frozen tasks. It is an action handoff, not approval and not release evidence. Do not merge, deploy, publish, or mark a task complete from this pack. Keep the named no-production/no-merge gates in force.

## Owner

| Action | Why | Exact form | Unblocks | Continue automatically? |
| --- | --- | --- | --- | --- |
| Preserve the Research Grade release block while evidence is acquired | `NOT_RUN`, `RESERVED_EXTERNAL`, missing, stale, or unverified material cannot pass | External owner instruction/decision record; no repository placeholder | Prevents premature T129 | No; owner decision required |
| After T070/T073/T079/T080/T093/T094/T095/T111/T127/T128 are independently complete, issue the explicit merge decision | T129 requires an owner merge approval as an external PR decision | Final exact-head PR decision with identity, disposition, head, and timestamp; no commit after final review | T129 | No; this is the final owner action |
| Retain named no-production/no-merge controls through the decision | T129 explicitly requires those gates to remain named | External governance record linked from the final PR/workflow | T129 safety condition | No |

The owner must not convert this action pack, a local green test run, or a preparation manifest into merge approval.

## Independent human reviewer

| Action | Why | Exact form | Unblocks | Continue automatically? |
| --- | --- | --- | --- | --- |
| Independently review citation pair annotations, adjudication, split leakage, and licence records | T070 requires genuine double annotation, adjudication, approval, and leakage control | Review disposition bound to `benchmark/citation-support/manifest.json`, split digests, `SOURCE-LICENCE-MANIFEST.json`, and `DATA-LICENCE.md`; preserve the immutable external PR/workflow record | T070, then T073/T127 | Yes after the review record is available; rerun remains required |
| Review and lock each discipline/category diversity packet without builder self-review | T079 requires at least ten locked human-reviewed packets per supported discipline using the frozen packet category set; do not multiply the cardinality by category | Review disposition bound to `evals/fixtures/source-diversity/manifest.json`, packet digests, reviewer identity, and category/discipline coverage | T079, then T080/T127 | Yes after packets and dispositions arrive; benchmark rerun remains required |
| Review multimodal rights, accessibility, grounding labels, pairs, adversarial cases, and provider output | T111 forbids unlicensed material, synthetic human judgments, and unexplained asset identity | Disposition bound to `evals/fixtures/multimodal/manifest.json`, per-asset rights records, asset digests, guidelines, and `DATA-LICENCE.md` | T111, then T127 | Yes after the complete review record arrives; evaluation rerun remains required |
| Perform an independent exact-head implementation/release review and resolve every thread | T127 requires independent review on the frozen head and resolved threads | External PR review with disposition, exact head, and thread IDs; do not commit post-review records | T127/T128 | No; a changed head restarts the final sequence |

The reviewer must be independent of the builder and must not fill missing evidence with a self-attestation.

## Maintainer / discipline steward

| Action | Why | Exact form | Unblocks | Continue automatically? |
| --- | --- | --- | --- | --- |
| Approve schema changes with the ADR and two named maintainers | Required approval shape in T127 | External ADR/PR approval records with identities, dispositions, and exact head | T127 | Yes after approval record; exact-head checks still required |
| Approve ontology with a maintainer and discipline steward | Required approval shape in T127 | External ontology/ADR approval record with both identities and disposition | T127 | Yes after approval record |
| Approve fixtures with two maintainers and the evaluation owner | Required approval shape in T127 | External fixture approval record bound to citation, diversity, PROV, and multimodal manifest digests | T070/T079/T093/T111/T127 | Yes after approval record; each verifier still must pass |
| Approve provider adapters with a maintainer and portability owner | Required approval shape in T127 | External adapter approval record bound to `acceptance/portability/matrix-v1.json` and adapter/config identities | T127 | Yes after approval record; six cases still require execution |
| Approve reviewer criteria | T127 requires a reviewer-criteria approval | External criteria approval record linked to the evidence PR/workflow | T127 | Yes after approval record |
| Supply and approve the independent ProvToolbox identity, licence, artifact, and digest | T094 must use a pinned independent oracle | Populate `benchmark/provenance/oracle-manifest.json` only with the approved relative artifact, lowercase SHA-256, licence, version, and placeholder-complete command; retain external approval | T094/T095/T127 | Yes after the approved manifest is committed; workflow execution remains required |

No maintainer or steward should mark a task complete based on a template, empty manifest, or unexecuted command.

## External execution environment

| Action | Why | Exact form | Unblocks | Continue automatically? |
| --- | --- | --- | --- | --- |
| Execute the exact independent PROV oracle | T094 requires ProvToolbox, not the SWOS converter | Follow [oracle-execution-kit.md](benchmark/provenance/oracle-execution-kit.md) through `.github/workflows/prov-certification.yml`; retain workflow run, certificate, command, input, and output hashes | T094/T095/T127 | Yes after a valid immutable workflow record arrives; certifier rerun remains required |
| Run `openai_api` portability case | Direct API semantic-equivalence case | `acceptance/portability/evidence/openai_api.json` produced only by `tools/record_portability_acceptance.py` after `tools/validate_autonomous_run.py --canonical`; retain credentials/provider/model/config provenance without secrets | T127 | Yes after PASS record arrives |
| Run `codex_chatgpt_subscription` portability case | Host-native subscription case forbids `OPENAI_API_KEY` and paid API calls | `acceptance/portability/evidence/codex_chatgpt_subscription.json`; record adapter, subscription host, zero paid calls, and semantic comparison | T127 | Yes after PASS record arrives |
| Run `claude_code_subscription` portability case | Host-native subscription case forbids `ANTHROPIC_API_KEY` and paid API calls | `acceptance/portability/evidence/claude_code_subscription.json`; record adapter, subscription host, zero paid calls, and semantic comparison | T127 | Yes after PASS record arrives |
| Run `replay_host_bundle` portability case | Offline/replay profile must preserve governed semantics | `acceptance/portability/evidence/replay_host_bundle.json`; record replay bundle digest and semantic comparison | T127 | Yes after PASS record arrives |
| Run `api_provider_changed` portability case | Proves provider variation without policy drift | `acceptance/portability/evidence/api_provider_changed.json`; adapter/provider must differ from `openai_api`, with output and evidence identity comparison | T127 | Yes after PASS record arrives |
| Run `model_changed_same_provider` portability case | Proves model variation within the same provider | `acceptance/portability/evidence/model_changed_same_provider.json`; provider must match `openai_api`, model must differ, and semantic comparison must pass | T127 | Yes after PASS record arrives |

Do not place API keys or subscription secrets in the repository, evidence JSON, chat, or logs. The release checker must remain fail-closed until all six recorder-produced records exist.

## Corpus and licensing acquisition

| Action | Why | Exact form | Unblocks | Continue automatically? |
| --- | --- | --- | --- | --- |
| Acquire and permission the citation-support corpus | T070's floors and `DATA-LICENCE.md` require real permitted pairs | Source URI/digest/licence/allowed-use/attribution records, pair files, annotation packets, adjudication, split manifest, leakage output, and checksum-bound `benchmark/citation-support/manifest.json` | T070/T073 | Yes after a complete permitted package arrives; builder and evaluator rerun required |
| Acquire diversity source material and prepare packets | T079 requires discipline-specific tuning and locked packets | Packet files under `evals/fixtures/source-diversity/`, source/provenance records, at least ten locked packets per supported discipline using the frozen packet category set, reviewer-lock records, and manifest digest | T079/T080 | Yes after complete packets and review arrive |
| Acquire PROV fixtures and performance corpora | T093/T095 require permitted valid/invalid/large/adversarial and resource-limit cases | Fixture files below `evals/fixtures/provenance/` plus `benchmark/provenance/manifest.json`, case digests, category/right records, and raw measurements | T093/T095 | Yes after complete corpus arrives; independent oracle still required |
| Acquire rights-cleared multimodal assets and annotations | T111 has frozen object, rendition, claim, pair, discipline, stratum, accessibility, and adversarial minima | Assets and records under `evals/fixtures/multimodal/`, per-asset URI/right URI/digest/allowed-use/attribution, guidelines, accessibility manifests, and mandatory `DATA-LICENCE.md` | T111 | Yes after rights and human-review records arrive; evaluation rerun required |

No copyrighted scraping, synthetic human judgments, invented source provenance, or placeholder digest may be used to satisfy any corpus action.

## Automatic continuation checklist

When an external packet arrives, the implementation builder may continue without another architectural decision only if it includes:

1. exact file paths and immutable digests;
2. rights/licence and allowed-use records where required;
3. reviewer, maintainer, steward, evaluation-owner, portability-owner, or owner identity/disposition in the required external record;
4. exact source-head binding and no unexplained head drift; and
5. enough inputs for the prescribed verifier or workflow to run without placeholders.

If any item is absent, keep the relevant task open and report the missing evidence. The next feature remains deferred until this feature's evidence and release gates are genuinely closed.
