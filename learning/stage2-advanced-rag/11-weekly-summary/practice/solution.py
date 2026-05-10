"""
Week 2 综合实战：Advanced RAG 系统 — 完整实现

管线：Multi-Query 改写 → BM25 + 向量检索 → RRF 融合 → Rerank 精排 → LLM 生成

运行：
  uv run python learning/stage2-advanced-rag/11-weekly-summary/practice/solution.py
"""

from common import load_dotenv_if_needed, get_or_create_embeddings, get_or_create_llm, section, check, summary, reset

load_dotenv_if_needed()
embeddings = get_or_create_embeddings()
llm = get_or_create_llm(temperature=0)

import os
from typing import List

import httpx
import jieba
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from rank_bm25 import BM25Okapi

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


class NaiveRAG:
    """最基础的 RAG：向量检索 → LLM 生成"""

    def __init__(self, docs: List[Document]):
        self.docs = docs
        self.vectorstore = FAISS.from_documents(docs, embeddings)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个智能助手，使用以下上下文回答问题。如果上下文中没有相关信息，请如实说明。\n\n上下文：\n{context}"),
            ("human", "{question}"),
        ])
        self.chain = self.prompt | llm | StrOutputParser()

    def ask(self, question: str, k: int = 3) -> dict:
        retrieved = self.vectorstore.similarity_search(question, k=k)
        context = "\n\n".join(doc.page_content for doc in retrieved)
        answer = self.chain.invoke({"context": context, "question": question})
        return {"answer": answer, "contexts": retrieved}


class Reranker:
    """智谱 Rerank API 封装 — 对候选文档精细打分排序"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/rerank"

    def rerank(self, query: str, documents: List[str], top_n: int = 3) -> List[dict]:
        resp = httpx.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "rerank", "query": query, "documents": documents, "top_n": top_n, "return_documents": True},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["results"]


class AdvancedRAG:
    """
    完整 Advanced RAG 管线

    流程：Multi-Query 改写 → BM25 + 向量检索 → RRF 融合 → Rerank 精排 → LLM 生成
    每步都有独立方法，方便单独测试和调参。
    """

    def __init__(self, docs: List[Document], rerank_api_key: str = None):
        self.docs = docs
        self.texts = [doc.page_content for doc in docs]

        # BM25 索引 — 用 jieba 分词支持中文
        self.tokenized_texts = [list(jieba.cut(text)) for text in self.texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

        # 向量索引
        self.vectorstore = FAISS.from_documents(docs, embeddings)

        # Multi-Query Chain — 让 LLM 生成多个查询改写版本
        self.multi_query_chain = (
            ChatPromptTemplate.from_template(
                """根据用户问题生成 {num} 个不同角度的改写版本，提升召回率。每行一个查询。

用户问题: {question}

