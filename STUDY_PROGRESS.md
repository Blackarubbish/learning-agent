# 学习状态 v2

## 项目概述

AI Agent 开发工程师学习项目，基于 AgentGuide 开源路线。**AI Agent 全程引导学习**。

## 学习进度

### 第一阶段：RAG 基础

| 序号 | 主题 | 状态 | 完成日期 |
|------|------|------|---------|
| 01 | FastAPI 快速入门 | ✅ | - |
| 02 | LangChain 核心概念 | ✅ | - |
| 03 | RAG Part 1 - 文档加载与分割 | ✅ | - |
| 04 | RAG Part 2 - 向量化与存储 | ✅ | - |
| 05 | Naive RAG 实战 | ✅ | - |

### 第二阶段：高级 RAG

| 序号 | 主题 | 状态 | 完成日期 |
|------|------|------|---------|
| 06 | Query Transformation | ✅ | - |
| 07 | 混合检索与 Rerank | ✅ | - |
| 08 | RAG 评估体系 | ✅ | 2026-04-25 |
| 09 | Milvus 向量数据库 | ✅ | 2026-04-25 |
| 10 | 高级数据处理 | ✅ | 2026-04-25 |
| 11 | 周度总结 | ✅ | 2026-05-09 |

### 第三阶段：Agent 开发与 Tool Calling

| 序号 | 主题 | 状态 | 完成日期 |
|------|------|------|---------|
| 12 | Agent 核心概念 (ReAct) | ✅ | 2026-05-12 |
| 13 | 自定义工具开发 | ✅ | 2026-05-13 |
| 14 | SQL & 数据库工具 | ✅ | 2026-05-13 |
| 15 | Function Calling 实战 | ✅ | 2026-05-15 |
| 16 | Agent Memory | ✅ | 2026-05-16 |
| 17 | Agent 错误处理 | ✅ | 2026-05-16 |
| 18 | 周度总结与 Agent 项目 | ✅ | 2026-05-19 |

### 第四阶段：系统性能优化 ✅ 已完成

| 序号 | 主题 | 状态 | 完成日期 |
|------|------|------|---------|
| 19 | 性能瓶颈分析 | ✅ | 2026-05-24 |
| 20 | 缓存优化 (Redis) | ✅ | 2026-05-24 |
| 21 | 异步处理 (Async) | ✅ | 2026-06-03 |
| 22 | 批处理优化 | ✅ | 2026-06-06 |
| 23 | 高性能推理 (vLLM) | ✅ 概念掌握 | 2026-06-08 |
| 24 | 周度总结与性能压测 | ✅ 跳过（已有 Node.js 压测经验） | 2026-06-08 |

### 第五阶段：监控与部署

| 序号 | 主题 | 状态 | 完成日期 |
|------|------|------|---------|
| 25 | Docker + Prometheus + Grafana | ✅ 自学完成 | 2026-06-08 |

### 第六阶段：多 Agent 系统

| 序号 | 主题 | 状态 | 完成日期 |
|------|------|------|---------|
| 26 | Swarm — Multi-Agent 基础原理 | ✅ 完成 | 2026-06-10 |
| 27 | AutoGen — 多 Agent 对话协作 | 📌 待学习 | - |
| 28 | CrewAI — 角色驱动的任务协作 | 📌 待学习 | - |
| 29 | LangGraph — 生产级 Agent 工作流 | 📌 待学习 | - |
| 30 | 实战项目 + 框架对比 | 📌 待学习 | - |

---

## 能力自评

> 每完成一个阶段（或感到能力变化时）更新此表。分数含义：
> - 1：只知道概念名字
> - 2：能复述原理
> - 3：能独立写 demo
> - 4：能调优参数，理解取舍
> - 5：能教别人，能根据场景选型

### 检索与向量化

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能从零搭建文档加载→分块→向量化 pipeline | 4 | 独立完成了 03-05 所有代码 |
| 我能解释不同 Embedding 模型的优缺点 | 2 | 只用过 Zhipu embedding-3 |
| 我能选择合适的 chunk_size 和 overlap | 3 | 理解原理但未系统对比 |
| 我能解释向量检索和关键词检索的区别 | 4 | 完成了 BM25+向量检索对比 |

