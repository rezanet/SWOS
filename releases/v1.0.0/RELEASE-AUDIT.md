# SWOS v1.0.0 Final Release Audit

**Audit state:** candidate — final CI and approval pending  
**Audit date:** 2026-08-20  
**Release-audit base:** `bcf096fe87585121729d80e32e672ba772eb06f5`  
**Policy basis:** `swos.release-gate@1.0.0` and `docs/operations-and-lifecycle-playbook.md`

## Scope

This audit applies SWOS's own release checklist to the first public v1.0.0 specification-lock release. The default effect of the release gate is deny; publication is allowed only after every required item is evidenced or explicitly not applicable.

## Checklist

| Requirement | Candidate status | Evidence / disposition |
|---|---|---|
| `make validate` green | PENDING FINAL PR CI | Release PR must pass Schema and contract conformance. |
| `make lint-skills` green | PENDING FINAL PR CI | Release PR must pass Agent Skills six-field constraint. |
| `make governance-check` green | PENDING FINAL PR CI | Release PR must pass Governance policy check. |
| `make eval` green; no plane regressed | PENDING FINAL PR CI | All eight planes must pass. v1.0.0 evaluates in contract mode when no system is bound. |
| Every ADR for this release merged | PASS | ADR-0001 through ADR-0010 are on `main`; no open PR existed when the release branch was created. |
| `CHANGELOG.md` updated, including known gaps | PASS | v1.0.0 entry retained and dated; three known gaps remain explicitly carried to 1.1. |
| Schema versions unchanged or migration + ADR | PASS | Comparison `d925668..bcf096fe` changes only `.github/workflows/swos-ci.yml` and `tools/check_dco.py`; no contract/schema drift. |
| Adapter capability matrices reviewed | PASS / NO CAPABILITY DELTA | Release-record work adds no host capability and changes no adapter matrix requirement. |
| Release notes signed | PENDING FINAL APPROVAL | Candidate notes exist; final sign-off becomes effective only after final CI and SDL approval. |
| Release provenance bundle created and frozen | CREATED / NOT YET FROZEN | Candidate EPG bundle exists with release scope; `frozen` remains false until final CI passes. |
| Governance-owner approval recorded as SDL `release` | CONDITIONAL / PENDING | Candidate release decision exists with `review_status: pending`; final approval follows CI. |
| Backout plan documented and tested | PASS | `BACKOUT.md` records a non-destructive dry-run appropriate to a first release. |

## Release-gate policy checks

| Gate rule | Candidate status |
|---|---|
| all required evaluation planes pass | PENDING FINAL PR CI |
| no required plane is `not_run` | PENDING FINAL PR CI |
| zero open blocker findings | PASS — no unresolved release blocker has been identified in this audit |
| provenance completeness | PENDING FREEZE |
| audit pack complete | PASS — audit, provenance, SDL, release notes and backout record are present |
| required human approval recorded | PENDING FINAL SDL APPROVAL |
| waiver shape | NOT APPLICABLE — no waiver is being used |

## Material findings

1. **No contract/schema drift:** the post-publication fixes were limited to CI matrix wiring and DCO enforcement.
2. **DCO is fail-closed:** the hardened checker selects explicit event ranges, rejects empty ranges and validates actual `Signed-off-by` trailers.
3. **Evaluation qualification:** contract-mode PASS means gate/fixture conformance, not empirical quality of an unbound AI system. The release notes state this plainly.
4. **First-release rollback semantics:** there is no legitimate previous supported version. Backout means withdrawal to “no supported release” while preserving history.

## Candidate decision

**BLOCK UNTIL FINALISATION.** The release artefacts are complete enough to enter final CI, but SWOS v1.0.0 must not be tagged while the SDL is pending or the provenance bundle is unfrozen.

After the release-record PR is green, this audit will be updated to PASS, the release SDL will be approved, and the provenance bundle will be frozen.
