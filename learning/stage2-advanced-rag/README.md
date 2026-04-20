# Stage 2: Advanced RAG 与生产级向量数据库

> Week 2 学习内容

## 目录结构

```
stage2-advanced-rag/
├── 06-query-transformation/     # Query Transformation (Day 8)
├── 07-hybrid-retriever-rerank/  # 混合检索与 Rerank (Day 9)
├── 08-rag-evaluation/           # RAG 评估体系 (Day 10-11)
├── 09-milvus/                   # Milvus 向量数据库 (Day 12)
├── 10-advanced-data-processing/# 高级数据处理 (Day 13)
└── 11-weekly-summary/           # 周度总结 (Day 14)
```

## 学习目标

- 掌握 10+ 种 RAG 优化策略
- 建立 RAG 系统的自动化评估流水线
- 熟练使用生产级的分布式向量数据库 Milvus
- 具备处理复杂、非结构化文档的能力

---

## Day 8: Query Transformation

### 核心概念

Query Transformation 是在检索前对用户查询进行改写优化的技术，提升召回质量。

### 主要方法

| 方法 | 原理 | 适用场景 |
|------|------|----------|
| **HyDE** | 让 LLM 生成假设性答案，再用答案检索 | 复杂问题、抽象概念 |
| **Multi-Query** | 用 LLM 生成多个改写版本，并行检索后合并 | 覆盖面广、召回率要求高 |
| **Sub-Query** | 将复杂问题拆分为多个简单子问题 | 多跳推理、复合问题 |

### 学习资源

- [LlamaIndex Query Transforms](https://docs.llamaindex.ai/en/stable/module_guides/querying/query_transforms/root.html)
- [LangChain Query Transformation](https://python.langchain.com/docs/modules/data_connection/retrievers/query_transformers)
- [RAG查询转换之多查询(CSDN)](https://blog.csdn.net/u013565133/article/details/145744707)

### 实践任务

- [ ] 实现 Multi-Query 检索
- [ ] 实现 HyDE 检索
- [ ] 对比不同方法的召回效果

---

## Day 9: 混合检索与 Rerank

### 核心概念

**混合检索** = 稀疏检索(BM25) + 密集检索(Embedding)

**Rerank** = 对初步检索结果进行二次排序，提升相关性

### 技术要点

1. **BM25**：基于词频的传统检索算法，解决纯向量检索对关键词不敏感的问题
2. **RRF (Reciprocal Rank Fusion)**：多检索结果融合算法
3. **Cohere Rerank**：使用专门的 Rerank 模型进行精细化排序

### 学习资源

- [BM25算法原理与Python实现](https://zhuanlan.zhihu.com/p/670322092)
- [混合检索+Rerank实战(CSDN)](https://blog.csdn.net/2401_88044367/article/details/159892152)
- [Cohere Rerank](https://docs.llamaindex.ai/en/stable/examples/node_postprocessor/CohereRerank.html)
- [Modular RAG 论文](https://arxiv.org/pdf/2407.21059)

### 实践任务

- [ ] 实现 BM25 检索
- [ ] 实现混合检索 (BM25 + Embedding)
- [ ] 集成 Cohere Rerank 模型

---

## Day 10-11: RAG 评估体系

### 核心指标

| 指标 | 说明 | 评估维度 |
|------|------|----------|
| **Faithfulness** | 答案是否忠实于检索上下文 | 生成质量 |
| **Answer Relevance** | 答案与问题的相关性 | 生成质量 |
| **Context Precision** | 相关文档的排名位置 | 检索质量 |
| **Context Recall** | 检索到的相关内容比例 | 检索质量 |

### 评估框架

- **RAGAs**：最流行的 RAG 评估框架，支持无参考评估
- **DeepEval**：基于 LLM 的评估工具
- **Lighteval**：HuggingFace 出品的轻量评估工具

### 学习资源

- [RAGAs 官方文档](https://docs.ragas.io/en/stable/)
- [RAGAs 指标解释(CSDN)](https://blog.csdn.net/qq_41913559/article/details/143055531)
- [RAG评价框架RAGAs完整使用指南](https://blog.csdn.net/gitblog_01126/article/details/157111695)

### 实践任务

- [ ] 安装配置 RAGAs
- [ ] 生成评估测试集
- [ ] 评估优化前后的系统性能

---

## Day 12: Milvus 向量数据库

### 核心概念

Milvus 是生产级分布式向量数据库，支持十亿级向量规模。

### 部署方式

| 方式 | 适用场景 | 复杂度 |
|------|----------|--------|
| **Milvus Lite** | 本地开发、笔记本运行 | ⭐ |
| **Milvus Standalone** | 单机部署、小规模生产 | ⭐⭐ |
| **Milvus Cluster** | 分布式生产环境 | ⭐⭐⭐⭐ |

### 学习资源

- [Milvus 官方文档](https://milvus.io/docs/install_standalone-docker.md)
- [Milvus Python SDK](https://github.com/milvus-io/milvus)
- [新手如何使用 Milvus(CSDN)](https://blog.csdn.net/qq_58286779/article/details/146413500)
- [Milvus 向量数据库入门(知乎)](https://zhuanlan.zhihu.com/p/565254258)

### 实践任务

- [ ] Docker 部署 Milvus
- [ ] 使用 Python SDK 进行 CRUD 操作
- [ ] 将 FAISS 索引迁移到 Milvus

---

## Day 13: 高级数据处理

### 核心工具

| 工具 | 擅长处理 | 特点 |
|------|----------|------|
| **Unstructured.io** | PDF, Word, HTML | 通用文档解析 |
| **MinerU** | 复杂 PDF（表格、图片） | 国产开源高精度 |
| **Docling** | 学术论文、技术文档 | 布局感知 |
| **PDF-Extract-Kit** | 中文 PDF | 专用提取工具 |

### 学习资源

- [Unstructured.io GitHub](https://github.com/unstructured-io/unstructured)
- [Unstructured 库实战(CSDN)](https://blog.csdn.net/weixin_29062865/article/details/157824929)
- [MinerU GitHub](https://github.com/opendatalab/MinerU)

### 实践任务

- [ ] 使用 Unstructured 解析 PDF
- [ ] 处理包含表格的复杂文档
- [ ] 集成到 RAG pipeline

---

## Day 14: 周度总结

### 升级任务

将 Week 1 的 Naive RAG 系统升级：

1. 集成 Query Transformation
2. 实现混合检索 + Rerank
3. 接入 Milvus 向量数据库
4. 添加 RAGAs 评估

### 产出要求

- 完整的 Advanced RAG 系统代码
- 性能对比报告（优化前 vs 优化后）
- README 文档说明

---

## 相关资源链接

### 向量数据库对比

参考 `AgentGuide/resources/rag/vector-db.md`

| 向量库 | 推荐场景 |
|--------|----------|
| **Milvus** | 生产环境、大规模数据 |
| **FAISS** | 本地检索、算法实验 |
| **Chroma** | 快速原型、小规模 |
| **Qdrant** | 需要复杂过滤的生产环境 |

### 扩展阅读

- [2025年最全RAG知识库项目汇总](https://github.com/adongwanai/AgentGuide/blob/main/resources/rag/projects.md)
- [向量数据库选型指南](https://github.com/adongwanai/AgentGuide/blob/main/resources/rag/vector-db.md)