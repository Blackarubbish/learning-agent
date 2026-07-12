# 05 — 手写 ReWOO (Reasoning WithOut Observation)

## 目标

实现 ReWOO 模式：一次性规划所有工具调用，构建依赖图，并行执行，无需中间 LLM 观察。

## 核心概念

ReAct 的问题是每调用一次工具就要 LLM 观察一次结果（N 次工具 = N 次 LLM 调用）。

ReWOO 的改进：
1. **Planner**：一次性列出所有需要的工具调用，标注参数和依赖关系
2. **Worker**：根据依赖图并行执行工具（无依赖的并行，有依赖的串行）
3. **Solver**：所有工具执行完后，LLM 综合结果生成答案

关键优势：LLM 只调用 2 次（Planner + Solver），工具调用次数不变但 LLM 省了中间观察。

## 你需要实现

1. **Planner**：LLM 生成工具调用计划，包含依赖标注（工具 B 的输入依赖工具 A 的输出）
2. **依赖图解析**：构建 DAG，识别哪些工具可以并行执行
3. **Worker 执行引擎**：并行执行无依赖的工具，按序执行有依赖的工具
4. **Solver**：所有结果汇总后，LLM 生成最终答案

## 运行

```bash
uv run handwrite/05-rewoo/starter.py
```
