# 18 - 周度总结与 Agent 项目实战

> 📌 待创建 practice 材料

## 目标

把 Week 3 学的全部内容整合为一个"研究助手 Agent"：能检索 RAG（Week 2 能力）+ 能调用工具（Week 3 能力）。

## 总结维度

| 维度 | 回顾内容 |
|------|---------|
| **ReAct 循环** | Thought → Action → Observation 机制是否真正理解 |
| **工具工程** | 你写的工具返回格式是否让 Agent 能正确决策 |
| **Memory** | 对话历史管理的分层设计 |
| **错误处理** | Reflection 是否生效，降级策略是否合理 |
| **Agent 评估** | 任务成功率、步数效率、工具调用准确率 |

## Agent 评估指标

来自 AgentGuide 的 `evaluation-harness.md`：

| 指标 | 含义 | 好 Agent 的标准 |
|------|------|:---:|
| 任务成功率 | 最终回答是否正确 | > 90% |
| 步数效率 | 完成任务用了多少步 | 越少越好 |
| 工具调用准确率 | 是否选了正确的工具 + 参数 | > 85% |
| 格式错误率 | parse_error 发生次数 | < 5% |

参考：AgentBench、GAIA 评估框架。

## 综合思考题（预习）

1. 你的 Agent 在什么时候不需要用 ReAct？把问题直接交给 RAG 会不会更好？
2. 回顾 `AgentGuide/resources/agent/ai-agent-production-challenges.md`，用一个具体例子解释为什么"限制步数"比"提高单步可靠性"更实际。
3. 如果要让这个 Agent 在生产环境跑，你会加哪些约束？（提示：max_steps、人工确认、降级输出）

## 框架选型预览

Week 6 会深入 Multi-Agent 框架。先用 LangChain Agent 手撕后，理解为什么需要 LangGraph/AutoGen/CrewAI 更高级的编排能力。

## 参考来源

- [AgentGuide](https://github.com/adongwanai/AgentGuide) — Day 21
- `AgentGuide/resources/agent/evaluation-harness.md`
- `AgentGuide/resources/agent/frameworks.md`
- `AgentGuide/docs/04-interview/03-agent-questions.md`
