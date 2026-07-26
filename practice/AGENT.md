# Agent 实践规则 v1

> AI Agent 行为指令集（实践模式）：帮助用户在 `practice/` 中自由实验 Hello-Agents、AgentScope、LangGraph 等框架。

---

## 0. 启动必读

**每次对话开始时，Agent 必须：**

1. 确认用户今天的实践目标（跑哪个示例、实验哪个框架、做哪个小项目）
2. 检查 `practice/.env` 是否包含必要的 API keys（如 OPENAI_API_KEY、DASHSCOPE_API_KEY 等）
3. 选择对应项目的工作目录：`practice/`

---

## 1. 实践模式

### 1.1 跑示例

用户说"跑一下 XX 示例"时：
- 找到 `practice/examples/` 下对应文件
- 用 `make run-practice f=...` 运行
- 解释输出，帮用户理解关键步骤

### 1.2 做实验

用户说"我想试试 XX"时：
- 在 `practice/notebooks/` 或 `practice/examples/` 新建实验文件
- 提供最小可运行代码，让用户先看到效果
- 再引导用户修改参数、观察变化

### 1.3 做小项目

用户说"做个项目"时：
- 在 `practice/src/hello_agents_practice/` 添加模块
- 在 `practice/examples/` 写入口脚本
- 用 `practice/tests/` 写简单断言验证

---

## 2. 项目结构

```
practice/
├── src/hello_agents_practice/   # 可复用模块
├── examples/                      # 可独立运行的示例脚本
├── notebooks/                     # Jupyter 实验笔记
├── tests/                         # 简单测试
├── .env                           # API keys（不提交）
└── README.md                      # 项目说明
```

---

## 3. 代码编写规则

### 3.1 消除摩擦

示例脚本开头建议加载环境变量：

```python
from hello_agents_practice.utils import load_env

load_env()
```

### 3.2 文件组织

- `examples/`：每个示例一个文件，文件名说明主题，如 `chapter6_agentscope/hello_agentscope.py`
- `src/hello_agents_practice/`：复用工具（如 `load_env`、`retry`、`format_messages`）
- `notebooks/`：探索性实验，保留输出以便复盘
- `tests/`：对核心工具写简单断言

### 3.3 编码规范

- 双引号，行宽 100，文件末尾一个空行
- import 按 标准库 → 第三方库 → 本地模块 排序，组内字母序
- 使用 `list`/`dict` 现代语法，避免未使用的 import 和变量
- 项目用 ruff 格式化和 lint（配置在根 `pyproject.toml`），`make lint` / `make format`

---

## 4. 交互风格

- **直接给可运行代码**：实践模式以动手为主，先让用户跑起来
- **解释关键原理**：运行后解释"这一步在做什么"，而不是"这行代码是什么"
- **鼓励修改**：给出 2-3 个可调整的参数，让用户自己实验
- **记录实验**：建议用户在 `practice/notebooks/` 或示例注释中记录观察结果

---

## 5. 常用命令

```bash
# 运行 practice 示例
make run-practice f=examples/chapter6_agentscope/hello_agentscope.py

# 同步 workspace 环境
uv sync

# 格式化和 lint
make format
make check
```
