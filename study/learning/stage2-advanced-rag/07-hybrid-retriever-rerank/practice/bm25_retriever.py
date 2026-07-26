"""
BM25 检索器实战

对比纯向量检索 vs BM25 检索的效果差异：
- 向量检索：擅长语义匹配，但对精确关键词不敏感
- BM25 检索：擅长关键词匹配，但无法理解语义

运行：
  uv run python bm25_retriever.py
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
    """智谱AI Embeddings包装器"""

    def __init__(self, client):
        self.client = client

    def embed_documents(self, texts):
        response = self.client.embeddings.create(model="embedding-3", input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text):
        response = self.client.embeddings.create(model="embedding-3", input=[text])
        return response.data[0].embedding


embeddings = ZhipuEmbeddings(zhipu_client)

# 示例文档：特意设计一些需要关键词精确匹配的场景
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

    def retrieve(self, query: str, k: int = 3) -> list[tuple]:
        """检索，返回 (Document, score) 列表"""
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)
        scored_docs = list(zip(self.docs, scores, strict=False))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[:k]


class VectorRetriever:
    """向量检索器"""

    def __init__(self, docs: list[Document], embeddings: Embeddings):
        self.docs = docs
        self.vectorstore = FAISS.from_documents(docs, embeddings)

    def retrieve(self, query: str, k: int = 3) -> list[tuple]:
        """检索，返回 (Document, score) 列表"""
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        # FAISS 返回 L2 距离，越小越相似，取负值以便统一排序方向
        return [(doc, -score) for doc, score in results]


def compare_retrievers(query: str, k: int = 3):
    """对比 BM25 和向量检索效果"""

    bm25_retriever = BM25Retriever(SAMPLE_DOCS)
    vector_retriever = VectorRetriever(SAMPLE_DOCS, embeddings)

    print("=" * 80)
    print(f"查询: {query}")
    print("=" * 80)

    print("\n【BM25 检索】(关键词匹配)")
    print("-" * 40)
    bm25_results = bm25_retriever.retrieve(query, k=k)
    for i, (doc, score) in enumerate(bm25_results, 1):
        print(f"  [{i}] score={score:.4f} | {doc.page_content}")

    print("\n【向量检索】(语义匹配)")
    print("-" * 40)
    vector_results = vector_retriever.retrieve(query, k=k)
    for i, (doc, score) in enumerate(vector_results, 1):
        print(f"  [{i}] score={score:.4f} | {doc.page_content}")

    # 分析差异
    bm25_contents = {doc.page_content for doc, _ in bm25_results}
    vector_contents = {doc.page_content for doc, _ in vector_results}
    common = bm25_contents & vector_contents
    bm25_only = bm25_contents - vector_contents
    vector_only = vector_contents - bm25_contents

    print("\n【差异分析】")
    print("-" * 40)
    print(f"  共同结果: {len(common)} 个")
    print(f"  仅 BM25: {len(bm25_only)} 个 → {bm25_only if bm25_only else '无'}")
    print(f"  仅向量:  {len(vector_only)} 个 → {vector_only if vector_only else '无'}")
    print()


if __name__ == "__main__":
    print("BM25 检索器实战\n")

    # 测试1: 语义查询 — 向量检索应更擅长
    compare_retrievers("什么是深度学习？它和AI有什么关系？", k=3)

    # 测试2: 精确关键词查询 — BM25 应更擅长
    compare_retrievers("OpenAI GPT-4", k=3)

    # 测试3: 语义+关键词混合查询
    compare_retrievers("用什么语言做向量检索", k=3)

    # 测试4: 简单同义词查询
    compare_retrievers("容器技术有哪些", k=3)
