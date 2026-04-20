# 混合检索与 Rerank (Day 9)

## 概述

混合检索 = 稀疏检索(BM25) + 密集检索(Embedding)

纯向量检索对关键词不敏感，纯 BM25 检索无法理解语义。混合检索结合两者优势，Rerank 对结果进行二次排序。

## 1. BM25 算法

### 核心原理

BM25 (Best Matching 25) 是基于词频的概率检索算法，是 Elasticsearch/Lucene 默认的相关性评分算法。

**公式**：
```
Score(D, Q) = Σ IDF(qi) × (f(qi,D) × (k1+1)) / (f(qi,D) + k1 × (1-b+b×|D|/avgdl))
```

**参数说明**：
- `f(qi,D)`：词 qi 在文档 D 中的词频
- `|D|`：文档长度
- `avgdl`：平均文档长度
- `k1`：词频饱和参数（通常 1.2）
- `b`：长度归一化参数（通常 0.75）
- `IDF(qi)`：逆文档频率，衡量词的区分能力

### Python 实现

```python
from rank_bm25 import BM25Okapi
import jieba

# 示例文档
documents = [
    "猫是一种可爱的动物，喜欢抓老鼠。",
    "狗是人类的好朋友，喜欢追猫。",
    "老鼠是一种小型啮齿动物，猫喜欢抓它们。"
]

# 中文分词
tokenized_docs = [list(jieba.cut(doc)) for doc in documents]

# 初始化 BM25
bm25 = BM25Okapi(tokenized_docs)

# 查询
query = "猫喜欢抓什么动物？"
tokenized_query = list(jieba.cut(query))
scores = bm25.get_scores(tokenized_query)

# 获取排名
doc_scores = list(zip(documents, scores))
doc_scores.sort(key=lambda x: x[1], reverse=True)
print(doc_scores)
```

### 安装依赖

```bash
pip install rank-bm25 jieba
```

---

## 2. 混合检索实现

### 方案一：手动实现混合检索

```python
from rank_bm25 import BM25Okapi
import jieba
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

class HybridRetriever:
    def __init__(self, texts, embedding_model):
        self.texts = texts
        self.embedding_model = embedding_model

        # BM25 索引
        self.tokenized_texts = [list(jieba.cut(text)) for text in texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

        # FAISS 索引
        self.vectors = embedding_model.embed_documents(texts)
        self.dimension = len(self.vectors[0])
        import faiss
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(self.vectors)

    def retrieve(self, query, k=5, alpha=0.5):
        # BM25 检索
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_ranking = sorted(range(len(bm25_scores)),
                             key=lambda i: bm25_scores[i],
                             reverse=True)[:k*2]

        # 向量检索
        query_vector = self.embedding_model.embed_query(query)
        _, vector_indices = self.index.search([query_vector], k*2)
        vector_ranking = vector_indices[0].tolist()

        # RRF 融合
        rrf_scores = {}
        for rank, doc_idx in enumerate(bm25_ranking):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + 1 / (60 + rank + 1)
        for rank, doc_idx in enumerate(vector_ranking):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + 1 / (60 + rank + 1)

        # 排序返回
        final_ranking = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return [self.texts[idx] for idx, _ in final_ranking]

# 使用
retriever = HybridRetriever(texts, OpenAIEmbeddings())
results = retriever.retrieve("机器学习是什么", k=5)
```

### 方案二：使用 LlamaIndex 实现混合检索

```python
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core import VectorStoreIndex

# BM25 Retriever
bm25_retriever = BM25Retriever.from_defaults(
    texts=texts,
    similarity_top_k=5
)

# Vector Retriever
vector_retriever = VectorStoreIndex.from_documents(documents).as_retriever(
    similarity_top_k=5
)

# 混合检索（使用 RRF）
hybrid_retriever = QueryFusionRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    mode="rrf",  # reciprocal rank fusion
    similarity_top_k=5
)

results = hybrid_retriever.retrieve("什么是深度学习")
```

---

## 3. Rerank 模型

Rerank 在初步检索后，用专门的 Rerank 模型对结果进行精细化排序。

### 使用 Cohere Rerank

```bash
pip install cohere
```

```python
import cohere

cohere_client = cohere.Client("your-api-key")

# 初步检索结果
initial_results = vectorstore.similarity_search(query, k=20)

# Rerank
reranked = cohere_client.rerank(
    query=query,
    documents=[doc.page_content for doc in initial_results],
    top_n=5,
    model="rerank-multilingual-v3.0"
)

# 获取最终结果
final_results = [initial_results[result.index] for result in reranked.results]
```

### 使用 LangChain Cohere Rerank 集成

