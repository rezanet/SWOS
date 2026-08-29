# Runtime Reconciliation Validation Quickstart

Run from the repository root on
`codex/swos-v1.1-runtime-reconciliation`. No provider credential is required.

```powershell
$env:SPECIFY_FEATURE_DIRECTORY = "specs/002-swos-v1-1-runtime-reconciliation"
pwsh -NoProfile -File .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
python tools/check_spec_kit_artifacts.py
python tools/validate_document_manifest.py
python -m unittest tests/test_document_manifest.py tests/test_spec_kit_artifacts.py
python -m unittest discover -s tests/runtime -p 'test_*.py'
python tools/check_host_independence.py
python tools/check_vendor_leakage.py
python tools/check_portability_acceptance.py --definitions-only
python -m ruff check swos_runtime evals tools tests
git diff --check
```

Acceptance requires both Spec Kit feature directories to validate, complete
manifest coverage, 51 deterministic runtime tests, definitions-only portability
PASS and no runtime source changes in the branch diff.
