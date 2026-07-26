"""
Week 2 综合实战：构建 Advanced RAG 系统

目标：整合 Query Transformation + BM25 + 向量检索 + RRF + Rerank 到统一管线。

运行：
  uv run python learning/stage2-advanced-rag/11-weekly-summary/practice/starter.py
"""

import os

import httpx
import jieba
from common import (
    check,
    get_or_create_embeddings,
    get_or_create_llm,
    load_dotenv_if_needed,
    reset,
    section,
    summary,
)
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from rank_bm25 import BM25Okapi

load_dotenv_if_needed()
embeddings = get_or_create_embeddings()
llm = get_or_create_llm(temperature=0)


# ============================================================
# 示例文档（和之前章节一致）
# ============================================================
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


class Reranker:
    """智谱 Rerank API 封装 — 对候选文档精细打分排序"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/rerank"

    def rerank(self, query: str, documents: list[str], top_n: int = 3) -> list[dict]:
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
        return resp.json()["results"]


# ============================================================
# TODO 1: Naive RAG（基准线）
# ============================================================
# 提示：直接向量检索 + LLM 生成，不做任何优化
# 参考 05-naive-rag 的实现方式


class NaiveRAG:
    """最基础的 RAG：向量检索 → LLM 生成"""

    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.vectorstore = FAISS.from_documents(docs, embeddings)
        self._setup_prompt()

    def _setup_prompt(self):
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一个智能助手，使用以下上下文回答问题。如果上下文中没有相关信息，请如实说明。\n\n上下文：\n{context}",
                ),
                ("human", "{question}"),
            ]
        )
        self.chain = self.prompt | llm | StrOutputParser()

    def ask(self, question: str, k: int = 3) -> dict:
        retrieved_docs = self.vectorstore.similarity_search(question, k=k)
        context = "\n".join([doc.page_content for doc in retrieved_docs])
        answer = self.chain.invoke({"context": context, "question": question})
        return {"answer": answer, "contexts": retrieved_docs}


# ============================================================
# TODO 2: Advanced RAG（完整管线）
# ============================================================
# 管线：Multi-Query 改写 → BM25 + 向量检索 → RRF 融合 → Rerank 精排 → LLM 生成
# 提示：逐模块构建，每完成一个模块就测试一下


class AdvancedRAG:
    """完整 Advanced RAG 管线"""

    def __init__(self, docs: list[Document], rerank_api_key: str = None):
        self.docs = docs
        self.texts = [doc.page_content for doc in docs]

        # TODO 2.1: 初始化 BM25 检索器（需要 jieba 分词）
        self.tokenized_texts = [list(jieba.cut(text)) for text in self.texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

        # TODO 2.2: 初始化向量检索器（FAISS）
        self.vectorstore = FAISS.from_documents(self.docs, embeddings)

        # TODO 2.3: 设置 Multi-Query Chain（用 LangChain ChatPromptTemplate）
        self.multi_query_chain = (
            ChatPromptTemplate.from_template(
                """请将以下问题改写成 {num} 个不同的查询，要求覆盖不同的表达方式和角度。

问题：{question}

