"""
端到端 RAG 评估流水线 - 对比 Naive RAG vs Advanced RAG

流程：
1. 用相同文档 + 相同测试问题
2. Naive RAG: 纯向量检索 + 直接生成
3. Advanced RAG: 混合检索(BM25+向量+RRF) + Rerank + 生成
4. 用 RAGAs 评估两者，输出对比报告

运行：
  uv run python 03_eval_pipeline.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

import httpx
import jieba
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)
from rank_bm25 import BM25Okapi

# === 基础设施 ===

zhipu_api_key = os.getenv("ZHIPU_API_KEY")
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

# 评估用 LLM
evaluator_llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=deepseek_api_key,
    temperature=0,
)

# 生成用 LLM（RAG 系统内部用的模型）
generator_llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=deepseek_api_key,
    temperature=0,
)


# Embeddings
class ZhipuEmbeddings(Embeddings):
    def __init__(self, api_key):
        self.api_key = api_key

    def embed_documents(self, texts):
        resp = httpx.post(
            "https://open.bigmodel.cn/api/paas/v4/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "embedding-3", "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["data"]]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


embeddings = ZhipuEmbeddings(zhipu_api_key)


# === 文档库 ===

DOCUMENTS = [
    Document(
        page_content="深度学习是机器学习的一个分支，它使用多层神经网络来学习数据的表征。深度学习在图像识别、语音识别和自然语言处理等领域取得了突破性进展。",
        metadata={"id": 0},
    ),
    Document(
        page_content="机器学习是人工智能的一个子领域，关注如何让计算机从数据中学习。主要方法包括监督学习、无监督学习和强化学习。",
        metadata={"id": 1},
    ),
    Document(
        page_content="神经网络是受生物神经系统启发的一种计算模型，是深度学习的基础。常见的神经网络架构包括CNN、RNN和Transformer。",
        metadata={"id": 2},
    ),
    Document(
        page_content="GPT是一种基于Transformer的大语言模型，由OpenAI开发。GPT-4是最新版本，具有强大的推理和多模态能力。",
        metadata={"id": 3},
    ),
    Document(
        page_content="Python是一种广泛使用的高级编程语言，由Guido van Rossum创建。Python在数据科学、机器学习和Web开发中非常流行。",
        metadata={"id": 4},
    ),
    Document(
        page_content="FAISS是Facebook开发的向量相似度搜索库，支持GPU加速和大规模向量检索，是构建RAG系统的常用工具。",
        metadata={"id": 5},
    ),
    Document(
        page_content="RAG（检索增强生成）是一种将信息检索与大语言模型结合的技术。它先检索相关文档，再将文档作为上下文提供给LLM生成答案。",
        metadata={"id": 6},
    ),
    Document(
        page_content="BM25是一种基于词频的概率检索算法，是Elasticsearch默认的相关性评分算法。它对精确关键词匹配非常有效。",
        metadata={"id": 7},
    ),
    Document(
        page_content="Transformer架构采用自注意力机制，是现代大语言模型的基础。它解决了RNN的序列依赖问题，支持并行计算。",
        metadata={"id": 8},
    ),
    Document(
        page_content="向量数据库（如Milvus、FAISS、Pinecone）专门用于存储和检索高维向量，是构建语义检索系统的核心组件。",
        metadata={"id": 9},
    ),
    Document(
        page_content="Rerank模型对初步检索结果进行二次排序，能显著提升检索精度。Cohere Rerank是常用的Rerank服务。",
        metadata={"id": 10},
    ),
    Document(
        page_content="LangChain是一个用于构建LLM应用的开源框架，提供了文档加载、切分、检索、生成等模块化组件。",
        metadata={"id": 11},
    ),
]

# === 测试问题 + 标准答案 ===

TEST_SET = [
    {
        "question": "深度学习和机器学习有什么关系？",
        "reference": "深度学习是机器学习的一个分支，使用多层神经网络学习数据表征。机器学习是人工智能的子领域，让计算机从数据中学习。",
    },
    {
        "question": "RAG 技术的工作原理是什么？",
        "reference": "RAG是一种将信息检索与大语言模型结合的技术，先检索相关文档，再将文档作为上下文提供给LLM生成答案。",
    },
    {
        "question": "FAISS 和向量数据库的关系？",
        "reference": "FAISS是Facebook开发的向量相似度搜索库，支持GPU加速和大规模向量检索。向量数据库（如Milvus、FAISS、Pinecone）是语义检索系统的核心组件。",
    },
    {
        "question": "Transformer 为什么重要？",
        "reference": "Transformer架构采用自注意力机制，是现代大语言模型的基础。它解决了RNN的序列依赖问题，支持并行计算。",
    },
    {
        "question": "Python 在 AI 领域有哪些应用？",
        "reference": "Python在数据科学、机器学习和Web开发中非常流行，是AI领域最常用的编程语言之一。",
    },
]


# === 检索器实现 ===


class NaiveRetriever:
    """纯向量检索"""

    def __init__(self, docs, embeddings):
        self.docs = docs
        self.vectorstore = FAISS.from_documents(docs, embeddings)

    def retrieve(self, query, k=3):
        return self.vectorstore.similarity_search(query, k=k)


class AdvancedRetriever:
    """混合检索(BM25+向量+RRF) + Rerank"""

    def __init__(self, docs, embeddings, api_key):
        self.docs = docs
        self.texts = [doc.page_content for doc in docs]

        # BM25 索引
        self.tokenized = [list(jieba.cut(t)) for t in self.texts]
        self.bm25 = BM25Okapi(self.tokenized)

        # 向量索引
        self.vectorstore = FAISS.from_documents(docs, embeddings)

        # Rerank
        self.api_key = api_key

    def _rrf_fusion(self, bm25_results, vector_results, k=60):
        doc_scores = {}
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.metadata["id"]
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1 / (k + rank + 1)
        for rank, doc in enumerate(vector_results):
            doc_id = doc.metadata["id"]
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1 / (k + rank + 1)
        doc_map = {doc.metadata["id"]: doc for doc in self.docs}
        sorted_ids = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_map[doc_id] for doc_id, _ in sorted_ids if doc_id in doc_map]

    def _rerank(self, query, documents, top_n=3):
        resp = httpx.post(
            "https://open.bigmodel.cn/api/paas/v4/rerank",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "rerank",
                "query": query,
                "documents": [doc.page_content for doc in documents],
                "top_n": top_n,
                "return_documents": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json()["results"]
        return [documents[r["index"]] for r in results]

    def retrieve(self, query, k=3):
        # 1. BM25 检索
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_top = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[
            : k * 2
        ]
        bm25_results = [self.docs[i] for i in bm25_top]

        # 2. 向量检索
        vector_results = self.vectorstore.similarity_search(query, k=k * 2)

        # 3. RRF 融合
        fused = self._rrf_fusion(bm25_results, vector_results)[: k * 2]

        # 4. Rerank
        reranked = self._rerank(query, fused, top_n=k)
        return reranked


# === 生成答案 ===

RAG_PROMPT = """请根据以下上下文回答问题。如果上下文中没有相关信息，请说"根据现有信息无法回答"。

