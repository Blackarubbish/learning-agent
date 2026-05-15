# 16 - Agent Memory

> 让 Agent 拥有记忆：从"失忆的对话机器人"到"记得你的智能助手"

---

## 在知识体系中的位置

```
上下文工程 (Context Engineering) — Agent 开发的本质
├── System Prompt      # 系统提示词
├── User Prompt        # 用户提示词
├── Short-term Memory  # 短期记忆 ← 本章
├── Long-term Memory   # 长期记忆 ← 本章
├── RAG                # 检索增强
├── Tools              # 工具调用（12-15 章）
└── Structured Output  # 结构化输出
```

Memory 解决的核心问题：**信息如何跨时间传递**。没有 Memory 的 Agent 每次对话都是全新开始；有了 Memory，Agent 能记住用户偏好、历史上下文、任务进度。

---

## 学习资料总结

### 一、核心概念

#### 1.1 为什么 Agent 需要 Memory？

| 能力 | 无 Memory | 有 Memory |
|------|----------|----------|
| 跨轮次对话 | 每轮都是新对话 | 记住前文 |
| 用户个性化 | 无法区分用户 | 记住偏好和历史 |
| 长期任务 | 丢失进度 | 跨会话追踪 |
| 知识积累 | 每次从头学 | 持续学习演进 |

#### 1.2 三层记忆架构（核心框架）

```
Layer 1: 工作记忆 (Working Memory)
  - 当前会话的对话历史
  - 存储：内存（最快）
  - 容量：最近 10-20 轮

Layer 2: 情节记忆 (Episodic Memory)
  - 本次会话中提取的关键信息
  - 存储：向量数据库
  - 容量：单会话级别

Layer 3: 语义记忆 (Semantic Memory)
  - 用户长期偏好、跨会话知识
  - 存储：知识图谱 + 向量库
  - 容量：无限（持久化）
```

#### 1.3 Memory 设计的 5 个核心问题

| 问题 | 策略选项 | 推荐方案 |
|------|---------|---------|
| **什么时候存？** | 全部存 / 只存重要的 / 定期存 | 重要性评分机制 |
| **怎么存？** | 原文 / 摘要 / 结构化实体 | 混合存储（原文+摘要+实体） |
| **怎么检索？** | 向量 / 关键词 / 图谱 | 混合检索 + 时间衰减 |
| **何时遗忘？** | 永远保留 / 时间过期 / 空间满时清理 | 时间衰减 + 重要性阈值 |
| **怎么更新？** | 覆盖 / 合并 / 版本化 | 冲突检测 → 合并或替换 |

---

### 二、主流实现方案

#### 方案 1：LangChain 内置 Memory（学习首选）

LangChain 提供多种开箱即用的 Memory 类型：

| 类型 | 原理 | 适用场景 |
|------|------|---------|
| `ConversationBufferMemory` | 完整保存对话历史 | 短对话 |
| `ConversationBufferWindowMemory` | 滑动窗口保留最近 K 轮 | 控制 token 消耗 |
| `ConversationSummaryMemory` | LLM 摘要压缩历史 | 长对话 |
| `ConversationSummaryBufferMemory` | 摘要 + 最近 K 轮混合 | 平衡精度和成本 |
| `ConversationKGMemory` | 提取实体关系存知识图谱 | 需要推理 |
| `VectorStoreRetrieverMemory` | 向量检索历史记忆 | 长期记忆 |

#### 方案 2：Mem0（10 行代码集成）⭐⭐⭐⭐⭐

- 自动实体提取 + 去重 + 更新
- 支持多种后端（Redis、Qdrant、PostgreSQL）
- GitHub 43k+ stars
- ⚠️ 社区反馈有稳定性问题，生产环境需测试

#### 方案 3：MemGPT（虚拟内存机制）⭐⭐⭐⭐

- 借鉴操作系统虚拟内存管理
- 自动 swap in/out 记忆到外部存储
- 突破上下文窗口限制，支持无限长对话
- GitHub 19k+ stars

#### 方案 4：Zep（企业级）⭐⭐⭐⭐

- 时序知识图谱，记录事件因果关系
- 生产级稳定性，可扩展性强

---

### 三、核心论文（了解即可）

| 论文 | 核心思想 | 适合 |
|------|---------|------|
| **MemGPT** (UC Berkeley, 2023) | LLM 作操作系统，虚拟内存管理 | 开发岗必读 |
| **Mem0** (2024) | 图增强记忆框架，自动实体提取 | 开发岗实战 |
| **Memorizing Transformers** (Google, 2022) | 首次引入外部记忆 + KNN 检索 | 算法岗开山作 |
| **Agent Memory Survey** (2024) | 记忆机制综述，6 大操作分类 | 建立全局认知 |

> 完整论文解读见 `AgentGuide/resources/agent/papers/agent_memory/Agent Memory 核心论文汇总.md`

---

### 四、参考资源

- [AgentGuide - Agent Memory 完整教程](../AgentGuide/docs/02-tech-stack/15-agent-memory.md)
- [AgentGuide - Memory 工具对比](../AgentGuide/resources/agent/memory.md)
- [LangChain Memory 官方文档](https://python.langchain.com/docs/modules/memory/)
- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [MemGPT GitHub](https://github.com/cpacker/MemGPT)

---

## 本章实践目标

实现一个 **MemoryAgent**，具备：

1. **短期记忆**：滑动窗口对话缓冲，记住当前会话的最近 N 轮
2. **长期记忆**：自动提取关键信息存入向量库，跨会话检索
3. **记忆整合**：Agent 响应时同时参考短期 + 长期记忆

与第 15 章 Function Calling 的对比：第 15 章解决的是"Agent 如何调用工具"，本章解决的是"Agent 如何记住上下文"——两者是 Agent 能力的不同维度，最终会组合使用。