改写后的查询："""
            )
            | llm
            | StrOutputParser()
        )
        # LLM
        self.llm = llm

        # Rerank（可选，检查环境变量）
        self.rerank_api_key = rerank_api_key or os.getenv("ZHIPU_API_KEY")

        self.reranker = Reranker(self.rerank_api_key) if self.rerank_api_key else None

        # 生成 Chain
        self.generate_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一个智能助手，使用以下上下文回答问题。如果上下文中没有相关信息，请如实说明。\n\n上下文：\n{context}",
                ),
                ("human", "{question}"),
            ]
        )
        self.generate_chain = self.generate_prompt | llm | StrOutputParser()

    # ---- TODO 2.4: Query Transformation ----
    def _generate_queries(self, question: str, num: int = 4) -> list[str]:
        """用 LLM 生成多个查询改写版本"""
        result = self.multi_query_chain.invoke({"question": question, "num": num})
        queries = [q.strip() for q in result.split("\n") if q.strip()]
        # 始终包含原始查询
        if question not in queries:
            queries.insert(0, question)
        return queries

    # ---- TODO 2.5: BM25 检索 ----
    def _bm25_retrieve(self, query: str, k: int = 6) -> list[Document]:
        """BM25 关键词检索"""
        tokenized = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.docs[i] for i in ranked]

    # ---- TODO 2.6: 向量检索 ----
    def _vector_retrieve(self, query: str, k: int = 6) -> list[Document]:
        return self.vectorstore.similarity_search(query, k=k)

    # ---- TODO 2.7: RRF 融合 ----
    def _rrf_fusion(self, results_list: list[list[Document]], k: int = 60) -> list[Document]:
        """RRF 融合多路检索结果"""
        doc_scores = {}
        for results in results_list:
            for rank, doc in enumerate(results):
                doc_id = doc.page_content  # 简单用内容作为 ID，实际应用中应该有唯一 ID
                score = 1 / (k + rank + 1)  # RRF 评分
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        doc_map = {d.page_content: d for d in self.docs}
        return [doc_map[content] for content, _ in sorted_docs]

    # ---- TODO 2.8: Rerank 精排（用智谱 Rerank API） ----
    def _rerank(self, query: str, docs: list[Document], top_n: int = 3) -> list[Document]:
        """对候选文档精排，返回 top_n"""
        if not self.rerank_api_key or not self.reranker:
            # 没有 API Key，直接返回前 top_n
            return docs[:top_n]
        doc_contents = [doc.page_content for doc in docs]
        rerank_results = self.reranker.rerank(query, doc_contents, top_n=top_n)
        final = []
        for r in rerank_results:
            doc = docs[r["index"]]
            final.append(
                Document(
                    page_content=doc.page_content,
                    metadata={**doc.metadata, "rerank_score": r["relevance_score"]},
                )
            )
        return final

    # ---- TODO 2.9: 检索主入口 ----
    def retrieve(self, question: str, k: int = 3) -> list[Document]:
        """完整检索管线：Multi-Query → 混合检索 → RRF → Rerank"""
        # 1) 生成多个查询
        queries = self._generate_queries(question, num=4)
        # 2) 对每个查询执行 BM25 和向量检索
        all_results = []
        for q in queries:
            bm25_results = self._bm25_retrieve(q, k * 2)
            vector_results = self._vector_retrieve(q, k * 2)
            all_results.append(bm25_results)
            all_results.append(vector_results)
        # 3) RRF 融合
        fused = self._rrf_fusion(all_results, k=60)
        # 4) Rerank 精排
        reranked = self._rerank(question, fused, top_n=k)
        return reranked

    # ---- TODO 2.10: 问答 ----
    def ask(self, question: str, k: int = 3) -> dict:
        """检索 + 生成，返回 {"answer": ..., "contexts": ...}"""
        retrieved_docs = self.retrieve(question, k=k)
        context = "\n".join([doc.page_content for doc in retrieved_docs])
        answer = self.generate_chain.invoke({"context": context, "question": question})
        return {"answer": answer, "contexts": retrieved_docs}


# ============================================================
# TODO 3: 对比测试
# ============================================================
# 用相同的查询对比 NaiveRAG 和 AdvancedRAG 的结果差异


def compare_rag_systems():
    """对比 Naive RAG 和 Advanced RAG 的检索结果"""
    naive = NaiveRAG(SAMPLE_DOCS)
    advanced = AdvancedRAG(SAMPLE_DOCS)

    test_queries = [
        "深度学习和人工智能有什么关系？",  # 语义查询 — 同义词/概念关联
        "OpenAI 有哪些模型？",  # 精确查询 — 特定关键词
        "用什么语言做向量检索？",  # 混合查询 — 语义+关键词
    ]

    for query in test_queries:
        section(f"查询: {query}")

        naive_result = naive.ask(query, k=3)
        advanced_result = advanced.ask(query, k=3)

        print("\n【Naive RAG 上下文】")
        for i, doc in enumerate(naive_result["contexts"], 1):
            print(f"  [{i}] {doc.page_content}")

        print("\n【Advanced RAG 上下文】")
        for i, doc in enumerate(advanced_result["contexts"], 1):
            score = doc.metadata.get("rerank_score", "N/A")
            print(f"  [{i}] (rerank={score}) {doc.page_content}")

        print(f"\n【Naive RAG 答案】\n{naive_result['answer']}")
        print(f"\n【Advanced RAG 答案】\n{advanced_result['answer']}\n")

        check("Naive RAG 有上下文", len(naive_result["contexts"]) > 0)
        check("Advanced RAG 有上下文", len(advanced_result["contexts"]) > 0)


# ============================================================
# 自检
# ============================================================
if __name__ == "__main__":
    reset()

    section("1. Naive RAG 基准测试")
    naive = NaiveRAG(SAMPLE_DOCS)
    result = naive.ask("深度学习和机器学习有什么关系？")
    print(f"答案: {result['answer']}")
    print(f"检索上下文数量: {len(result['contexts'])}")
    check("Naive RAG 返回了答案", len(result["answer"]) > 0)

    section("2. Advanced RAG 测试")
    advanced = AdvancedRAG(SAMPLE_DOCS)
    result = advanced.ask("深度学习和机器学习有什么关系？")
    print(f"答案: {result['answer']}")
    print(f"检索上下文数量: {len(result['contexts'])}")
    check("Advanced RAG 返回了答案", len(result["answer"]) > 0)

    section("3. 对比测试")
    compare_rag_systems()
    check("对比测试完成", True)

    summary()
