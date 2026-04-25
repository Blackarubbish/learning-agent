.PHONY: sync-rules lint format check

sync-rules:
	cp CLAUDE.md AGENT.md
	@echo "Synced CLAUDE.md → AGENT.md "

lint:
	uv run ruff check

lint-fix:
	uv run ruff check --fix

format:
	uv run ruff format

format-check:
	uv run ruff format --check

check:
	uv run ruff check
	uv run ruff format --check