上下文：
{context}

问题：{question}

回答："""


def generate_answer(query, contexts, llm):
    context_text = "\n".join(f"- {c.page_content}" for c in contexts)
    prompt = RAG_PROMPT.format(context=context_text, question=query)
    response = llm.invoke(prompt)
    return response.content


# === 运行 RAG 系统 + 收集评估数据 ===


def run_rag_and_collect(retriever, test_set, llm, system_name):
    """运行 RAG 系统，收集 RAGAs 评估所需的数据"""
    samples = []

    print(f"\n{'=' * 60}")
    print(f"运行 {system_name}")
    print(f"{'=' * 60}")

    for item in test_set:
        query = item["question"]
        reference = item["reference"]

        # 检索
        contexts = retriever.retrieve(query, k=3)

        # 生成
        answer = generate_answer(query, contexts, llm)

        # 收集
        sample = SingleTurnSample(
            user_input=query,
            response=answer,
            retrieved_contexts=[c.page_content for c in contexts],
            reference=reference,
        )
        samples.append(sample)

        print(f"\n  Q: {query}")
        print(f"  A: {answer[:80]}...")
        print(f"  检索到 {len(contexts)} 个文档")

    return samples


# === 主流程 ===

print("端到端 RAG 评估流水线")
print("=" * 60)
print(f"文档数: {len(DOCUMENTS)}")
print(f"测试问题数: {len(TEST_SET)}")
print("评估指标: Faithfulness / Answer Relevancy / Context Precision / Context Recall\n")

# 构建 Naive RAG
naive_retriever = NaiveRetriever(DOCUMENTS, embeddings)
naive_samples = run_rag_and_collect(
    naive_retriever, TEST_SET, generator_llm, "Naive RAG (纯向量检索)"
)

# 构建 Advanced RAG
advanced_retriever = AdvancedRetriever(DOCUMENTS, embeddings, zhipu_api_key)
advanced_samples = run_rag_and_collect(
    advanced_retriever, TEST_SET, generator_llm, "Advanced RAG (混合检索+Rerank)"
)

# === RAGAs 评估 ===

metrics = [
    Faithfulness(),
    AnswerRelevancy(),
    ContextPrecision(),
    ContextRecall(),
]

# 为 AnswerRelevancy 设置 generate_n=1（DeepSeek 兼容）
for m in metrics:
    if hasattr(m, "generate_n"):
        m.generate_n = 1

print(f"\n{'=' * 60}")
print("RAGAs 评估: Naive RAG")
print(f"{'=' * 60}")
naive_dataset = EvaluationDataset(samples=naive_samples)
naive_result = evaluate(
    naive_dataset,
    metrics=metrics,
    llm=evaluator_llm,
    embeddings=OpenAIEmbeddings(
        model="embedding-3", base_url="https://open.bigmodel.cn/api/paas/v4", api_key=zhipu_api_key
    ),
)
print(naive_result)

print(f"\n{'=' * 60}")
print("RAGAs 评估: Advanced RAG")
print(f"{'=' * 60}")
advanced_dataset = EvaluationDataset(samples=advanced_samples)
advanced_result = evaluate(
    advanced_dataset,
    metrics=metrics,
    llm=evaluator_llm,
    embeddings=OpenAIEmbeddings(
        model="embedding-3", base_url="https://open.bigmodel.cn/api/paas/v4", api_key=zhipu_api_key
    ),
)
print(advanced_result)

# === 对比报告 ===

print(f"\n{'=' * 60}")
print("对比报告: Naive RAG vs Advanced RAG")
print(f"{'=' * 60}")

metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
print(f"{'指标':<25} {'Naive RAG':<15} {'Advanced RAG':<15} {'变化':<10}")
print("-" * 65)

# EvaluationResult._repr_dict 包含各指标的平均值
naive_scores = naive_result._repr_dict
adv_scores = advanced_result._repr_dict

for metric in metric_names:
    naive_score = naive_scores.get(metric, 0)
    adv_score = adv_scores.get(metric, 0)
    if naive_score > 0:
        change = (adv_score - naive_score) / naive_score * 100
        change_str = f"{change:+.1f}%"
    else:
        change_str = "N/A"
    print(f"{metric:<25} {naive_score:<15.4f} {adv_score:<15.4f} {change_str}")

print("\n小结：")
n_faith = naive_scores.get("faithfulness", 0)
a_faith = adv_scores.get("faithfulness", 0)
n_prec = naive_scores.get("context_precision", 0)
a_prec = adv_scores.get("context_precision", 0)
n_recall = naive_scores.get("context_recall", 0)
a_recall = adv_scores.get("context_recall", 0)

print(
    f"  - Faithfulness: Advanced RAG {'提升' if a_faith > n_faith else '下降/持平'} (Rerank 过滤不相关噪声 → 答案更忠实)"
)
print(
    f"  - Context Precision: Advanced RAG {'提升' if a_prec > n_prec else '下降/持平'} (Rerank 重排 → 相关文档更靠前)"
)
print(
    f"  - Context Recall: Advanced RAG {'提升' if a_recall > n_recall else '下降/持平'} (混合检索 → 覆盖更广)"
)
print("  - Answer Relevancy: 两个系统生成的答案相似，差异主要来自检索质量的影响")
