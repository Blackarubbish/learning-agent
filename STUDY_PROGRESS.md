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
| 11 | 周度总结 | 📌 待学习 | - |

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
| 我能解释 RRF 融合原理并实现 | 3 | 能写出代码但不确定 k=60 为什么 |
| 我能解释 Rerank 的作用和原理 | 3 | 理解粗排→精排的管线 |
| 我能从零搭建混合检索+Rerank管线 | 4 | 独立完成了 hybrid_rerank_retriever.py |

### 评估体系

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能解释 Faithfulness 的含义 | 2 | 读了笔记，没动手跑过 |
| 我能用 Ragas 评估 RAG 系统 | 1 | 还没开始 |
| 我能设计评估数据集（ground truth） | 1 | 还没开始 |

### 向量数据库

| 能力维度 | 自评 | 证据 |
|---------|------|------|
| 我能解释 FAISS 和 Milvus 的区别 | 4 | 独立完成 CRUD，理解了增量写入/属性过滤/持久化的优势 |
| 我能用 Milvus 做 CRUD | 4 | 独立完成 starter.py 全流程 |

---

## 薄弱点追踪

| 标记日期 | 概念 | 问题描述 | 复习计划 |
|---------|------|---------|---------|
| - | - | 暂无 | - |

---

## 学习路径

```
Week 1: FastAPI + LangChain + Naive RAG              ✅ 已完成
Week 2: Advanced RAG + Milvus                        🔄 进行中 (06-07 ✅, 08-11 📌)
Week 3: Agent Development & Tool Calling
Week 4: Performance Optimization (Redis, Async, vLLM)
Week 5: Monitoring & Deployment (Docker, Prometheus)
Week 6: Multi-Agent Systems (AutoGen, CrewAI)
```

## 当前进度

- **已完成章节**: 09 - Milvus 向量数据库
- **当前学习**: 11 - 周度总结
- **下次学习**: 11 - 周度总结

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
    │   ├── 01-fastapi/
    │   ├── 02-langchain/
    │   ├── 03-rag-part1/
    │   ├── 04-rag-part2/
    │   └── 05-naive-rag/
    └── stage2-advanced-rag/
        ├── 06-query-transformation/
        ├── 07-hybrid-retriever-rerank/
        ├── 08-rag-evaluation/
        ├── 09-milvus/
        ├── 10-advanced-data-processing/
        └── 11-weekly-summary/
```

---

## 学习规则

1. **开始学习前**：读取本文件了解进度 + 能力短板
2. **学习过程中**：按照 AGENT.md 的引导流程进行
3. **完成章节后**：更新状态 ✅ + 更新能力自评表
4. **每周五**：回顾 + 更新 CONCEPT_MAP.md