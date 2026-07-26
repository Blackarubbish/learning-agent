# 02 — 手写 ReAct Agent

## 目标

从零实现 ReAct（Reasoning + Acting）循环，不依赖任何 Agent 框架。

## 前置知识

- 01-llm_client：LLMClient 流式调用

## 核心概念

ReAct 循环 = Thought → Action → Observation → Thought → ... → Final Answer

- **Thought**：LLM 分析当前状态，决定下一步行动
- **Action**：调用工具（搜索、计算等）
- **Observation**：工具返回结果，作为下一轮 Thought 的输入
- **Final Answer**：LLM 认为任务完成时输出最终答案

## 你需要实现

1. **工具定义**：至少 2 个工具（如搜索、计算器），包含 `name`、`description`、`parameters`
2. **ReAct Prompt 模板**：指导 LLM 按 Thought/Action/Observation 格式输出
3. **输出解析**：从 LLM 回复中提取 Thought、Action、Action Input
4. **执行循环**：`while step < max_steps`，解析 → 执行工具 → 拼接 Observation → 继续
5. **终止检测**：识别 "Final Answer" 标记

## 运行

```bash
uv run handwrite/02-react/starter.py
```

## 参考

- 复用 `handwrite/01-llm_client/01-llm_client.py` 中的 LLMClient
