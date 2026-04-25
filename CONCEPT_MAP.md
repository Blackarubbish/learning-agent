# 概念地图

> 每次完成一个章节后，在这里连接新概念与已有知识。连线含义由你口述，AI Agent 帮你生成 Mermaid 代码。

```mermaid
graph TD
    %% ====== 基础层 ======
    subgraph 基础架构
        FastAPI[FastAPI Web框架] -->|提供 API 接口| RAG[RAG 检索增强生成]
        LangChain[LangChain 应用框架] -->|编排组件| RAG
    end

    %% ====== 文档处理层 ======
    subgraph 文档处理
        DocLoader[文档加载器<br/>TextLoader/PDF] --> TextSplitter[文本分割<br/>RecursiveCharacterTextSplitter]
        TextSplitter --> Chunks[文档块]
    end

    %% ====== Embedding 层 ======
    subgraph 向量化
        Chunks --> EmbeddingModel[Embedding 模型<br/>Zhipu embedding-3]
        EmbeddingModel --> Vectors[向量表示]
    end

    %% ====== 检索层 ======
    subgraph 检索策略
        Vectors --> VectorSearch[向量检索<br/>语义相似度]
        Chunks --> BM25[BM25 关键词检索<br/>词频统计]
        VectorSearch --> RRF[RRF 融合<br/>倒数排名融合]
        BM25 --> RRF
        RRF --> Rerank[Rerank 精排<br/>Zhipu rerank]
        QueryTransform[查询变换<br/>MultiQuery/HyDE] --> VectorSearch
        QueryTransform --> BM25
    end

    %% ====== 向量数据库层 ======
    subgraph 向量存储
        Vectors --> FAISS[FAISS<br/>内存向量库]
        Vectors --> Milvus[Milvus<br/>分布式向量库]
    end

    %% ====== 生成层 ======
    subgraph 生成
        Rerank --> LLM[LLM 生成<br/>DeepSeek/Zhipu]
        LLM --> Answer[答案]
    end

    %% ====== 评估层 ======
    subgraph 评估体系
        Answer --> Faithfulness[Faithfulness<br/>忠实度评估]
        Rerank --> ContextPrecision[Context Precision<br/>上下文精确度]
        RRF --> ContextRecall[Context Recall<br/>上下文召回率]
        Answer --> AnswerRelevancy[Answer Relevancy<br/>答案相关性]
        Faithfulness --> Ragas[Ragas 评估框架]
        ContextPrecision --> Ragas
        ContextRecall --> Ragas
        AnswerRelevancy --> Ragas
        Ragas --> DeepEval[DeepEval 替代方案]
    end

    %% ====== 样式 ======
    style RAG fill:#f9f,stroke:#333,stroke-width:4px
    style RRF fill:#bbf,stroke:#333,stroke-width:2px
    style Rerank fill:#bfb,stroke:#333,stroke-width:2px
    style Ragas fill:#fbb,stroke:#333,stroke-width:2px
```

---

## 概念关联记录

每完成一个章节后在此处手动记录：

| 章节 | 新概念 | 关联到已有概念 | 关联含义 |
|------|--------|--------------|---------|
| 07 | RRF 融合 | BM25 + 向量检索 | RRF 把两种检索结果按排名取倒数求和，不依赖绝对分数 |
| 07 | Rerank 精排 | RRF 融合 | Rerank 在 RRF 粗筛后用专用模型精排，类比搜索引擎二次排序 |
| 09 | Milvus 向量数据库 | FAISS | Milvus 是 FAISS 的生产级替代：多了增删改查、属性过滤、持久化、分布式 |
| 10 | 文档解析 (Unstructured) | TextLoader + 文本分割 | 解析能按结构分类（标题/正文/表格），避免分块截断和结构信息丢失 |

<!-- 继续往下写... -->

---

## 核心流程一句话总结

```
用户问题 → [查询变换优化] → [多路检索(BM25+向量)] → [RRF融合] → [Rerank精排] → [LLM生成] → [评估验证]
                ↑__________________检索增强__________________↑