### 高级检索

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能实现 BM25 检索器 | 4 | 独立实现了 BM25 封装 |
| 我能解释 RRF 融合原理并实现 | 4 | 独立完成 RRF 融合，理解 k=60 的作用 |
| 我能解释 Rerank 的作用和原理 | 4 | 理解粗排→精排的管线，完成智谱 Rerank 接入 |
| 我能从零搭建混合检索+Rerank管线 | 5 | 独立完成 AdvancedRAG 全管线，能对比解释各环节贡献 |
| 我能整合 Query Transformation + 混合检索 + Rerank 到统一系统 | 4 | 独立完成了 11 章综合实战 |

### 评估体系

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能解释 Faithfulness 的含义 | 4 | 通过对比实验理解了 Faithfulness 是检测幻觉最直接的指标 |
| 我能用 Ragas 评估 RAG 系统 | 1 | 还没开始 |
| 我能设计评估数据集（ground truth） | 1 | 还没开始 |
| 我能区分 Faithfulness / Answer Relevancy / Answer Correctness 的适用场景 | 3 | 在综合讨论中理解了三个指标的检测目标差异 |

### 向量数据库

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能解释 FAISS 和 Milvus 的区别 | 4 | 独立完成 CRUD，理解了增量写入/属性过滤/持久化的优势 |
| 我能用 Milvus 做 CRUD | 4 | 独立完成 starter.py 全流程 |

### Agent 开发

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能解释 Agent 和传统 RAG 的本质区别 | 4 | 理解 Agent 是循环而非管道，能举例说明何时不用 Agent |
| 我能从零实现 ReAct 循环 | 4 | 独立完成 starter.py 的 SimpleAgent，含工具定义、输出解析、执行循环 |
| 我能解释 Reflection（反思）的雏形原理 | 3 | 实现了 parse_error 反馈机制，理解错误累积问题 |
| 我能判断什么场景该用 Agent | 3 | 理解 Anthropic "简单优先"原则，能区分确定性任务和开放式任务 |
| 我能设计信息抽象的工具输出（截断+摘要+引导） | 4 | 独立完成 smart_search，理解渐进式曝光模式 |
| 我能设计带状态反馈的批量处理工具 | 4 | 独立完成 batch_process，含进度统计和失败处理建议 |
| 我能设计带错误恢复接口的 API 工具 | 4 | 独立完成 api_fetch，每个错误分支提供可用选项和正确示例 |
| 我能解释工具工程为什么决定 Agent 上限 | 4 | 理解 70% 工作在工具端，同样的 LLM + 不同工具 = 不同 Agent |
| 我能从零构建安全的 SQL Agent 工具 | 4 | 独立完成 db_schema + db_query，含安全校验和信息抽象 |
| 我能解释 Schema 探索和 SQL 安全拦截的必要性 | 4 | 理解"先看目录再翻书"模式，识别 Agent 幻觉导致数据灾难的风险 |
| 我能将 ReAct 工具定义转换为 FC JSON Schema 格式 | 4 | 独立完成 TODO 1，含 enum 约束 |
| 我能从零实现 bind_tools + ToolMessage 的 FC Agent 循环 | 4 | 独立完成 TODO 2，13/13 断言通过 |
| 我能解释 tool_choice 四种模式的行为差异和适用场景 | 4 | 独立完成 TODO 3，理解 auto/required/none/指定工具的 API 级别控制 |
| 我能对比 FC 和 ReAct 的优劣并做技术选型 | 4 | 理解 FC 的解析可靠性+并行调用优势，也知道 ReAct 在需要暴露推理链时的价值 |
| 我能从零实现双层记忆 Agent（短期缓冲+长期向量存储） | 4 | 独立完成 ShortTermMemory + LongTermMemory + MemoryAgent |
| 我能解释短期记忆和长期记忆在存储介质、检索方式、数据形态上的区别 | 4 | 能清晰对比内存全文 vs 向量语义检索 |
| 我能解释定期批量提取（而非每轮提取）的设计取舍 | 4 | 理解 token 成本、性能、信息冗余的权衡 |
| 我能从零实现带错误分类的 ResilientAgent | 4 | 独立完成了三分类+反射循环+降级策略 |
| 我能解释为什么错误分三类而非二类 | 4 | 理解 PARAMETER_ERROR 让 LLM 从"盲目重试"变成"检查参数再试" |
| 我能解释错误累积对长任务成功率的影响 | 5 | 理解 95%→36% 的指数衰减，能讲清楚反射如何阻断这个衰减 |
| 我能设计结构化错误反馈（分类+摘要+修复建议） | 4 | 独立实现了 classify_error + _format_error_feedback |
| 我能解释降级阈值和重试次数的区别 | 4 | 理解连续失败触发降级（防死循环），总重试控制 token 成本 |
| 我能从零集成 FC 循环+工具工程+双层记忆+错误反射到一个 Agent | 4 | 独立完成 ResearchAssistant，9/9 断言通过 |
| 我能解释记忆在 Agent 中的价值（不只是上下文管理） | 4 | 理解短期缓冲 vs 长期偏好存储，场景 3 验证了跨轮回忆 |
| 我能解释 Agent 集成中各模块的职责边界 | 4 | FC 循环=决策框架，工具工程=可靠性，记忆=体验，反射=安全网 |

