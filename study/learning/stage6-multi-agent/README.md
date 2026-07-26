# Stage 6 — 多 Agent 系统

## 阶段目标

理解 Multi-Agent 系统的设计哲学：**不是把任务塞给一个大 Agent，而是把任务拆给多个专职 Agent，通过协调机制让它们协作完成。**

## 章节安排

| 章节 | 主题 | 状态 |
|------|------|------|
| 26 | Swarm — Multi-Agent 基础原理 | ✅ |
| 27 | AutoGen — 多 Agent 对话协作 | ✅ |
| 28 | CrewAI — 角色驱动的任务协作 | 📌 |
| 29 | LangGraph — 生产级 Agent 工作流 | 📌 |
| 30 | 实战项目 + 框架对比 | 📌 |

## 核心问题

本阶段围绕一个核心问题展开：

> 当多个 Agent 协作时，**谁来决定下一轮到谁发言、谁做什么？**

不同框架给出不同答案：

| 框架 | 协调机制 | 适用场景 |
|------|---------|---------|
| Swarm | Handoff（tool 返回 Agent） | 教育理解、简单转交 |
| AutoGen | GroupChat + SpeakerSelector | 对话式协作 |
| CrewAI | Task + Process | 角色驱动的任务流水线 |
| LangGraph | StateGraph | 生产级复杂工作流 |

## 学习路径

1. 先学 Swarm，理解 Multi-Agent 的最小概念集（Agent / Handoff / Routine）
2. 再学 AutoGen，理解多人对话中的协调问题（RoundRobin / LLMSelector / Termination）
3. 然后学 CrewAI，理解角色驱动的任务编排
4. 最后学 LangGraph，理解声明式状态机和生产级容错
5. 实战项目做框架对比，建立选型能力

## 参考资料

- [AgentGuide Multi-Agent 框架对比](https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/06-multi-agent-frameworks.md)
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system)
- [AutoGen 官方文档](https://microsoft.github.io/autogen/stable/)
