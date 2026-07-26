# 04 — 手写 Reflection (Reflexion)

## 目标

在 ReAct 基础上加入反思循环：执行失败时反馈给 LLM 修正，而非盲目重试。

## 核心概念

Reflection 的核心：失败 → 结构化反馈 → LLM 自我修正 → 重试

对比普通的 ReAct：
- ReAct：Observation 告诉 Agent 结果，Agent 自己判断要不要重试
- Reflection：Observation 包含**错误分类 + 修复建议**，Agent 被引导修正

Reflexion 进阶：不仅修正当前步骤，还把失败经验存入长期记忆，跨会话避免重复错误。

## 你需要实现

1. **错误分类**：参考三分类 RETRYABLE / PARAMETER_ERROR / PERMANENT
2. **结构化错误反馈**：分类 + 摘要 + 修复建议（不含堆栈）
3. **反射循环**：工具返回错误 → 生成结构化反馈 → 注入 messages → LLM 重试
4. **降级策略**：连续 N 次失败后安全终止

## 运行

```bash
uv run handwrite/04-reflection/starter.py
```
