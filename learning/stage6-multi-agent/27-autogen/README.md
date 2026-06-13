# 27 - AutoGen：多 Agent 对话协作

## 目标

理解 AutoGen 的核心理念：**多个 Agent 在同一个 GroupChat 中对话协作**，掌握三种关键机制：

- **GroupChat** = 共享上下文的对话容器
- **Speaker Selection（发言人选择）** = 决定下一轮到谁说话
  - `RoundRobin`：固定轮询，简单可控
  - `Selector`：由 LLM 动态选择最合适的 Agent
- **Termination（终止条件）** = 防止对话无限进行
- **AgentTool** = 把 Agent 包装成 Tool，实现递归组合

## 核心概念

### 为什么学完 Swarm 再学 AutoGen？

Swarm 教你理解 Multi-Agent 的底层三件事：角色、Handoff、上下文传递。AutoGen 在此基础上增加了一个关键问题：

> 当 3 个以上 Agent 需要协作时，**谁来决定下一轮到谁说话**？

这是 Multi-Agent 的**协调问题（Coordination）**。AutoGen 的答案是：把协调策略做成可插拔组件。

### AutoGen AgentChat 的设计哲学

AutoGen 把多 Agent 协作抽象成三层：

```
Agents（角色 + 工具）
  ↓ 组成
Teams（协作模式：GroupChat）
  ↓ 由
Termination（终止条件）控制结束
```

**关键设计**：协调策略与 Agent 能力解耦。同样的三个 Agent，可以用 RoundRobin 轮流发言，也可以用 Selector LLM 动态选人，甚至可以用 Swarm 风格的 tool-based 路由。

### GroupChat 的两个经典模式

#### 1. RoundRobinGroupChat —— 固定轮询

```python
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination

# 三个 Agent 轮流发言：A → B → C → A → B → ...
team = RoundRobinGroupChat(
    participants=[researcher, analyst, writer],
    termination_condition=MaxMessageTermination(max_messages=10)
        | TextMentionTermination("TERMINATE"),
)
```

**适用场景**：流程明确、角色之间需要充分讨论、不需要动态调度。

#### 2. SelectorGroupChat —— LLM 动态选人

```python
from autogen_agentchat.teams import SelectorGroupChat

team = SelectorGroupChat(
    participants=[researcher, analyst, writer],
    model_client=model_client,  # 专门用于选人的 LLM
    selector_prompt=selector_prompt,  # 告诉 LLM 怎么选
    allow_repeated_speaker=False,  # 是否允许同一个人连续发言
    termination_condition=TextMentionTermination("TERMINATE"),
)
```

**适用场景**：任务不确定，需要 orchestrator 根据上下文判断谁最有资格下一步发言。

> ⚠️ 关键认知：Selector LLM 和任务 LLM 可以是同一个，但也可以分开。选人的 LLM 通常只需要 cheap/fast 模型。

### 终止条件（Termination）

AutoGen 把终止条件也做成了可组合组件：

| 终止条件 | 含义 |
|---------|------|
| `MaxMessageTermination(n)` | 发言达到 n 条后终止 |
| `TextMentionTermination("TERMINATE")` | 某条消息包含特定文本时终止 |
| `HandoffTermination(target="user")` | 转交给人类时终止 |

可以组合：

```python
termination = MaxMessageTermination(10) | TextMentionTermination("TERMINATE")
```

### AgentTool：把 Agent 包装成 Tool

AutoGen 允许把一组 Agent 封装成一个 Tool，供另一个 Agent 调用：

```python
from autogen_agentchat.tools import AgentTool

# 把 research_team 包装成一个 Tool
research_tool = AgentTool(
    name="research_team",
    description="调用研究团队完成资料搜集",
    team=research_team,
)

# 主 Agent 可以像调用普通工具一样调用整个子团队
manager = AssistantAgent(
    name="manager",
    model_client=model_client,
    tools=[research_tool],
)
```

**价值**：实现递归组合。上层 Agent 不需要知道子团队内部有几个人、怎么协调，只把它当做一个能力更强的工具。

### 什么时候用 Multi-Agent？（Anthropic 生产经验）

来自 Anthropic [How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system)：

**适合**：
- 任务可以拆成多个独立方向并行探索
- 信息量超过单个上下文窗口
- 需要与大量复杂工具交互

**不适合**：
- 所有 Agent 必须共享同一上下文
- 子任务之间依赖关系复杂
- 任务价值不足以支付 15× 的 token 成本

**推荐架构**：Orchestrator-Workers
- 一个 lead agent 分析任务、制定策略
- 多个 subagent 并行执行、过滤信息
- 最后由 orchestrator 汇总

## 实验设计

由于 `autogen-agentchat` 默认强依赖 OpenAI 兼容接口，本实验用纯 Python 手动实现一个**极简 AutoGen-style GroupChat**，直接复用你现有的 DeepSeek/Zhipu LLM。

### 实验目标

1. 实现 `GroupChat` 容器（管理 participants + shared history）
2. 实现 `RoundRobinSelector`（固定轮询）
3. 实现 `LLMSelector`（由 LLM 根据上下文选择下一个发言人）
4. 实现 `TerminationCondition`（MaxMessage + TextMention 组合）
5. 构建「研究员 → 分析师 → 写手」的协作流程
6. 验证：Selector LLM 能在合适时机选择正确角色

## 前置条件

```bash
# 复用现有的 common 模块，无额外依赖
uv sync  # 或 pip install -e .
```

## 学习资料总结

### 官方文档

| 资料 | 链接 | 重点 |
|------|------|------|
| AutoGen AgentChat 快速开始 | [quickstart.html](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/quickstart.html) | 安装、`AssistantAgent`、`Console`、`run_stream` |
| Selector Group Chat 教程 | [selector-group-chat.html](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/selector-group-chat.html) | LLM 动态选人机制 |
| Teams API 参考 | [autogen_agentchat.teams](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.teams.html) | `RoundRobinGroupChat`、`SelectorGroupChat` 参数 |
| Termination 教程 | [termination.html](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html) | 终止条件类型与组合 |

### 工程实践

| 资料 | 来源 | 重点 |
|------|------|------|
| How we built our multi-agent research system | Anthropic | Orchestrator-Workers 架构、15× token 成本、何时用 multi-agent |
| 12-Factor Agent — Factor 9 | AgentGuide `docs/02-tech-stack/12-factor-agent-architecture.md` | 错误信息压缩到上下文窗口 |
| Multi-Agent 面试题 Q9 | AgentGuide `docs/04-interview/03-agent-questions.md` | 多 Agent 优势 vs 引入的复杂性 |

### 关键 API 速查

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.tools import AgentTool
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
```

## 参考来源

- [AutoGen 官方文档](https://microsoft.github.io/autogen/stable/)
- [AutoGen GitHub](https://github.com/microsoft/autogen)
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system)
- [AgentGuide 面试题 Q9](https://github.com/adongwanai/AgentGuide/blob/main/docs/04-interview/03-agent-questions.md)
