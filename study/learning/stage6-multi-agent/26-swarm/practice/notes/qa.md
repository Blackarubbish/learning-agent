# 26 - Swarm: Multi-Agent 基础原理

## 一、它解决什么问题？

单个 Agent 包揽一切 → system prompt 越来越长、职责混杂（一个 prompt 里既要写客服逻辑又要写技术逻辑）。Swarm 的思路：**角色拆分 + Handoff 转交**——每个 Agent 只做一件事，超出能力范围就转给更合适的 Agent。

和微服务拆分的逻辑一致：职责单一、边界清晰、上下文不污染。

## 二、核心原理（用类比解释）

Handoff 就是普通 tool function，返回值是目标 Agent 对象。框架唯一做的就是 `isinstance(result, Agent)` ——检测是否是 Agent 对象，是就切换。

类比：公司内线转接电话。客服接到技术问题时，不是挂断让用户重新打，而是按"转接键"（handoff tool）→ 电话连到技术支持，技术支持能看到之前的所有通话记录（history）。

关键设计：**History 共享不重置**。切换 Agent 只换了 current_agent 变量，history list 原封不动——新 Agent 能看到完整对话链。

## 三、反面案例 —— 如果没有 Handoff 机制，会发生什么？

- **单 Agent 硬扛**：客服的 system prompt 里塞满技术问题的处理规则 → prompt 臃肿 → LLM 推理质量下降（上下文污染）
- **硬编码路由**：`if "API" in question → 转技术` → 规则维护成本高，边界 case 漏判
- **多 Agent 但无上下文传递**：每次转交丢失对话历史 → 用户需要重复描述问题

## 四、我能用它做什么？

1. **多级客服系统**：售前 → 售后 → 技术支持，每个角色只需写自己的 instructions
2. **代码审查流水线**：语法检查 Agent → 安全审查 Agent → 性能分析 Agent，发现专属问题自动转交
3. **信息检索链**：通用搜索 Agent（80% 问题） → 专业领域 Agent（学术/法律/医疗），按需转交

## 五、和已有知识的关联

- [[CONCEPT_MAP#12 Agent / ReAct]]：SimpleAgent 是"一人包揽"，Swarm 是"分工协作"。核心循环完全一样（LLM → tool → 追加消息），唯一增量是 `isinstance(result, Agent)` 检测
- [[CONCEPT_MAP#13 信息抽象]]：职责单一让每个 Agent 的 system prompt 更短更精确，上下文污染更少——和工具输出截断/摘要的设计目标一致
- [[CONCEPT_MAP#17 错误处理]]：终端 Agent 无 handoff 防止无限转交，和降级策略（防止死循环）同构
- [[CONCEPT_MAP#22 批处理优化]]：Routine 模式预定义流程减少 LLM 调用，和批处理追求减少 API 往返的目标一致

## 六、我还困惑的地方（后续补充）

- Swarm 没有并发控制：如果 3 个 Agent 同时判断自己处理不了，会不会互相踢皮球？
- Handoff 时是否应该截断 history 以减少 token 消耗？（Stage 3 的信息抽象原则在这里适用吗？）
- 和 LangGraph 的 ConditionalEdge 比，LLM 自主路由 vs 代码硬编码路由的取舍边界在哪？
