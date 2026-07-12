"""
混合检索 + Rerank 完整流程

流程：BM25 检索 → 向量检索 → RRF 融合 → Rerank 精排

Rerank 的作用：
- 初步检索（BM25 + 向量）是"粗筛"，快速从大量文档中召回候选
- Rerank 是"精排"，用专用模型对候选文档与查询的相关性做精细打分
- 类比：搜索引擎先返回 100 条结果，再根据点击率、时效性等二次排序

运行：
  uv run python hybrid_rerank_retriever.py
"""

import os
from pathlib import Path
from typing import List
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
    Document(page_content="深度学习是机器学习的一个分支，它使用多层神经网络来学习数据的表征。"),
    Document(page_content="机器学习是人工智能的一个子领域，关注如何让计算机从数据中学习。"),
    Document(page_content="神经网络是受生物神经系统启发的一种计算模型，是深度学习的基础。"),
    Document(page_content="GPT是一种基于Transformer的大语言模型，由OpenAI开发。"),
    Document(page_content="GPT-4是OpenAI最新的大型语言模型，具有强大的推理能力。"),
    Document(page_content="ChatGPT是OpenAI开发的对话应用，基于GPT模型构建。"),
    Document(page_content="计算机视觉是AI的一个分支，让计算机能够理解和处理图像。"),
    Document(page_content="卷积神经网络(CNN)是计算机视觉中常用的深度学习模型。"),
    Document(page_content="自然语言处理(NLP)是AI处理和理解人类语言的技术。"),
    Document(page_content="Transformer架构是现代大语言模型的基础。"),
    Document(page_content="Python是一种广泛使用的高级编程语言，由Guido van Rossum创建。"),
    Document(page_content="Rust是一种系统编程语言，注重安全性和性能。"),
    Document(page_content="FAISS是Facebook开发的向量相似度搜索库，支持大规模向量检索。"),
    Document(page_content="Redis是一种内存数据库，常用于缓存和消息队列。"),
    Document(page_content="Docker是一种容器化技术，用于打包和部署应用程序。"),
]


class BM25Retriever:
    def __init__(self, docs: List[Document]):
        self.docs = docs
        self.texts = [doc.page_content for doc in docs]
        self.tokenized_texts = [list(jieba.cut(text)) for text in self.texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.docs[i] for i in ranked]


class VectorRetriever:
    def __init__(self, docs: List[Document], embeddings: Embeddings):
        self.docs = docs
        self.vectorstore = FAISS.from_documents(docs, embeddings)

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        return self.vectorstore.similarity_search(query, k=k)


def rrf_fusion(results_list: List[List[Document]], k: int = 60) -> List[Document]:
    doc_scores = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc.page_content[:100]
            score = 1 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
    sorted_ids = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    doc_map = {doc.page_content[:100]: doc for doc in SAMPLE_DOCS}
    return [doc_map[doc_id] for doc_id, _ in sorted_ids]


class ZhipuReranker:
    """智谱AI Rerank 封装"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/rerank"

    def rerank(self, query: str, documents: List[str], top_n: int = 3) -> List[dict]:
        """
        对候选文档重排序

        返回格式：[{"index": 原始索引, "relevance_score": 分数, "document": 原文本}, ...]
        """
        resp = httpx.post(
            self.base_url,
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
        data = resp.json()
        return data["results"]


class HybridRerankRetriever:
    """
    混合检索 + Rerank 完整管线

    流程：
    1. BM25 检索 top-k*2 候选
    2. 向量检索 top-k*2 候选
    3. RRF 融合两路结果
    4. Rerank 对融合结果精排，返回 top-k
    """

    def __init__(self, docs: List[Document], embeddings: Embeddings, reranker_api_key: str):
        self.docs = docs
        self.bm25_retriever = BM25Retriever(docs)
        self.vector_retriever = VectorRetriever(docs, embeddings)
        self.reranker = ZhipuReranker(reranker_api_key)

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        # 1. 多召回候选
        bm25_results = self.bm25_retriever.retrieve(query, k=k * 2)
        vector_results = self.vector_retriever.retrieve(query, k=k * 2)

        # 2. RRF 融合
        fused = rrf_fusion([bm25_results, vector_results])
        candidates = fused[: k * 3]  # 多留一些给 Rerank 筛选

        # 3. Rerank 精排
        candidate_texts = [doc.page_content for doc in candidates]
        rerank_results = self.reranker.rerank(query, candidate_texts, top_n=k)

        # 4. 按 Rerank 返回的顺序组装结果
        final = []
        for r in rerank_results:
            doc = candidates[r["index"]]
            final.append(
                Document(
                    page_content=doc.page_content,
                    metadata={**doc.metadata, "rerank_score": r["relevance_score"]},
                )
            )
        return final


def compare_all_retrievers(query: str, k: int = 3):
    """对比四种检索方式"""

    bm25 = BM25Retriever(SAMPLE_DOCS)
    vector = VectorRetriever(SAMPLE_DOCS, embeddings)
    hybrid_results = rrf_fusion(
        [
            bm25.retrieve(query, k=k * 2),
            vector.retrieve(query, k=k * 2),
        ]
    )[:k]
    hybrid_rerank = HybridRerankRetriever(SAMPLE_DOCS, embeddings, zhipu_api_key)

    print("=" * 80)
    print(f"查询: {query}")
    print("=" * 80)

    bm25_results = bm25.retrieve(query, k=k)
    vector_results = vector.retrieve(query, k=k)
    rerank_results = hybrid_rerank.retrieve(query, k=k)

    for name, results in [
        ("1. BM25 检索", bm25_results),
        ("2. 向量检索", vector_results),
        ("3. 混合检索 (BM25+向量+RRF)", hybrid_results),
        ("4. 混合检索+Rerank", rerank_results),
    ]:
        print(f"\n【{name}】")
        print("-" * 40)
        for i, doc in enumerate(results, 1):
            score_info = ""
            if hasattr(doc, "metadata") and "rerank_score" in doc.metadata:
                score_info = f" (rerank: {doc.metadata['rerank_score']:.4f})"
            print(f"  [{i}] {doc.page_content}{score_info}")

    # 对比 RRF 和 Rerank 的差异
    hybrid_contents = [doc.page_content for doc in hybrid_results]
    rerank_contents = [doc.page_content for doc in rerank_results]
    if hybrid_contents != rerank_contents:
        print(f"\n【Rerank 调整了排序】")
        for i, (h, r) in enumerate(zip(hybrid_contents, rerank_contents)):
            changed = " ← 变化" if h != r else ""
            print(f"  位置{i + 1}: RRF={h[:30]}... → Rerank={r[:30]}...{changed}")
    else:
        print(f"\n【Rerank 确认了 RRF 的排序】")
    print()


if __name__ == "__main__":
    print("混合检索 + Rerank 完整流程\n")

    # 语义查询
    compare_all_retrievers("什么是深度学习？它和AI有什么关系？", k=3)

    # 精确关键词查询
    compare_all_retrievers("OpenAI GPT-4", k=3)

    # 混合查询
    compare_all_retrievers("用什么语言做向量检索", k=3)

    # 同义词查询
    compare_all_retrievers("容器技术有哪些", k=3)
