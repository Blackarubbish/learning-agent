# 周度总结 (Day 14)

## Week 2 学习回顾

### Advanced RAG 技术栈

```
┌─────────────────────────────────────────────────────────────────┐
│                      Advanced RAG 系统                           │
├─────────────────────────────────────────────────────────────────┤
│  用户查询 → Query Transformation → 混合检索 → Rerank → 生成     │
│                      ↓                    ↓                     │
│            (HyDE/Multi-Query)      (BM25+Vector+RRF)            │
│                                                               │
│  评估: RAGAs → 指标分析 → 持续优化                              │
└─────────────────────────────────────────────────────────────────┘
```

### 技术要点

| 技术 | 作用 | 关键实现 |
|------|------|----------|
| **Query Transformation** | 提升召回率 | Multi-Query, HyDE, Sub-Query |
| **混合检索** | 平衡关键词和语义 | BM25 + 向量 + RRF |
| **Rerank** | 精细化排序 | Cohere Rerank |
| **RAG 评估** | 量化系统质量 | RAGAs 指标体系 |
| **Milvus** | 生产级向量存储 | 分布式 + 多种索引 |
| **数据处理** | 复杂文档解析 | Unstructured, MinerU |

---

## 系统升级任务

将 Week 1 的 Naive RAG 系统升级为 Advanced RAG。

### 升级清单

- [ ] 集成 Query Transformation（Multi-Query 或 HyDE）
- [ ] 实现混合检索（BM25 + 向量）
- [ ] 添加 Rerank 模块
- [ ] 接入 Milvus 向量数据库
- [ ] 添加 RAGAs 评估
- [ ] 对比优化前后性能

---

## 完整代码框架

```python
from rank_bm25 import BM25Okapi
import jieba
from pymilvus import MilvusClient
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors import CohereRerank

class AdvancedRAG:
    def __init__(self, milvus_uri, cohere_api_key):
        # 向量存储
        self.milvus = MilvusClient(uri=milvus_uri)

        # Embedding
        self.embeddings = OpenAIEmbeddings()

        # BM25
        self.bm25 = None
        self.texts = []

        # Reranker
        self.rerank_compressor = CohereRerank(
            cohere_api_key=cohere_api_key,
            top_n=5
        )

        # LLM
        self.llm = ChatOpenAI(model="gpt-4o-mini")

    def initialize(self, documents):
        """初始化系统"""
        # 1. 文本分割
        from langchain.text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)
        self.texts = [chunk.page_content for chunk in chunks]

        # 2. 构建 BM25 索引
        self.tokenized_texts = [list(jieba.cut(text)) for text in self.texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

        # 3. 存储到 Milvus
        vectors = self.embeddings.embed_documents(self.texts)
        data = [{"id": i, "vector": vectors[i], "text": self.texts[i]}
                for i in range(len(self.texts))]

        self.milvus.insert(collection_name="documents", data=data)

        # 4. 创建向量索引
        self.milvus.create_index(
            collection_name="documents",
            index_params={"metric_type": "IP", "index_type": "HNSW", "params": {"M": 16}}
        )

        print(f"已索引 {len(self.texts)} 个文档")

    def retrieve(self, query, k=10, use_rerank=True):
        """检索"""
        # 1. Query Transformation (Multi-Query)
        from langchain.output_parsers import StrOutputParser
        from langchain.prompts import ChatPromptTemplate

        multi_query_prompt = ChatPromptTemplate.from_template(
            """根据用户问题生成5个不同的改写版本，增加召回率。
            问题: {question}
            改写:"""
        )

        multi_query_chain = multi_query_prompt | self.llm | StrOutputParser()
        queries = multi_query_chain.invoke({"question": query})
        query_list = queries.strip().split("\n")

        # 2. 混合检索 + RRF
        all_scores = {}

        # BM25 检索
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        for rank, idx in enumerate(sorted(range(len(bm25_scores)),
                                          key=lambda i: bm25_scores[i],
                                          reverse=True)[:k]):
            all_scores[idx] = all_scores.get(idx, 0) + 1 / (60 + rank + 1)

        # 向量检索
        query_vector = self.embeddings.embed_query(query)
        results = self.milvus.search(collection_name="documents",
                                      data=[query_vector],
                                      limit=k)

        for rank, result in enumerate(results[0]):
            idx = result["id"]
            all_scores[idx] = all_scores.get(idx, 0) + 1 / (60 + rank + 1)

        # 排序
        sorted_results = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:k]
        retrieved_chunks = [self.texts[idx] for idx, _ in sorted_results]

        # 3. Rerank
        if use_rerank:
            reranked = self.rerank_compressor.compress_documents(
                retrieved_chunks, query
            )
            return reranked

        return retrieved_chunks[:5]

    def ask(self, question):
        """问答"""
        # 检索相关文档
        contexts = self.retrieve(question, k=5)

        # 构建 prompt
        from langchain.prompts import ChatPromptTemplate
        from langchain.prompts import HumanMessagePromptTemplate

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个智能助手，使用以下上下文回答问题。\n\n上下文：\n{context}"),
            ("human", "{question}")
        ])

        chain = prompt | self.llm

        response = chain.invoke({
            "context": "\n\n".join(contexts),
            "question": question
        })

        return {
            "answer": response.content,
            "contexts": contexts
        }
```

---

## 性能对比模板

```python
def compare_performance(baseline_results, optimized_results):
    """对比优化前后性能"""

    metrics = {
        "Faithfulness": [],
        "Answer Relevance": [],
        "Context Precision": [],
        "Context Recall": []
    }

    print("=" * 60)
    print(f"{'Metric':<25} {'Baseline':<12} {'Optimized':<12} {'Improvement':<12}")
    print("=" * 60)

    for metric in metrics:
        baseline_avg = sum(baseline_results[metric]) / len(baseline_results[metric])
        optimized_avg = sum(optimized_results[metric]) / len(optimized_results[metric])
        improvement = (optimized_avg - baseline_avg) / baseline_avg * 100

        print(f"{metric:<25} {baseline_avg:<12.3f} {optimized_avg:<12.3f} {improvement:+.1f}%")

    print("=" * 60)
```

---

## 参考资源

- [Modular RAG 论文](https://arxiv.org/pdf/2407.21059)
- [RAGAs 官方文档](https://docs.ragas.io/en/stable/)
- [Milvus 官方文档](https://milvus.io/docs/install_standalone-docker.md)
- [向量数据库选型指南](https://github.com/adongwanai/AgentGuide/blob/main/resources/rag/vector-db.md)