### 性能分析

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能用 cProfile + pstats 定位 Agent 系统的性能瓶颈 | 4 | 独立完成 profile_run + compare_sorts + run_experiments |
| 我能解释 cumtime 和 tottime 的区别及各自用途 | 4 | cumtime 找时间黑洞（网络 I/O），tottime 找代码热点（CPU 密集） |
| 我能用 print_callers 追踪慢函数的调用链 | 3 | 理解了调用链分析，TODO 4 未独立完成 |
| 我能从零实现 Cache-Aside 模式（查缓存→miss→调LLM→写缓存） | 4 | 独立完成 cached_llm_invoke，两轮 benchmark 验证 |
| 我能解释精确缓存和语义缓存的区别及适用场景 | 4 | 精确缓存用 SHA256 做 key，语义缓存用 embedding 相似度匹配 |
| 我能用 fakeredis 做本地缓存开发测试 | 4 | 独立完成 ExactMatchCache + SemanticCache 集成 |
| 我能将同步 Agent 改造为异步（llm.ainvoke + asimilarity_search） | 4 | 独立完成 AsyncAgent，10/10 断言通过 |
| 我能解释 asyncio 事件循环如何让 I/O 等待时间重叠 | 4 | 用自己的话解释了 40s→14s 的加速原理，餐厅服务员类比 |
| 我能用 asyncio.gather 并发执行多个 Agent 查询 | 4 | 独立完成了 benchmark，5 并发加速比 2.8x |
| 我能解释异步不加速单任务的原理 | 5 | 能讲清楚 await 是"挂起让路"而非"阻塞等待"，单协程无切换则无加速 |

### 批处理优化

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能解释 Embedding 批处理和 LLM batch 的本质区别 | 4 | 独立完成 benchmark，理解 API 级合并 vs 框架级并发 |
| 我能从零实现批量 Embedding 并计算加速比 | 4 | 独立完成 measure_embedding + run_embedding_benchmark |
| 我能解释 batch_size 收益递减的原因 | 4 | 独立完成 find_best_batch_size，观察到 1→5 收益远大于 10→30 |
| 我能用 llm.batch() 替代串行 for 循环 | 4 | 独立完成 benchmark_llm_batch，加速比 4.5x |

### 多 Agent 系统

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能从零实现 Swarm 风格 Handoff 机制 | 4 | 独立完成 Agent 类 + Swarm.run() 循环，19/19 断言通过 |
| 我能解释 Handoff 为什么是普通 tool 而非框架特殊机制 | 4 | 理解 isinstance(result, Agent) 检测替代特殊 API |
| 我能解释 Handoff 后上下文如何传递 | 4 | 理解 history list 共享不重置，切换只在 current_agent 变量 |
| 我能区分终端 Agent 和中间 Agent 的设计差异 | 4 | 终端 Agent 不设 handoff 防止无限转交 |
| 我能解释 Routine 模式对减少 LLM 调用的价值 | 3 | 理解预设流程 vs LLM 自主路由的 token 成本差异

