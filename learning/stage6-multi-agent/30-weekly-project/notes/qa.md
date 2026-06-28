# 第 30 章 — 多 Agent 框架实战对比

> 完成项目实现和测试后，用自己的话回答以下问题。

## 一、它解决什么问题？

（提示：用两个框架实现同一个业务场景，你发现了什么？框架选型这件事，本质上在解决什么问题？）
本质上是在降低手动对接llm的输入输出和编排llm复杂度。对于客服这个场景，如果依靠纯代码调用llm，那么需要自己手动处理llm的返回，编排流程。而CrewAI和LangGraph给了用户两种编排llm的工作方案，用来解决上述的问题


## 二、核心原理（用类比解释）

（提示：如果把 CrewAI 和 LangGraph 分别比喻成两种工厂产线设计，它们各像什么？）
LangGraph比较像一个装配间，把一个零件

CrewAI比较像一个工厂，把需求和开发方式告诉这个工厂，就能得到结果，而如何得到这个结果其实用户感知的不是很大

LangGraph则是一个更加清晰的工厂，这个工厂做的每一个操作你都可以看得到。


## 三、反面案例 —— 如果选错了框架，会发生什么？

（提示：想想如果你用 LangGraph 做一个简单的角色流水线、或用 CrewAI 做一个复杂条件路由的状态机，各会遇到什么麻烦？）

CrewAI我在使用的时候就发现了，判断回复是否正确，是由用户手动处理的。那么当场景更加复杂的情况下，用户手写的代码依然会很多，而且无法解耦，对于代码维护和开发效率来说是比较糟糕的

而LangGraph对于一些简答的流水线，如果能简单编排那么根本不需要用到LangGraph，因为需要定义state还不如直接用CrewAI一把梭




## 四、我能用它做什么？（3 个具体场景）

（提示：基于你在这个项目中的体验，举 3 个真实业务场景，分别说明该用哪种框架，为什么。）

1.LangGraph: 适合复杂的多场景流转，比如审批流，多条件分发的复杂场景
2.CrewAI: 适合简单的状态较少的编排场景，比如代码审查，流程一定是 确认代码质量，运行代码测试，提交报告
3.AutoGen: 适合多个模型一起讨论的头脑风暴场景

## 五、和已有知识的关联

本章的客服工单系统把之前学的东西串成了一条线：

**Stage 1-2 RAG 检索 → 本项目的知识库检索**：之前的 RAG 是向量检索 + 关键词检索，本项目在 FR-2 中用 LLM 做语义匹配替代了向量数据库。本质上都是在"从一堆文档中找出和用户问题最相关的那几条"，只是这个项目规模小，用 LLM 直接判断就够了，不需要 embedding + FAISS。

**Stage 3 Agent Tool Calling → 本项目的 Multi-Agent 协作**：Stage 3 学的是单个 Agent 的 ReAct 循环——一个人拿着工具干活，思考→行动→观察→再思考。本项目的 Multi-Agent 是把一个 Agent 的思考链拆成多个 Agent 各管一段：分类的人不管检索，检索的人不管回复。从"一个人干所有活"变成了"团队分工协作"。核心变化是协调成本（Handoff / context 传递 / 审核退回）替代了 ReAct 循环中的工具调用成本。

**Stage 6 四个框架 → 本项目的两框架实战**：
- Swarm（26）的 Handoff 思想 → 如果本项目用 Swarm 实现，就是把客服工单在分类/检索/回复/审核四个 Agent 之间转交
- AutoGen（27）的 GroupChat 思想 → 如果本项目用 AutoGen，所有 Agent 在一个群聊里讨论，LLM 选择谁发言
- CrewAI（28）的 Agent/Task/Crew 三段式 → 本项目 FR-5a 直接用了这套 API，角色定义 + 任务依赖 + 顺序执行
- LangGraph（29）的 StateGraph → 本项目 FR-5b 直接用了 Node/Edge/ConditionalEdge，用状态机替代顺序流水线

**关键认知**：框架只是"协调结构"的语法糖。四种框架解决的是同一个问题——怎么让多个 LLM 调用协调起来。区别在于协调方式：转交（Swarm）、讨论（AutoGen）、流水线（CrewAI）、状态机（LangGraph）。

## 六、我还困惑的地方

1. **CrewAI 的 task.output.raw 访问模式太脆弱了**：`crew.kickoff()` 之后通过 `task_classify.output.raw` 取结果，但这个字段是否总是可用？文档不清晰，调试时经常不确定是 Crew 没跑完还是字段没填充。

2. **CrewAI 的重试需要重建整个 Crew**：FR-5a 里审核退回后重新创建了 Crew 对象（包含 classify + search + draft + review），实际上只需要重跑 draft + review。框架没有提供"只重跑部分 Task"的 API，感觉设计上没考虑局部重试的场景。

3. **什么时候用 CrewAI 的 context 依赖链，什么时候用 LangGraph 的显式 State 传递？**两个框架都能做顺序流水线，但在需要条件分支时 LangGraph 明显更好。问题是：有没有一个复杂度分界线？还是说只要预期未来会变复杂，就一律用 LangGraph？

4. **CrewAI 创建了 5 个 Agent 但 billing/general specialist 没用到**：本项目中 search 和 draft 的 agent 写死成了 tech_support，billing_support 和 general_support 形同虚设。如何让 CrewAI 在运行时根据分类结果动态选择 agent？目前看需要更复杂的 Task 路由逻辑，框架对此支持有限。
