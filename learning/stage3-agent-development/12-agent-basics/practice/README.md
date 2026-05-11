# 12 - Agent 核心概念：ReAct 框架

## 目标

理解 Agent 的 "思考-行动" 工作流，从零实现一个 ReAct Agent（不用 LangChain 内置 Agent）。

## Agent 是什么？

```
传统 RAG：用户问题 → 检索 → 生成答案（单向管道）
Agent：  用户问题 → 思考 → 调用工具 → 观察结果 → 再思考 → ... → 最终答案（循环）
```

Agent = LLM + Tools + 思考循环。核心能力是"推理 → 行动 → 观察 → 再推理"，而不仅仅是"回答一个问题"。

## 什么时候不该用 Agent？ ⭐ 关键判断

来自 [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) 的核心原则：

| 用 Agent | 不用 Agent（用 Workflow/普通代码） |
|---------|---------------------------|
| 任务路径不确定，需动态决策 | 业务流程固定，步骤明确 |
| 需要与多个外部工具交互 | 简单的 if-else 逻辑就能搞定 |
| 需要根据中间结果调整策略 | 对延迟和成本要求严格 |
| 开放式探索（如研究、调试） | 数据转换、格式转换等确定性任务 |

**核心原则：简单的 prompt 优化往往比复杂的 Agent 更有效。从最简单的方案开始，按需迭代。**

## 核心概念

| 概念 | 说明 |
|------|------|
| **ReAct** | Reasoning + Acting，交替进行推理和行动 |
| **Tool** | Agent 可以调用的外部能力（计算器、搜索、API 等） |
| **Agent Executor** | 管理 Agent 的思考循环（调用 LLM → 解析输出 → 执行工具 → 反馈结果） |
| **Tool Schema** | 工具的描述和参数定义，LLM 据此决定是否调用 |
| **Reflection** | 工具调用失败或格式错误时，Agent 根据错误信息自我修正（第 17 章深入） |

## 进阶知识预览

本章只实现基础 ReAct 循环。下面这些概念会在后续章节展开，但你需要在动手时就建立意识：

**1. 错误累积**：如果每一步有 95% 可靠性，20 步后成功率只有 36%。这就是为什么 Agent 步数要尽量少（本章 `max_steps=5`）。

**2. 反思（Reflection）**：当你写的 Agent 输出格式错误时，它能否根据错误提示自我修正？这是本章的隐藏练习——观察 `parse_error` 发生后 Agent 的行为。

**3. 工具反馈设计**：工具返回什么信息给 Agent？太简略 Agent 无法判断，太详细浪费 token。本章的 `string_tool` 返回自然语言而不是简单值，就是这个考虑。

## 前置知识

- 完成 LangChain 基础（02 章）
- 理解 Prompt Template 和 Output Parser

## 参考资源

- [AgentGuide Week 3](https://github.com/adongwanai/AgentGuide) — `docs/05-roadmaps/learning-roadmap-development.md`
- [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [ReAct 论文](https://arxiv.org/abs/2210.03629)
- 本项目 `AgentGuide/resources/agent/` 目录

## 运行方式

```bash
make run f=learning/stage3-agent-development/12-agent-basics/practice/starter.py
```