```python
from langchain_community.document_compressors import CohereRerank
from langchain.retrievers import ContextualCompressionRetriever

# 基础检索器
base_retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

# Rerank 压缩器
compressor = CohereRerank(cohere_api_key="your-api-key", top_n=5)

# 带 Rerank 的压缩检索器
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=base_retriever
)

# 最终检索
results = compression_retriever.get_relevant_documents(query)
```

---

## 4. RRF (Reciprocal Rank Fusion) 融合算法

RRF 是融合多个检索结果的标准方法：

```python
def reciprocal_rank_fusion(results_list, k=60):
    """
    results_list: [[doc1, doc2, ...], [doc_a, doc_b, ...]]
    k: 融合参数，通常 60
    """
    doc_scores = {}

    for results in results_list:
        for rank, doc in enumerate(results):
            # 使用文档前100字符作为唯一标识
            doc_id = hash(doc.page_content[:100])
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1 / (k + rank + 1)

    # 按分数排序
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_docs
```

**原理**：排名靠前的文档获得更高权重，RRF 能平衡不同检索系统的结果。

---

## 5. 完整混合检索 + Rerank 流程

```python
from rank_bm25 import BM25Okapi
import jieba
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

class AdvancedRAGRetriever:
    def __init__(self, texts, api_key):
        self.texts = texts
        self.embeddings = OpenAIEmbeddings(api_key=api_key)

        # 构建 BM25 索引
        self.tokenized_texts = [list(jieba.cut(t)) for t in texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

        # 构建向量索引
        self.vectors = self.embeddings.embed_documents(texts)
        import faiss
        self.d = len(self.vectors[0])
        self.index = faiss.IndexFlatL2(self.d)
        self.index.add(self.vectors)

    def _rrf_fusion(self, bm25_results, vector_results, k=60):
        doc_scores = {}
        for rank, doc_idx in enumerate(bm25_results):
            doc_scores[doc_idx] = doc_scores.get(doc_idx, 0) + 1 / (k + rank + 1)
        for rank, doc_idx in enumerate(vector_results):
            doc_scores[doc_idx] = doc_scores.get(doc_idx, 0) + 1 / (k + rank + 1)
        return sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

    def retrieve(self, query, k=5, use_rerank=False, cohere_api_key=None):
        # 1. BM25 检索
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_top = sorted(range(len(bm25_scores)),
                         key=lambda i: bm25_scores[i],
                         reverse=True)[:k*2]

        # 2. 向量检索
        q_vec = self.embeddings.embed_query(query)
        _, vector_indices = self.index.search([q_vec], k*2)
        vector_top = vector_indices[0].tolist()

        # 3. RRF 融合
        fused = self._rrf_fusion(bm25_top, vector_top, k=60)
        fused_indices = [idx for idx, _ in fused[:k*2]]

        # 4. Rerank（可选）
        if use_rerank and cohere_api_key:
            import cohere
            client = cohere.Client(cohere_api_key)
            docs_to_rerank = [self.texts[i] for i in fused_indices]

            reranked = client.rerank(
                query=query,
                documents=docs_to_rerank,
                top_n=k,
                model="rerank-multilingual-v3.0"
            )
            return [docs_to_rerank[r.index] for r in reranked.results]

        return [self.texts[i] for i in fused_indices[:k]]

# 使用
retriever = AdvancedRAGRetriever(texts, api_key)
results = retriever.retrieve("深度学习原理", k=5, use_rerank=True, cohere_api_key="xxx")
```

---

## 方法对比

| 组件 | 作用 | 优缺点 |
|------|------|--------|
| **BM25** | 关键词匹配 | 优点：精确、速度快；缺点：无法理解语义 |
| **向量检索** | 语义匹配 | 优点：理解语义；缺点：对关键词不敏感 |
| **RRF** | 结果融合 | 平衡两种检索方式的优点 |
| **Rerank** | 精细排序 | 优点：精度高；缺点：增加延迟 |

---

## 实践任务

1. 实现 BM25 检索器
2. 实现混合检索（BM25 + 向量 + RRF）
3. 集成 Cohere Rerank 模型
4. 对比不同配置的召回效果

---

## 参考资源

- [BM25算法原理与Python实现](https://zhuanlan.zhihu.com/p/670322092)
- [混合检索+Rerank实战(CSDN)](https://blog.csdn.net/2401_88044367/article/details/159892152)
- [Cohere Rerank 官方文档](https://docs.llamaindex.ai/en/stable/examples/node_postprocessor/CohereRerank.html)
- [Modular RAG 论文](https://arxiv.org/pdf/2407.21059)