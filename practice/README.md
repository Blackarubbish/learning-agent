# Hello-Agents Practice

This is the hands-on practice project for the `learning-agent` workspace.

## Structure

```text
practice/
├── src/hello_agents_practice/    # Shared utilities
├── examples/                      # Chapter-by-chapter examples
│   ├── chapter6_agentscope/
│   └── chapter7_framework/
├── notebooks/                     # Jupyter experiments
└── tests/                         # Practice tests
```

## Quick Start

```bash
# From the workspace root
uv run --directory practice python examples/chapter6_agentscope/hello_agentscope.py

# Or use the root Makefile
make run-practice f=examples/chapter6_agentscope/hello_agentscope.py
```

## Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys
```
