.PHONY: help lint type test check build clean

help: ## Show targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

lint: ## ruff check + format check
	uv run ruff check src tests
	uv run ruff format --check src tests

type: ## mypy (strict) + pyright on tests
	uv run mypy src tests
	uv run pyright tests

test: ## full suite, including the real-git slow tier
	uv run pytest -m ""

check: lint type test ## all gates

build: ## wheel + sdist
	uv build

clean:
	rm -rf dist .pytest_cache .mypy_cache .ruff_cache
