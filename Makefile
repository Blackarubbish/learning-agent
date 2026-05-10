.PHONY: sync-rules lint format check run

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

# 运行任意 practice 文件，自动设置 PYTHONPATH
# 用法: make run f=learning/stage2-advanced-rag/11-weekly-summary/practice/starter.py
run:
	PYTHONPATH=. uv run python $(f)
