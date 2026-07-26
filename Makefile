.PHONY: sync-rules lint lint-fix format format-check check run-study run-practice

sync-rules:
	cp CLAUDE.md AGENT.md
	@echo "Synced CLAUDE.md → AGENT.md"

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

# Run a practice file inside the study project.
# Usage: make run-study f=learning/stage1-rag-basics/01-fastapi/practice/starter.py
run-study:
	PYTHONPATH=. uv run --directory study python $(f)

# Run an example file inside the practice project.
# Usage: make run-practice f=examples/chapter6_agentscope/hello_agentscope.py
run-practice:
	uv run --directory practice python $(f)
