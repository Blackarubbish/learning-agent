# Learning Agent

This repository is a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) for learning and practicing LLM Agent development.

## Workspace Structure

```text
learning-agent/
├── study/          # Learning project following the LLM Agent curriculum
└── practice/       # Hands-on practice project for Hello-Agents and other frameworks
```

## Setup

```bash
# Sync the shared workspace environment
uv sync

# Run study practice file
make run-study f=learning/stage1-rag-basics/01-fastapi/practice/starter.py

# Run practice example
make run-practice f=examples/chapter6_agentscope/hello_agentscope.py

# Lint and format
make check
make format
```

## Environment Variables

Study and practice projects keep their own `.env` files:

```bash
cp study/.env.example study/.env
# Edit study/.env with your API keys

cp practice/.env.example practice/.env
# Edit practice/.env with your API keys
```

## Notes

- `study/` contains the original learning curriculum, including `common/`, `learning/`, and `handwrite/`.
- `practice/` is a standalone editable package for hands-on experiments.
- `ref/hello-agents/` is a cloned reference repository (gitignored).
