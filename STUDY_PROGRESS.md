# 学习状态

## 项目概述

这是一个 AI Agent 开发工程师的学习项目，基于 AgentGuide 开源路线进行学习。

## 学习进度

### 已完成

| 序号 | 主题 | 目录 | 状态 |
|------|------|------|------|
| 01 | FastAPI 快速入门 | `learning/01-fastapi/` | ✅ 完成 |
| 02 | LangChain 核心概念 | `learning/02-langchain/` | ✅ 完成 |
| 03 | RAG Part 1 - 文档加载与分割 | `learning/03-rag-part1/` | ✅ 完成 |
| 04 | RAG Part 2 - 向量化与存储 | `learning/04-rag-part2/` | ✅ 完成 |
| 05 | Naive RAG 实战 | `learning/05-naive-rag/` | 🔄 进行中 |

### 学习路径（开发工程师方向）

```
Week 1: FastAPI + LangChain + Naive RAG
Week 2: Advanced RAG + Milvus
Week 3: Agent Development & Tool Calling
Week 4: Performance Optimization (Redis, Async, vLLM)
Week 5: Monitoring & Deployment (Docker, Prometheus)
Week 6: Multi-Agent Systems (AutoGen, CrewAI)
```

## 当前进度

- **已完成章节**: 05 - Naive RAG 实战
- **下次学习**: Advanced RAG + Milvus

## 学习规则

1. 学习过程中所有询问的问题，需汇总到 `learning/XX-XX-topic/notes/qa.md` 文件中。
2. 每次开始学习前，先阅读本文件了解进度。
3. 完成后更新本文件的"已完成"状态。

## 目录结构

```
agent-study/
├── AGENT.md          # Agent 行为规则
├── STUDY_PROGRESS.md # 学习进度（当前文件）
└── learning/
    ├── 01-fastapi/
    │   ├── README.md
    │   ├── cheatsheet.md
    │   └── notes/
    │       └── qa.md
    └── 02-langchain/
        ├── README.md
        └── notes/
            └── qa.md
```

## 资源链接

- [AgentGuide 学习路线](AgentGuide/docs/05-roadmaps/learning-roadmap-development.md)
- [FastAPI 官方教程](https://fastapi.tiangolo.com/tutorial/)
- [LangChain 官方文档](https://python.langchain.com/)
