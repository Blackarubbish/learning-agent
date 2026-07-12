# 03 — 手写 Plan-and-Solve Agent

## 目标

从零实现 Plan-and-Solve 模式：先制定完整计划，再逐步执行。

## 核心概念

Plan-and-Solve 分两个阶段：

- **Plan 阶段**：LLM 分析任务，输出一个步骤列表（如 1.搜索 X 2.分析结果 3.给出结论）
- **Solve 阶段**：按计划逐步执行，每步执行后更新状态，遇到问题可调整计划

与 ReAct 的区别：ReAct 是"边想边做"，Plan-and-Solve 是"先想清楚全貌再一步步落地"。后者适合步骤明确的任务，减少 LLM 调用次数。

## 你需要实现

1. **Plan Prompt**：让 LLM 把用户任务拆解为步骤列表
2. **计划解析**：从 LLM 输出中提取步骤（如 JSON 数组 `[{"step": 1, "action": "search", "query": "..."}, ...]`）
3. **Solve 循环**：按顺序执行每个步骤，观察结果，决定是否调整计划
4. **最终综合**：所有步骤执行完后，让 LLM 基于结果生成最终答案

## 运行

```bash
uv run handwrite/03-plan-and-solve/starter.py
```
