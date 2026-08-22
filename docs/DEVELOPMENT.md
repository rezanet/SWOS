# SWOS development and quality baseline

This repository has two deliberately separate evidence classes:

- deterministic gates run from the committed source, tests and locked developer
  environment and are merge-blocking;
- Luna/OpenAI live evidence is stochastic, requires an operator-supplied key and
  remains explicitly non-gating.

The implementation surface is Python 3.11 or newer. The commands below use the
Windows PowerShell spelling; replace `\.venv\Scripts\python.exe` with
`.venv/bin/python` on POSIX systems.

## Clean local setup

Run these commands from a fresh checkout. The lock contains the exact developer
and CI toolchain; the editable install does not resolve dependencies again.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation --editable .
```

Do not put credentials in `.env`, source files, fixtures, logs, reports or Git.
Use [`.env.example`](../.env.example) only as a variable-name reference. GitHub
secret scanning and push protection are enabled for the public repository.

## Deterministic gates

The following commands are the local equivalents of the engineering quality
workflow:

```powershell
.\.venv\Scripts\python.exe -m ruff format --check swos_prose benchmark tools evals tests
.\.venv\Scripts\python.exe -m ruff check swos_prose benchmark tools evals tests
.\.venv\Scripts\python.exe -m coverage erase
.\.venv\Scripts\python.exe -m coverage run --branch --source=swos_prose -m unittest discover -s tests/prose -p 'test_*.py'
.\.venv\Scripts\python.exe -m coverage json -o coverage.json
.\.venv\Scripts\python.exe -m coverage report --fail-under=80
.\.venv\Scripts\python.exe tools/check_coverage.py --coverage-json coverage.json
.\.venv\Scripts\python.exe -m pip_audit --requirement requirements-dev.lock --strict
.\.venv\Scripts\python.exe -m bandit -r swos_prose benchmark tools evals -lll -ii
```

`make quality` runs the same quality gates on systems with GNU Make. `make ci`
also runs schema validation, Agent Skills portability, governance, all eight
evaluation planes, semantic-delta tests and the active 56-case benchmark
contract.

Coverage measures every executable module under `swos_prose`; tests and tooling
are not silently excluded from the lint or format gates. The policy is an 80%
whole-package floor plus higher floors for the M1 repair, pipeline, causal-scope,
deterministic-verifier and proposition modules. The thresholds are enforced by
`tools/check_coverage.py`, not inferred from a percentage in prose.

## Security and dependency changes

`requirements-dev.lock` is the authoritative developer/CI dependency set. A
dependency update must regenerate it intentionally, run the deterministic test
suite, run `pip-audit` against the resulting lock and include the resulting
version diff in review. Do not add an unpinned CI dependency or bypass the lock.

Bandit is the local Python SAST gate. CodeQL runs as the hosted repository SAST
workflow. A high-confidence/high-severity finding blocks the relevant check;
warnings are recorded rather than silently suppressed.

## Governed merge checklist

Every authored commit must be created with `git commit -s` and inspected for a
standalone `Signed-off-by:` trailer before pushing. When a hosted squash merge
is used, the merge message must contain a real line break before that trailer;
an escaped `\n` sequence is text, not a DCO trailer. Verify the post-merge DCO
job on the exact `main` SHA before treating the milestone as complete. If a
hosted merge produces an unsigned commit, preserve the history and record it as
a historical DCO deviation. A signed governed follow-up makes the new commit
range pass but does not retroactively remediate the unsigned commit; do not
rewrite `main` without explicit authority.

## Live evidence

Live verifier, dogfood and benchmark jobs use `OPENAI_API_KEY` only when the
workflow secret is present. They may expose model variability and are retained
as evidence, but they do not replace deterministic semantic, schema, governance,
DCO, benchmark-contract or evaluation gates. Local live runs should set the
variables from `.env.example` in the process environment and must never commit
the values.
