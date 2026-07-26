# 26 - Swarm: Multi-Agent 基础原理

## 目标

用 OpenAI 的 Swarm 框架（最简 Multi-Agent 框架，核心代码仅 ~500 行），理解 Multi-Agent 的三个核心概念：
- **Agent** = 角色（instructions + tools）
- **Handoff** = 转交（一个 Agent 把对话转给另一个）
- **Routine** = 预设流程（预定义的 Agent 切换路径，无需 LLM 判断）

## 核心概念

### 为什么从 Swarm 开始？

AgentGuide 的学习建议：
```
Step 1: Swarm (理解原理，1天) → Step 2: LangChain → Step 3: AutoGen/LangGraph → Step 4: CrewAI
```

Swarm 是 OpenAI 官方出的**教育性框架**，代码极少但概念完整。学完 Swarm 后，AutoGen/CrewAI/LangGraph 的核心概念（Agent 路由、Handoff、上下文传递）你已经全懂了——它们只是在此基础上的增强。

### Swarm 的三个核心理念

**1. Agent —— 一个角色**
```python
agent = Agent(
    name="客服",
    instructions="你是客服，帮助用户解决问题。如果解决不了，转给技术支持。",
    tools=[search_knowledge_base],
)
```

**2. Handoff —— 对话转移**
```python
def transfer_to_tech_support():
    """把对话转给技术支持 Agent"""
    return tech_support_agent  # 返回目标 Agent 对象


agent = Agent(
    name="客服",
    tools=[search_knowledge_base, transfer_to_tech_support],  # handoff 也是 tool
)
```
关键是：Handoff 就是一个普通 tool，返回值是目标 Agent。Swarm 框架看到 tool 返回 Agent 对象时，自动切换。

**3. Routine —— 预设流程（AgentGuide 强调）**
```python
# 不需要 LLM 动态判断"该转给谁"的场景：
# 直接用 function 串联，减少 LLM 调用次数 + token 消耗
def customer_service_flow(user_input):
    response = triage_agent.run(user_input)
    if response.handoff_to == "tech":
        return tech_agent.run(response.context)
    elif response.handoff_to == "billing":
        return billing_agent.run(response.context)
    return response
```

### Swarm vs 其他框架的核心差异

| 特性 | Swarm | AutoGen | CrewAI | LangGraph |
|------|-------|---------|--------|-----------|
| 代码量 | ~500 行 | ~20K 行 | ~30K 行 | ~15K 行 |
| Handoff 机制 | 函数返回值 | 消息发布/订阅 | Task 委托 | 状态机边 |
| LLM 调用次数 | 最少（Routine 模式） | 每次发言都调 LLM | 每个 Task 调 LLM | 每个节点调 LLM |
| 学习目标 | 理解原理 | 对话式协作 | 角色式协作 | 生产级编排 |
| 生产推荐 | ❌ 教育用途 | ⚠️ 原型 | ⚠️ 原型 | ✅ 生产环境 |

---

## 实验设计

由于 Swarm 底层依赖 OpenAI API，我们用纯 Python 手动实现一个极简 Swarm（~100 行），直接复用你现有的 DeepSeek/Zhipu LLM。

### 实验目标
1. 实现 Agent（instructions + tools + handoff functions）
2. 实现 Swarm.run() 循环（LLM 调用 → tool 执行 → 检测 Handoff → 切换 Agent）
3. 构建"客服 → 技术支持"二级 Handoff 系统
4. 验证：客服收到技术问题时自动转给技术支持

## 前置条件

```bash
# 无额外依赖，复用现有的 common 模块
pip install -e .  # 如果还没装过
```

## 参考来源

- [OpenAI Swarm](https://github.com/openai/swarm) — 官方仓库
- [AgentGuide: Agent 框架对比](./resources/agent/frameworks.md)
- [AgentGuide: 开发岗学习路线 - 第 6 周](./docs/05-roadmaps/learning-roadmap-development.md)
