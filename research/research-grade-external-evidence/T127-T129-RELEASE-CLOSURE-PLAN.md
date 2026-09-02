# T127–T129 Release Closure Plan

Status: RESEARCH/PREPARATION ONLY
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`

## T127 — exact-head approvals, portability and independent review

Frozen T127 requires on one immutable candidate head:

- ADR + two-maintainer schema approval;
- maintainer + discipline-steward ontology approval;
- two-maintainer + evaluation-owner fixture approval;
- maintainer + portability-owner provider-adapter approval;
- reviewer-criteria approval;
- all six portability PASS records;
- green hosted CI;
- independent review of the exact frozen head;
- every review thread resolved.

### Preparation before asking humans

Do not request final approvals while the fixture/model/oracle corpus is still changing.

Before the exact-head sequence:

1. finish genuine T070/T073 citation evidence;
2. finish genuine T079/T080 diversity evidence;
3. finish genuine T093/T094/T095 provenance evidence;
4. finish genuine T111 multimodal evidence;
5. obtain all six recorder-produced portability PASS records;
6. freeze all manifests and collect their SHA-256 digests;
7. run hosted CI on the exact candidate.

Then prepare an approval index with one row per required approval containing:

- approval class;
- required role(s);
- candidate head;
- artifact/ADR/manifest paths;
- canonical digests;
- external record URL/ID;
- disposition;
- timestamp.

Approval records should remain external PR/workflow artifacts. Do not commit a new record after the final review and thereby change the head being reviewed.

## T128 — external immutable audit pack

Current pre-freeze audit manifest names `reports/coverage.json` with a historical digest, but that path is absent in the current checkout; verification correctly fails closed.

Do not satisfy this by creating an empty or placeholder coverage file.

At final candidate head:

1. run the authoritative coverage workflow/command;
2. retain raw coverage JSON as an immutable workflow/release artifact;
3. bind its SHA-256, exact source SHA, runner fingerprint and command;
4. collect exact-head CI workflow IDs;
5. collect the independent review disposition and thread-resolution evidence;
6. collect schema/ontology/fixture/adapter/reviewer approvals;
7. collect the six portability records;
8. collect citation/diversity/PROV/multimodal release artifacts;
9. collect independent ProvToolbox oracle output;
10. assemble the external immutable audit pack;
11. independently verify that pack.

If the independent review leads to any repository-content change, the candidate head changes and the final T126–T128 sequence must be repeated. Do not try to carry exact-head approval/review evidence across a changed candidate.

## T129 — explicit owner decision

T129 cannot be delegated to the builder, this research agent, an automated workflow or an independent reviewer.

Only after every prior frozen release condition passes, the owner should issue a single external decision containing:

- exact candidate commit SHA;
- owner identity;
- explicit disposition (`approve merge` or equivalent unambiguous form);
- timestamp;
- confirmation that named no-production/no-merge gates remained active up to the decision.

The decision must be external to the already-reviewed source head so it does not create a post-review commit.

No existing research note, preparation pack, green local test run or prior conversation counts as T129 approval.

## Sequence

The safe final sequence is:

external evidence complete
→ six portability PASS records
→ freeze exact candidate
→ hosted CI
→ required maintainer/steward/evaluation/portability approvals
→ independent exact-head review
→ resolve threads (restart exact-head sequence if source changes)
→ external immutable T128 audit pack + independent verification
→ explicit owner T129 decision

Merge and deployment remain separate actions even after T129.