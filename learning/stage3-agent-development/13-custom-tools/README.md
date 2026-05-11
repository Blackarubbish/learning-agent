# 13 - 自定义工具开发

> 📌 待创建 practice 材料

## 目标

不只是"写个函数"，而是设计 **AI 友好的工具接口**。Agent 生产实践揭示：**70% 的工作是工具工程**，AI 只完成 30%。

## 核心概念（来自 AgentGuide 生产实践）

| 概念 | 说明 |
|------|------|
| **工具反馈设计** | 工具返回的信息必须让 LLM 能据此做出下一步决策 |
| **信息抽象** | 数据库查回 10000 行，Agent 只需要前 5 行 + 总数 |
| **状态反馈** | 操作部分成功时，如何告知 Agent 进度？ |
| **错误恢复接口** | 工具失败时返回什么信息，让 Agent 知道如何修正？ |

## 反面案例

如果工具只是 `return raw_response`，Agent 会因为上下文过载而无法决策——太多 token 冲垮推理能力。

## 参考来源

- [AgentGuide 学习路线](https://github.com/adongwanai/AgentGuide) — Day 16
- `AgentGuide/resources/agent/ai-agent-production-challenges.md` — 第三部分"工具工程现实墙"
- [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
