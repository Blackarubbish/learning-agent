# 17 - Agent 错误处理与反思机制

> ✅ practice 材料已创建（starter.py + solution.py）

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

## 学习资料总结

### 核心阅读

| 资料 | 来源 | 关键要点 |
|------|------|---------|
| AI Agent 生产环境实践 | `AgentGuide/resources/agent/ai-agent-production-challenges.md` | 错误指数累积数学、Token 二次成本、工具工程 70% 工作量、成功 Agent 的共同模式（限定上下文+可验证操作+人类决策点） |
| 12-Factor Agent — Factor 9 | `AgentGuide/docs/02-tech-stack/12-factor-agent-architecture.md` | 错误信息压缩到上下文窗口（Compact Errors）：只给分类+摘要+修复建议，不堆栈追踪；LLM 能读取并自我修复 |
| 面试题 Q29/Q36/Q45 | `AgentGuide/docs/04-interview/03-agent-questions.md` | 工具调用失败反馈策略、子 Agent 回复不对时的反思+限制次数、超时/空返回的重试/降级/用户澄清机制 |
| Reflexion 论文 | https://arxiv.org/abs/2303.11366 | Language Agents with Verbal Reinforcement — 将失败经验存入长期记忆避免跨会话重复犯错 |

### 设计原则

1. **错误分三类，不是两类**：可重试（超时）→ 原参数重试；参数错误 → 修正参数重试；永久（无权限）→ 立即放弃
2. **错误反馈要结构化**：类型 + 摘要 + 修复建议，不要裸堆栈
3. **降级阈值独立于重试次数**：连续失败触发降级（防止死循环），总重试次数控制 Token 成本
4. **权限校验在工具层**：不在 prompt 层，因为 prompt 可被绕过

## 参考来源

- [AgentGuide](https://github.com/adongwanai/AgentGuide) — Day 20 + 面试题 Q29/Q36/Q45
- `AgentGuide/resources/agent/ai-agent-production-challenges.md`
- `AgentGuide/docs/02-tech-stack/12-factor-agent-architecture.md` — Factor 9 (Compact Errors)
- [Reflexion 论文](https://arxiv.org/abs/2303.11366)