改写版本:"""
            )
            | llm
            | StrOutputParser()
        )

        # Rerank 可选 — 没有 API key 时跳过精排
        self.reranker = Reranker(rerank_api_key) if rerank_api_key else None

        # 生成 Chain
        self.generate_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个智能助手，使用以下上下文回答问题。如果上下文中没有相关信息，请如实说明。\n\n上下文：\n{context}"),
            ("human", "{question}"),
        ])
        self.generate_chain = self.generate_prompt | llm | StrOutputParser()

    # ============ Query Transformation ============

    def _generate_queries(self, question: str, num: int = 4) -> List[str]:
        """生成多个改写查询，覆盖不同角度提高召回率"""
        result = self.multi_query_chain.invoke({"question": question, "num": num})
        queries = [q.strip() for q in result.strip().split("\n") if q.strip()]
        # 始终包含原始查询
        if question not in queries:
            queries.insert(0, question)
        return queries

    # ============ BM25 检索 ============

    def _bm25_retrieve(self, query: str, k: int = 6) -> List[Document]:
        """BM25 关键词检索 — 精确匹配，不受语义漂移影响"""
        tokenized = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.docs[i] for i in ranked]

    # ============ 向量检索 ============

    def _vector_retrieve(self, query: str, k: int = 6) -> List[Document]:
        """FAISS 向量检索 — 语义匹配，理解同义词和概念关联"""
        return self.vectorstore.similarity_search(query, k=k)

    # ============ RRF 融合 ============

    def _rrf_fusion(self, results_list: List[List[Document]], k: int = 60) -> List[Document]:
        """
        RRF (Reciprocal Rank Fusion) — 按排名而非绝对分数融合多路检索。

        k=60 是经验值：太小则排名权重差异大，太大则趋近平均。60 被大多数实验验证为合理默认值。
        """
        doc_scores = {}
        for results in results_list:
            for rank, doc in enumerate(results):
                # 用 page_content 前 100 字符做去重 key
                key = doc.page_content[:100]
                doc_scores[key] = doc_scores.get(key, 0) + 1 / (k + rank + 1)
        sorted_keys = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        doc_map = {doc.page_content[:100]: doc for doc in self.docs}
        return [doc_map[key] for key, _ in sorted_keys]

    # ============ Rerank ============

    def _rerank(self, query: str, docs: List[Document], top_n: int = 3) -> List[Document]:
        """Rerank 精排 — 用专用模型对候选做精细相关性打分"""
        if not self.reranker or len(docs) <= top_n:
            return docs[:top_n]

        candidate_texts = [doc.page_content for doc in docs]
        results = self.reranker.rerank(query, candidate_texts, top_n=top_n)

        final = []
        for r in results:
            doc = docs[r["index"]]
            final.append(Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "rerank_score": r["relevance_score"]},
            ))
        return final

    # ============ 检索主入口 ============

    def retrieve(self, question: str, k: int = 3) -> List[Document]:
        """
        完整检索管线：

        1. Multi-Query 改写 → 多角度召回
        2. 对每个改写查询做 BM25 + 向量检索
        3. RRF 融合所有结果
        4. Rerank 精排 → 返回 top-k
        """
        # Step 1: 查询改写
        queries = self._generate_queries(question)

        # Step 2: 多路检索（每个改写查询都做 BM25 + 向量）
        all_results = []
        for q in queries:
            all_results.append(self._bm25_retrieve(q, k=k * 2))
            all_results.append(self._vector_retrieve(q, k=k * 2))

        # Step 3: RRF 融合
        fused = self._rrf_fusion(all_results)

        # Step 4: Rerank 精排（多留一些候选给 Rerank 筛选）
        candidates = fused[: k * 3]
        return self._rerank(question, candidates, top_n=k)

    # ============ 问答 ============

    def ask(self, question: str, k: int = 3) -> dict:
        contexts = self.retrieve(question, k=k)
        context_text = "\n\n".join(doc.page_content for doc in contexts)
        answer = self.generate_chain.invoke({"context": context_text, "question": question})
        return {"answer": answer, "contexts": contexts}


def compare_rag_systems():
    """对比 Naive RAG 和 Advanced RAG"""
    naive = NaiveRAG(SAMPLE_DOCS)
    advanced = AdvancedRAG(SAMPLE_DOCS, rerank_api_key=os.getenv("ZHIPU_API_KEY"))

    test_queries = [
        # 语义查询 — 需要理解概念关联，同义词
        "深度学习和人工智能有什么关系？",
        # 精确查询 — 特定技术名词
        "OpenAI 有哪些模型？",
        # 混合查询 — 既需要语义理解又有关键词
        "用什么语言做向量检索？",
    ]

    for query in test_queries:
        section(f"查询: {query}")

        naive_result = naive.ask(query, k=3)
        advanced_result = advanced.ask(query, k=3)

        print(f"\n【Naive RAG 上下文】")
        for i, doc in enumerate(naive_result["contexts"], 1):
            print(f"  [{i}] {doc.page_content}")

        print(f"\n【Advanced RAG 上下文】")
        for i, doc in enumerate(advanced_result["contexts"], 1):
            score = doc.metadata.get("rerank_score", "N/A")
            print(f"  [{i}] (rerank={score}) {doc.page_content}")

        print(f"\n【Naive RAG 答案】\n{naive_result['answer']}")
        print(f"\n【Advanced RAG 答案】\n{advanced_result['answer']}")
        print()

        # 断言
        check(f"Naive RAG 有上下文", len(naive_result["contexts"]) > 0)
        check(f"Advanced RAG 有上下文", len(advanced_result["contexts"]) > 0)
        check("两者返回了答案", len(naive_result["answer"]) > 0 and len(advanced_result["answer"]) > 0)

    summary()


if __name__ == "__main__":
    reset()

    section("1. 单次查询测试 — Naive RAG")
    naive = NaiveRAG(SAMPLE_DOCS)
    result = naive.ask("深度学习和机器学习有什么关系？")
    print(f"答案: {result['answer']}")
    print(f"上下文数量: {len(result['contexts'])}")
    check("Naive RAG 返回了答案", len(result["answer"]) > 0)
    check("Naive RAG 返回了上下文", len(result["contexts"]) == 3)

    section("2. 单次查询测试 — Advanced RAG")
    advanced = AdvancedRAG(SAMPLE_DOCS, rerank_api_key=os.getenv("ZHIPU_API_KEY"))
    result = advanced.ask("深度学习和机器学习有什么关系？")
    print(f"答案: {result['answer']}")
    print(f"上下文数量: {len(result['contexts'])}")
    check("Advanced RAG 返回了答案", len(result["answer"]) > 0)
    check("Advanced RAG 返回了上下文", len(result["contexts"]) > 0)

    section("3. 全管线对比测试")
    compare_rag_systems()

    print("\n提示: 对比 Naive 和 Advanced 的上下文顺序和质量，观察 Rerank 对排序的调整。")
