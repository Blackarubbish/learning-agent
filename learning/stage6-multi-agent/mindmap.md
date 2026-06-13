# Stage 6 — 多 Agent 系统

```mermaid
mindmap
  root((多 Agent 系统))
    26-Swarm ✅
      Agent = 角色 + instructions + tools
      Handoff = tool 返回 Agent 对象
      Routine = 预设流程，减少 LLM 调用
      Swarm 是教育性框架，代码仅 ~500 行
    27-AutoGen ✅
      GroupChat = 共享上下文的对话容器
      RoundRobinSelector = 固定轮询
      LLMSelector = LLM 动态选人
      TerminationCondition = 可组合终止
      AgentTool = 把 Agent 包装成 Tool
    28-CrewAI 📌
      Agent = role + goal + backstory
      Task = desc + expected_output
      Crew = agents + tasks + process
      Sequential / Hierarchical 两种流程
    29-LangGraph 📌
      StateGraph = 声明式状态机
      Node = 处理函数
      ConditionalEdge = 条件路由
      Checkpoint = 断点续跑
    30-实战项目 📌
      框架对比：Swarm / AutoGen / CrewAI / LangGraph
      选型依据：场景复杂度 / 可控性 / 成本
```
