.PHONY: help validate lint-skills eval eval-fast test-prose audit-pack gate governance-check ci clean

help:
	@echo "SWOS - make targets"
	@echo "  validate     Validate every artefact against the frozen JSON Schemas"
	@echo "  lint-skills  Enforce the six-field Agent Skills frontmatter constraint"
	@echo "  eval         Run the full evaluation harness (all eight planes)"
	@echo "  eval-fast    Run grounding + citation planes only (pre-commit)"
	@echo "  test-prose   Run SWOS Prose semantic-delta unit tests"
	@echo "  ci           validate + lint-skills + governance-check + eval + prose tests"

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

gate:
	python3 tools/run_gate.py --policy governance/policies/release-gate.policy.json --context examples/worked-example/gate-context.json --work-id work-4f3a91c2-0b7d-4e18-9a52-6c81de7f0a33

governance-check:
	python3 tools/check_governance.py

ci: validate lint-skills governance-check eval test-prose

clean:
	rm -rf .swos-cache build dist
