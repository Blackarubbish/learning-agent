"""
检索效果对比评测

四种配置 × 多场景查询，量化对比：
1. 纯 BM25
2. 纯向量检索
3. 混合检索 (BM25 + 向量 + RRF)
4. 混合检索 + Rerank

评估维度：
- 人工标注的相关文档（ground truth）
- Precision@K：返回的 K 个结果中，有多少是相关的
- Recall@K：所有相关文档中，有多少被返回了
- 结果多样性：返回结果覆盖了多少个不同主题

运行：
  uv run python evaluate_retrievers.py
"""

import os
from pathlib import Path
from typing import List, Dict, Set
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi
import jieba
import httpx
from zai import ZhipuAiClient

zhipu_api_key = os.getenv("ZHIPU_API_KEY")
if not zhipu_api_key:
    raise ValueError("ZHIPU_API_KEY environment variable not set")

zhipu_client = ZhipuAiClient(api_key=zhipu_api_key)


class ZhipuEmbeddings(Embeddings):
    def __init__(self, client):
        self.client = client

    def embed_documents(self, texts):
        response = self.client.embeddings.create(model="embedding-3", input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text):
        response = self.client.embeddings.create(model="embedding-3", input=[text])
        return response.data[0].embedding


embeddings = ZhipuEmbeddings(zhipu_client)

SAMPLE_DOCS = [
    Document(
        page_content="深度学习是机器学习的一个分支，它使用多层神经网络来学习数据的表征。",
        metadata={"id": 0, "topic": "AI基础"},
    ),
    Document(
        page_content="机器学习是人工智能的一个子领域，关注如何让计算机从数据中学习。",
        metadata={"id": 1, "topic": "AI基础"},
    ),
    Document(
        page_content="神经网络是受生物神经系统启发的一种计算模型，是深度学习的基础。",
        metadata={"id": 2, "topic": "AI基础"},
    ),
    Document(
        page_content="GPT是一种基于Transformer的大语言模型，由OpenAI开发。",
        metadata={"id": 3, "topic": "大模型"},
    ),
    Document(
        page_content="GPT-4是OpenAI最新的大型语言模型，具有强大的推理能力。",
        metadata={"id": 4, "topic": "大模型"},
    ),
    Document(
        page_content="ChatGPT是OpenAI开发的对话应用，基于GPT模型构建。",
        metadata={"id": 5, "topic": "大模型"},
    ),
    Document(
        page_content="计算机视觉是AI的一个分支，让计算机能够理解和处理图像。",
        metadata={"id": 6, "topic": "计算机视觉"},
    ),
    Document(
        page_content="卷积神经网络(CNN)是计算机视觉中常用的深度学习模型。",
        metadata={"id": 7, "topic": "计算机视觉"},
    ),
    Document(
        page_content="自然语言处理(NLP)是AI处理和理解人类语言的技术。",
        metadata={"id": 8, "topic": "NLP"},
    ),
    Document(
        page_content="Transformer架构是现代大语言模型的基础。",
        metadata={"id": 9, "topic": "大模型"},
    ),
    Document(
        page_content="Python是一种广泛使用的高级编程语言，由Guido van Rossum创建。",
        metadata={"id": 10, "topic": "编程语言"},
    ),
    Document(
        page_content="Rust是一种系统编程语言，注重安全性和性能。",
        metadata={"id": 11, "topic": "编程语言"},
    ),
    Document(
        page_content="FAISS是Facebook开发的向量相似度搜索库，支持大规模向量检索。",
        metadata={"id": 12, "topic": "向量检索"},
    ),
    Document(
        page_content="Redis是一种内存数据库，常用于缓存和消息队列。",
        metadata={"id": 13, "topic": "基础设施"},
    ),
    Document(
        page_content="Docker是一种容器化技术，用于打包和部署应用程序。",
        metadata={"id": 14, "topic": "基础设施"},
    ),
]


# ===== 检索器实现 =====


class BM25Retriever:
    def __init__(self, docs):
        self.docs = docs
        self.texts = [doc.page_content for doc in docs]
        self.tokenized_texts = [list(jieba.cut(t)) for t in self.texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

    def retrieve(self, query, k=3):
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.docs[i] for i in ranked]


class VectorRetriever:
    def __init__(self, docs, embeddings):
        self.docs = docs
        self.vectorstore = FAISS.from_documents(docs, embeddings)

    def retrieve(self, query, k=3):
        return self.vectorstore.similarity_search(query, k=k)


def rrf_fusion(results_list, k=60):
    doc_scores = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc.metadata.get("id", id(doc))
            score = 1 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
    sorted_ids = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    doc_map = {doc.metadata["id"]: doc for doc in SAMPLE_DOCS if "id" in doc.metadata}
    return [doc_map[doc_id] for doc_id, _ in sorted_ids if doc_id in doc_map]


