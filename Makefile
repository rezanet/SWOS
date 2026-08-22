.PHONY: help validate lint-skills eval eval-fast test-prose benchmark-prose audit-pack gate governance-check format lint coverage security sast quality ci clean

help:
	@echo "SWOS - make targets"
	@echo "  validate        Validate every artefact against the frozen JSON Schemas"
	@echo "  lint-skills     Enforce the six-field Agent Skills frontmatter constraint"
	@echo "  eval            Run the full evaluation harness (all eight planes)"
	@echo "  eval-fast       Run grounding + citation planes only (pre-commit)"
	@echo "  test-prose      Run SWOS Prose semantic-delta unit tests"
	@echo "  benchmark-prose Validate the active 56-case SWOS Prose benchmark corpus"
	@echo "  format          Check repository Python formatting"
	@echo "  lint            Run the general Python lint gate"
	@echo "  coverage        Measure and enforce executable-Python coverage"
	@echo "  security        Audit the pinned developer dependency lock"
	@echo "  sast            Run the Python static security analysis gate"
	@echo "  quality         Run format + lint + coverage + security + SAST"
	@echo "  ci              Run all deterministic SWOS release and quality gates"

validate:
	python3 tools/validate_schemas.py

lint-skills:
	python3 tools/lint_skills.py

eval:
	python3 evals/harness/run_evals.py --all

eval-fast:
	python3 evals/harness/run_evals.py --planes grounding,citation

test-prose:
	python3 -m unittest discover -s tests/prose -p 'test_*.py'

benchmark-prose:
	python3 benchmark/runner.py --mode validate --expect-count 56 --output /tmp/swos-prose-benchmark-validate.json

gate:
	python3 tools/run_gate.py --policy governance/policies/release-gate.policy.json --context examples/worked-example/gate-context.json --work-id work-4f3a91c2-0b7d-4e18-9a52-6c81de7f0a33

governance-check:
	python3 tools/check_governance.py

format:
	python3 -m ruff format --check swos_prose benchmark tools evals tests

lint:
	python3 -m ruff check swos_prose benchmark tools evals tests

coverage:
	python3 -m coverage erase
	python3 -m coverage run --branch --source=swos_prose -m unittest discover -s tests/prose -p 'test_*.py'
	python3 -m coverage json -o coverage.json
	python3 -m coverage report --fail-under=80
	python3 tools/check_coverage.py --coverage-json coverage.json

security:
	python3 -m pip_audit --requirement requirements-dev.lock --strict

sast:
	python3 -m bandit -r swos_prose benchmark tools evals -lll -ii

quality: format lint coverage security sast

ci: validate lint-skills governance-check eval test-prose benchmark-prose quality

clean:
	rm -rf .swos-cache build dist
