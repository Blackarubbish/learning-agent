# 12 - Agent 核心概念：ReAct 框架

> ✅ practice 材料已创建（starter.py + solution.py）

## 目标

理解 Agent 与 RAG 的本质区别，从零实现一个 ReAct Agent（不用 LangChain 内置 Agent）。

## 核心概念

| 概念 | 说明 |
|------|------|
| **ReAct** | Reasoning + Acting，交替进行推理和行动 |
| **Tool** | Agent 可以调用的外部能力（计算器、搜索、API 等） |
| **Agent Executor** | 管理思考循环（调用 LLM → 解析输出 → 执行工具 → 反馈结果） |
| **Reflection** | 工具调用失败或格式错误时，Agent 根据错误信息自我修正（第 17 章深入） |

## 什么时候不该用 Agent？

来自 [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)：

| 用 Agent | 不用 Agent |
|---------|-----------|
| 任务路径不确定，需动态决策 | 业务流程固定，步骤明确 |
| 需要与多个外部工具交互 | 简单的 if-else 逻辑就能搞定 |
| 需要根据中间结果调整策略 | 对延迟和成本要求严格 |

**核心原则：简单的 prompt 优化往往比复杂的 Agent 更有效。**

## 练习文件

| 文件 | 说明 |
|------|------|
| `practice/starter.py` | 骨架代码 + TODO，实现 calculator/string/datetime 三个工具 |
| `practice/solution.py` | 完整参考实现，含 SimpleAgent + 自检断言 |

## 运行方式

```bash
make run f=learning/stage3-agent-development/12-agent-basics/practice/starter.py
```

## 参考来源

- [AgentGuide](https://github.com/adongwanai/AgentGuide) — Week 3 Day 15
- [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [ReAct 论文](https://arxiv.org/abs/2210.03629)
- `AgentGuide/resources/agent/ai-agent-production-challenges.md`
