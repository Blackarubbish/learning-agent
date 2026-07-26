"""
混合检索实战：BM25 + 向量检索 + RRF 融合

核心思路：
- BM25 擅长关键词匹配，向量检索擅长语义匹配
- RRF (Reciprocal Rank Fusion) 将两路结果融合，取长补短
- 融合公式：score = Σ 1/(k + rank)，rank 越靠前分数越高

运行：
  uv run python hybrid_retriever.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")
import jieba
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from rank_bm25 import BM25Okapi
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
    """BM25 检索器"""

    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.texts = [doc.page_content for doc in docs]
        self.tokenized_texts = [list(jieba.cut(text)) for text in self.texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

    def retrieve(self, query: str, k: int = 3) -> list[Document]:
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.docs[i] for i in ranked]


class VectorRetriever:
    """向量检索器"""

    def __init__(self, docs: list[Document], embeddings: Embeddings):
        self.docs = docs
        self.vectorstore = FAISS.from_documents(docs, embeddings)

    def retrieve(self, query: str, k: int = 3) -> list[Document]:
        return self.vectorstore.similarity_search(query, k=k)


def rrf_fusion(results_list: list[list[Document]], k: int = 60) -> list[Document]:
    """
    RRF (Reciprocal Rank Fusion) 融合算法

    核心思想：每路检索中排名靠前的文档获得更高分数，多路结果累加后排序。
    公式：score(doc) = Σ 1/(k + rank + 1)

    参数 k=60 是经典值，k 越大 → 排名差异的影响越小 → 更平滑
    """
    doc_scores = {}

    for results in results_list:
        for rank, doc in enumerate(results):
            # 用文档内容前 100 字符作为唯一标识
            doc_id = doc.page_content[:100]
            score = 1 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score

    # 按融合分数排序
    sorted_ids = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

    # 用 doc_id 找回原始 Document
    doc_map = {doc.page_content[:100]: doc for doc in SAMPLE_DOCS}
    return [doc_map[doc_id] for doc_id, _ in sorted_ids]


class HybridRetriever:
    """
    混合检索器：BM25 + 向量检索 + RRF 融合

    流程：
    1. BM25 检索 top-k*2 候选
    2. 向量检索 top-k*2 候选
    3. RRF 融合两路结果，返回 top-k
    """

    def __init__(self, docs: list[Document], embeddings: Embeddings):
        self.bm25_retriever = BM25Retriever(docs)
        self.vector_retriever = VectorRetriever(docs, embeddings)

    def retrieve(self, query: str, k: int = 3, rrf_k: int = 60) -> list[Document]:
        # 先多召回一些候选，避免 RRF 融合后不足 k 个
        bm25_results = self.bm25_retriever.retrieve(query, k=k * 2)
        vector_results = self.vector_retriever.retrieve(query, k=k * 2)

        # RRF 融合
        fused = rrf_fusion([bm25_results, vector_results], k=rrf_k)
        return fused[:k]


def compare_retrievers(query: str, k: int = 3):
    """对比三种检索方式"""

    bm25 = BM25Retriever(SAMPLE_DOCS)
    vector = VectorRetriever(SAMPLE_DOCS, embeddings)
    hybrid = HybridRetriever(SAMPLE_DOCS, embeddings)

    print("=" * 80)
    print(f"查询: {query}")
    print("=" * 80)

    bm25_results = bm25.retrieve(query, k=k)
    vector_results = vector.retrieve(query, k=k)
    hybrid_results = hybrid.retrieve(query, k=k)

    for name, results in [
        ("BM25 检索", bm25_results),
        ("向量检索", vector_results),
        ("混合检索 (BM25+向量+RRF)", hybrid_results),
    ]:
        print(f"\n【{name}】")
        print("-" * 40)
        for i, doc in enumerate(results, 1):
            print(f"  [{i}] {doc.page_content}")

    # 分析混合检索的来源
    bm25_set = {doc.page_content for doc in bm25_results}
    vector_set = {doc.page_content for doc in vector_results}
    hybrid_set = {doc.page_content for doc in hybrid_results}

    print("\n【融合效果】")
    print("-" * 40)
    from_bm25_only = hybrid_set & bm25_set - vector_set
    from_vector_only = hybrid_set & vector_set - bm25_set
    from_both = hybrid_set & bm25_set & vector_set
    new_docs = hybrid_set - bm25_set - vector_set

    print(f"  来自两路共同: {len(from_both)} 个")
    print(f"  仅来自 BM25: {len(from_bm25_only)} 个")
    print(f"  仅来自向量:  {len(from_vector_only)} 个")
    if new_docs:
        print(f"  RRF 提升上来的: {len(new_docs)} 个 → {new_docs}")
    print()


if __name__ == "__main__":
    print("混合检索实战：BM25 + 向量 + RRF\n")

    # 语义查询 — 向量检索优势场景
    compare_retrievers("什么是深度学习？它和AI有什么关系？", k=3)

    # 精确关键词查询 — BM25 优势场景
    compare_retrievers("OpenAI GPT-4", k=3)

    # 混合查询 — 需要两者配合
    compare_retrievers("用什么语言做向量检索", k=3)

    # 同义词查询
    compare_retrievers("容器技术有哪些", k=3)
