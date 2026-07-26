# Agent 模式选择器

本仓库是 uv workspace，包含两个项目：

- `study/`：课程学习项目，包含 `common/`、`learning/`、`handwrite/` 等课程代码。
- `practice/`：动手实践项目，用于 Hello-Agents、AgentScope、LangGraph 等自由实验。

## 每次对话启动流程

Agent 必须先判断用户当前意图：

1. **学习模式**：用户提到具体章节、复习、starter/solution、费曼笔记、STUDY_PROGRESS、CONCEPT_MAP、某个 stage 等。
2. **实践模式**：用户提到练习、实验、Hello-Agents、AgentScope、LangGraph、做项目、跑示例、调试代码等。
3. 如果意图不明确，**必须直接询问**：
   > "你今天想学习 `study/` 里的课程，还是在 `practice/` 里做实验？"

## 模式对应的规则文件

- **学习模式**：读取 `study/AGENT.md`，遵循其中的学习教练规则。
- **实践模式**：读取 `practice/AGENT.md`，遵循其中的动手实践规则。

## 通用命令

```bash
# 同步 workspace 环境
uv sync

# 运行 study 中的练习
make run-study f=learning/stage1-rag-basics/01-fastapi/practice/starter.py

# 运行 practice 中的示例
make run-practice f=examples/chapter6_agentscope/hello_agentscope.py

# 格式化和 lint
make format
make check
```

## 环境变量

- `study/.env`：学习项目 API keys
- `practice/.env`：实践项目 API keys

> 不要直接修改本文件去写学习或实践规则。请分别维护 `study/AGENT.md` 和 `practice/AGENT.md`。
