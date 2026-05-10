# 12 - Agent 核心概念：ReAct 框架

## 目标

理解 Agent 的 "思考-行动" 工作流，用 LangChain 构建第一个多工具 Agent。

## Agent 是什么？

```
传统 RAG：用户问题 → 检索 → 生成答案（单向）
Agent：  用户问题 → 思考 → 调用工具 → 观察结果 → 再思考 → ... → 最终答案（循环）
```

Agent = LLM + Tools + 思考循环。它不只是"回答"，而是"推理 → 行动 → 观察 → 再推理"。

## 核心概念

| 概念 | 说明 |
|------|------|
| **ReAct** | Reasoning + Acting，交替进行推理和行动 |
| **Tool** | Agent 可以调用的外部能力（计算器、搜索、API 等） |
| **Agent Executor** | 管理 Agent 的思考循环（调用 LLM → 解析输出 → 执行工具 → 反馈结果） |
| **Tool Schema** | 工具的描述和参数定义，LLM 据此决定是否调用 |

## 前置知识

- 完成 LangChain 基础（02 章）
- 理解 LCEL 和 Prompt Template

## 运行方式

```bash
make run f=learning/stage3-agent-development/12-agent-basics/practice/starter.py
```
