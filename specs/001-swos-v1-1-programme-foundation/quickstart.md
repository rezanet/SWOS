# Foundation Validation Quickstart

Run from the repository root on the programme-foundation branch.

## Prerequisites

- Python 3.11 or newer;
- the repository's locked developer environment when running the full suite;
- Spec Kit v1.0.1 available through the pinned `uvx` command; and
- no provider credential is needed for the foundation checks.

## Foundation checks

```powershell
uvx --from git+https://github.com/github/spec-kit.git@v1.0.1 specify --version
pwsh -NoProfile -File .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
python -m unittest tests/test_document_manifest.py tests/test_workflow_profiles.py
python tools/validate_document_manifest.py
python tools/check_workflow_profiles.py
```

Expected result: Spec Kit reports `1.0.1`; the focused tests pass; the manifest
validator reports the complete document count with zero errors; and the workflow
inspector reports deterministic PR/push and manual live separation.

## Existing repository gates

```powershell
python tools/validate_schemas.py --strict
python tools/check_governance.py
python tools/lint_skills.py --strict
python tools/check_host_independence.py
python tools/check_vendor_leakage.py
python tools/check_portability_acceptance.py --definitions-only
python -m unittest discover -s tests/prose -p 'test_*.py'
python -m unittest discover -s tests/runtime -p 'test_*.py'
python -m ruff format --check swos_prose swos_runtime benchmark tools evals tests
python -m ruff check swos_prose swos_runtime benchmark tools evals tests
```

Live workflows are intentionally not part of this local quickstart. They must
be dispatched explicitly against a selected exact SHA and are not ordinary
merge gates.