class ZhipuReranker:
    def __init__(self, api_key):
        self.api_key = api_key

    def rerank(self, query, documents, top_n=3):
        resp = httpx.post(
            "https://open.bigmodel.cn/api/paas/v4/rerank",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "rerank",
                "query": query,
                "documents": documents,
                "top_n": top_n,
                "return_documents": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["results"]


def hybrid_retrieve(bm25_retriever, vector_retriever, query, k=3):
    bm25_results = bm25_retriever.retrieve(query, k=k * 2)
    vector_results = vector_retriever.retrieve(query, k=k * 2)
    fused = rrf_fusion([bm25_results, vector_results])
    return fused[:k]


def hybrid_rerank_retrieve(bm25_retriever, vector_retriever, reranker, query, k=3):
    bm25_results = bm25_retriever.retrieve(query, k=k * 2)
    vector_results = vector_retriever.retrieve(query, k=k * 2)
    fused = rrf_fusion([bm25_results, vector_results])
    candidates = fused[: k * 3]
    candidate_texts = [doc.page_content for doc in candidates]
    rerank_results = reranker.rerank(query, candidate_texts, top_n=k)
    return [candidates[r["index"]] for r in rerank_results]


# ===== 评测框架 =====

# 人工标注的 ground truth：查询 → 相关文档 id 集合
GROUND_TRUTH = {
    "深度学习和机器学习有什么关系？": {0, 1, 2},
    "OpenAI GPT-4": {4, 3, 5},
    "用什么语言做向量检索": {12, 10},
    "容器技术有哪些": {14, 13},
    "神经网络在视觉领域怎么用": {7, 6, 2},
    "NLP和大模型有什么关系": {8, 9, 3, 4},
    "Python和Rust的区别": {10, 11},
    "什么是人工智能": {1, 0, 6, 8},
}

QUERY_SCENARIOS = {
    "深度学习和机器学习有什么关系？": "语义关联",
    "OpenAI GPT-4": "精确关键词",
    "用什么语言做向量检索": "混合查询",
    "容器技术有哪些": "同义词/隐含意图",
    "神经网络在视觉领域怎么用": "跨领域关联",
    "NLP和大模型有什么关系": "多主题交叉",
    "Python和Rust的区别": "对比类",
    "什么是人工智能": "宽泛查询",
}


def precision_at_k(results: List[Document], relevant_ids: Set[int], k: int) -> float:
    """Precision@K：返回的 K 个结果中，有多少是相关的"""
    retrieved_ids = {doc.metadata["id"] for doc in results[:k]}
    if len(retrieved_ids) == 0:
        return 0.0
    return len(retrieved_ids & relevant_ids) / len(retrieved_ids)


def recall_at_k(results: List[Document], relevant_ids: Set[int], k: int) -> float:
    """Recall@K：所有相关文档中，有多少被返回了"""
    retrieved_ids = {doc.metadata["id"] for doc in results[:k]}
    if len(relevant_ids) == 0:
        return 0.0
    return len(retrieved_ids & relevant_ids) / len(relevant_ids)


def topic_diversity(results: List[Document]) -> int:
    """结果覆盖了多少个不同主题"""
    return len({doc.metadata.get("topic") for doc in results})


def evaluate():
    bm25 = BM25Retriever(SAMPLE_DOCS)
    vector = VectorRetriever(SAMPLE_DOCS, embeddings)
    reranker = ZhipuReranker(zhipu_api_key)
    k = 3

    methods = {
        "BM25": lambda q: bm25.retrieve(q, k=k),
        "向量检索": lambda q: vector.retrieve(q, k=k),
        "混合(BM25+向量+RRF)": lambda q: hybrid_retrieve(bm25, vector, q, k=k),
        "混合+Rerank": lambda q: hybrid_rerank_retrieve(bm25, vector, reranker, q, k=k),
    }

    # 逐查询评测
    all_scores = {name: {"precision": [], "recall": []} for name in methods}

    for query, scenario in QUERY_SCENARIOS.items():
        relevant_ids = GROUND_TRUTH[query]

        print("=" * 80)
        print(f"查询: {query}  (场景: {scenario})")
        print(f"相关文档: {relevant_ids}")
        print("=" * 80)

        for name, retrieve_fn in methods.items():
            results = retrieve_fn(query)
            p = precision_at_k(results, relevant_ids, k)
            r = recall_at_k(results, relevant_ids, k)
            div = topic_diversity(results)

            all_scores[name]["precision"].append(p)
            all_scores[name]["recall"].append(r)

            retrieved_ids = [doc.metadata["id"] for doc in results]
            print(f"\n  【{name}】 P@{k}={p:.2f}  R@{k}={r:.2f}  多样性={div}")
            print(f"    返回: {retrieved_ids}")
            hit = set(retrieved_ids) & relevant_ids
            miss = relevant_ids - set(retrieved_ids)
            print(f"    命中: {hit if hit else '无'}  漏掉: {miss if miss else '无'}")

        print()

    # 汇总
    print("=" * 80)
    print("汇总对比 (8 个查询的平均值)")
    print("=" * 80)
    print(f"{'方法':<20} {'Avg P@3':<12} {'Avg R@3':<12}")
    print("-" * 44)
    for name in methods:
        avg_p = sum(all_scores[name]["precision"]) / len(all_scores[name]["precision"])
        avg_r = sum(all_scores[name]["recall"]) / len(all_scores[name]["recall"])
        print(f"{name:<20} {avg_p:<12.3f} {avg_r:<12.3f}")

    print()
    print("小结：")
    print("  - BM25 在精确关键词查询上表现好，但同义词/语义查询容易漏召回")
    print("  - 向量检索在语义关联上表现好，但精确关键词可能排不到前面")
    print("  - 混合检索通过 RRF 融合，兼顾关键词和语义，整体更稳定")
    print("  - Rerank 在混合检索基础上做精排，能纠正一些 RRF 的误排")


if __name__ == "__main__":
    print("检索效果对比评测\n")
    evaluate()