---

## 薄弱点追踪

| 标记日期 | 概念 | 问题描述 | 复习计划 |
|---------|------|---------|---------|
| - | - | 暂无 | - |

---

## 学习路径

```
Week 1: FastAPI + LangChain + Naive RAG              ✅ 已完成
Week 2: Advanced RAG + Milvus                        ✅ 已完成 (06-11)
Week 3: Agent Development & Tool Calling          ✅ 已完成 (12-18)
Week 4: Performance Optimization (Redis, Async, vLLM) ✅ 已完成 (19/24)
Week 5: Monitoring & Deployment (Docker, Prometheus)       ✅ 已完成
Week 6: Multi-Agent Systems (AutoGen, CrewAI)               🔄 进行中
```

## 当前进度

- **已完成章节**: 25 — Stage 5 自学完成
- **当前学习**: Stage 6 — 多 Agent 系统（AutoGen, CrewAI）
- **下次学习**: 27 — AutoGen 多 Agent 对话协作

---

## 项目文件结构

```
agent-study/
├── CLAUDE.md             # Agent 行为规则（所有 AI 助手的指令集，唯一源头）
├── STUDY_PROGRESS.md     # 本文件 — 学习进度 + 能力自评
├── CONCEPT_MAP.md        # 概念地图（Mermaid 可视化）
├── README.md             # 项目说明
├── common/               # 共享基础设施（消除 boilerplate）
│   ├── __init__.py
│   ├── env.py            # 环境变量加载
│   ├── embeddings.py     # ZhipuEmbeddings 封装
│   ├── llm.py            # LLM 工厂（DeepSeek/Zhipu）
│   └── check.py          # 自检工具（section/check/summary）
├── main.py
├── pyproject.toml
└── learning/
    ├── stage1-rag-basics/
    │   ├── mindmap.md        # Stage 1 思维导图
    │   ├── 01-fastapi/
    │   ├── 02-langchain/
    │   ├── 03-rag-part1/
    │   ├── 04-rag-part2/
    │   └── 05-naive-rag/
    └── stage2-advanced-rag/
        ├── mindmap.md        # Stage 2 思维导图
        ├── 06-query-transformation/
        ├── 07-hybrid-retriever-rerank/
        ├── 08-rag-evaluation/
        ├── 09-milvus/
        ├── 10-advanced-data-processing/
        └── 11-weekly-summary/
    └── stage3-agent-development/
        ├── mindmap.md        # Stage 3 思维导图
        ├── 12-agent-basics/
        ├── 13-custom-tools/
        ├── 14-sql-agent/
        ├── 15-function-calling/
        ├── 16-agent-memory/
        ├── 17-error-handling/
        └── 18-weekly-summary/
    └── stage4-performance/
        ├── mindmap.md        # Stage 4 思维导图
        ├── 19-profiling/
        ├── 20-redis-cache/
        ├── 21-async/
        ├── 22-batch/
        ├── 23-vllm/
        └── 24-weekly-summary/
    └── stage5-monitoring-deployment/
        ├── README.md         # Stage 5 学习资料（自学）
        └── mindmap.md        # Stage 5 思维导图
    └── stage6-multi-agent/
        ├── README.md         # Stage 6 总览
        ├── mindmap.md        # Stage 6 思维导图
        ├── 26-swarm/         # Swarm 极简入门
        ├── 27-autogen/       # AutoGen 对话协作
        ├── 28-crewai/        # CrewAI 角色驱动
        ├── 29-langgraph/     # LangGraph 生产级工作流
        └── 30-weekly-project/ # 实战项目 + 框架对比
```

---

## 学习规则

1. **开始学习前**：读取本文件了解进度 + 能力短板
2. **学习过程中**：按照 AGENT.md 的引导流程进行
3. **完成章节后**：更新状态 ✅ + 更新能力自评表
4. **每周五**：回顾 + 更新 CONCEPT_MAP.md