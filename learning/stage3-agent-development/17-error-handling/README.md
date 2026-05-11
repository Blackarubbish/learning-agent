# 17 - Agent 错误处理与反思机制

> 📌 待创建 practice 材料

## 目标

让 Agent 在失败时能自我修正（Reflection/Reflexion），而不是直接崩溃。

## 核心概念

| 概念 | 说明 |
|------|------|
| **Reflection** | Agent 根据工具返回的错误信息，自己修正参数或换工具重试 |
| **Reflexion** | 进阶版：Agent 不仅修正当前步，还把失败经验存入"长期记忆"避免再犯 |
| **降级策略** | 连续失败 N 次后，不再死循环，改用人机交互或返回"我做不到" |
| **错误分类** | 区分可重试错误（超时）、参数错误（命名不对）、永久错误（无权限） |

## 错误累积的数学现实

来自 `AgentGuide/resources/agent/ai-agent-production-challenges.md`：

| 单步可靠性 | 5 步成功率 | 10 步成功率 | 20 步成功率 |
|:---:|:---:|:---:|:---:|
| 95% | 77% | 59% | **36%** |
| 99% | 95% | 90% | 82% |

这就是为什么 Agent 步数要尽量少、错误处理要到位。

## 面试高频问题

- Q: "如果 agent 调用工具不正确怎么办？" → 分层错误反馈 + 重试 + 降级
- Q: "工具调用失败后有没有 feedback 策略？" → 结构化错误信息 + Reflection 循环
- Q: "如何防止 Agent 泄露用户隐私或越权操作？" → 权限校验在工具层，不在 prompt 层

## 参考来源

- [AgentGuide](https://github.com/adongwanai/AgentGuide) — Day 20 + 面试题 Q29/Q36/Q45
- `AgentGuide/resources/agent/ai-agent-production-challenges.md`
- [Reflexion 论文](https://arxiv.org/abs/2303.11366)
