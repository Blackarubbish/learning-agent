"""
Query Transformation 实战

三种查询改写技术：
1. Multi-Query: 生成多个查询版本，并行检索后合并
2. HyDE: 生成假设文档，用假设文档检索
3. Sub-Query: 分解复杂问题为多个子问题

运行：
  python main.py
"""

import os
from typing import Annotated, List, Literal
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from zai import ZhipuAiClient
import uuid
from pathlib import Path

# API 配置
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
zhipu_api_key = os.getenv("ZHIPU_API_KEY")

if not deepseek_api_key:
    raise ValueError("DEEPSEEK_API_KEY environment variable not set")
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


# 初始化 Embeddings 和 LLM
embeddings = ZhipuEmbeddings(zhipu_client)
llm = ChatOpenAI(
    model="deepseek-chat",
    temperature=0,
    openai_api_key=deepseek_api_key,
    base_url="https://api.deepseek.com/v1",
)

# 示例文档
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
]


class BaseRetriever:
    """基础检索器接口"""

    def __init__(self, docs: List[Document], embeddings: Embeddings):
        self.docs = docs
        self.embeddings = embeddings
        self.vectorstore = FAISS.from_documents(docs, embeddings)

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        raise NotImplementedError


class MultiQueryRetriever(BaseRetriever):
    """
    Multi-Query 检索器

    原理：让 LLM 生成多个不同角度的查询版本，并行检索后合并结果
    """

    def __init__(
        self, docs: List[Document], embeddings: Embeddings, llm: ChatOpenAI, num_queries: int = 5
    ):
        super().__init__(docs, embeddings)
        self.num_queries = num_queries
        self.llm = llm
        self._setup_chain()

    def _setup_chain(self):
        """设置查询生成 Chain"""
        self.query_gen_chain = (
            ChatPromptTemplate.from_template(
                """你是一个信息检索专家。根据用户问题，生成 {num} 个不同的查询版本。
            每个查询应该从不同的角度或用不同的措辞来表达同一个问题。

            原始问题: {question}

            生成的查询（每行一个）:"""
            )
            | self.llm
            | StrOutputParser()
        )

    def _generate_queries(self, query: str) -> List[str]:
        """生成多个查询版本"""
        result = self.query_gen_chain.invoke({"question": query, "num_queries": self.num_queries})
        queries = [q.strip() for q in result.strip().split("\n") if q.strip()]
        return queries

    def _rrf_fusion(self, results_list: List[List[Document]], k: int = 60) -> List[Document]:
        """
        RRF (Reciprocal Rank Fusion) 融合

        对多个检索结果进行排名融合
        """
        doc_scores = {}

        for results in results_list:
            for rank, doc in enumerate(results):
                doc_id = id(doc)
                score = doc_scores.get(doc_id, 0) + 1 / (k + rank + 1)
                doc_scores[doc_id] = score

        # 按分数排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        doc_map = {id(doc): doc for doc in self.docs}

        return [doc_map[doc_id] for doc_id, _ in sorted_docs]

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        """检索"""
        # 1. 生成多个查询
        queries = self._generate_queries(query)
        print(f"生成的查询: {queries}")

        # 2. 并行检索
        results_list = []
        for q in queries:
            results = self.vectorstore.similarity_search(q, k=k)
            results_list.append(results)

        # 3. RRF 融合
        fused_results = self._rrf_fusion(results_list)

        return fused_results[:k]


class HyDERetriever(BaseRetriever):
    """
    HyDE (Hypothetical Document Embeddings) 检索器

    原理：先让 LLM 生成假设性答案文档，再用这个假设文档去检索
    """

    def __init__(self, docs: List[Document], embeddings: Embeddings, llm: ChatOpenAI):
        super().__init__(docs, embeddings)
        self.llm = llm
        self._setup_chain()

    def _setup_chain(self):
        """设置假设文档生成 Chain"""
        self.hyde_chain = (
            ChatPromptTemplate.from_template(
                """你是一个文档撰写专家。根据用户问题，生成一个假设性的答案文档。
            这个文档应该：
            1. 直接回答问题
            2. 包含可能出现在真实文档中的关键词
            3. 格式类似学术或技术文档

            问题: {question}

            假设答案文档:"""
            )
            | self.llm
            | StrOutputParser()
        )

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        """检索"""
        # 1. 生成假设文档
        hypothetical_doc = self.hyde_chain.invoke({"question": query})
        print(f"假设文档:\n{hypothetical_doc}\n")

        # 2. 用假设文档检索
        results = self.vectorstore.similarity_search(hypothetical_doc, k=k)

        return results


class SubQueryRetriever(BaseRetriever):
    """
    Sub-Query (子查询分解) 检索器

    原理：将复杂问题拆分为多个简单子问题，分别检索后合并
    """

    def __init__(self, docs: List[Document], embeddings: Embeddings, llm: ChatOpenAI):
        super().__init__(docs, embeddings)
        self.llm = llm
        self._setup_chain()

    def _setup_chain(self):
        """设置问题分解 Chain"""
        self.decompose_chain = (
            ChatPromptTemplate.from_template(
                """你是一个信息检索专家。将复杂问题拆分为2-3个简单的子问题。
            每个子问题应该能够独立回答，并且合起来能回答原问题。

            复杂问题: {question}

            子问题（每行一个）:"""
            )
            | self.llm
            | StrOutputParser()
        )

    def _deduplicate(self, docs: List[Document]) -> List[Document]:
        """去重"""
        seen_content = set()
        unique_docs = []
        for doc in docs:
            content = doc.page_content[:50]
            if content not in seen_content:
                seen_content.add(content)
                unique_docs.append(doc)
        return unique_docs

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        """检索"""
        # 1. 分解问题
        sub_queries_text = self.decompose_chain.invoke({"question": query})
        sub_queries = [q.strip() for q in sub_queries_text.strip().split("\n") if q.strip()]
        print(f"子问题: {sub_queries}")

        # 2. 分别检索
        all_results = []
        for sq in sub_queries:
            results = self.vectorstore.similarity_search(sq, k=k)
            all_results.extend(results)

        # 3. 去重合并
        unique_results = self._deduplicate(all_results)

        return unique_results[:k]


def compare_retrievers(query: str, k: int = 3):
    """对比三种检索器效果"""

    retrievers = {
        "Naive (直接检索)": lambda: BaseRetriever(SAMPLE_DOCS, embeddings),
        "Multi-Query": lambda: MultiQueryRetriever(SAMPLE_DOCS, embeddings, llm, num_queries=4),
        "HyDE": lambda: HyDERetriever(SAMPLE_DOCS, embeddings, llm),
        "Sub-Query": lambda: SubQueryRetriever(SAMPLE_DOCS, embeddings, llm),
    }

    print("=" * 80)
    print(f"查询: {query}")
    print("=" * 80)

    for name, retriever_fn in retrievers.items():
        print(f"\n【{name}】")
        print("-" * 40)
        try:
            retriever = retriever_fn()
            results = retriever.retrieve(query, k=k)
            print(f"返回 {len(results)} 个结果:")
            for i, doc in enumerate(results, 1):
                print(f"  [{i}] {doc.page_content}")
        except Exception as e:
            print(f"错误: {e}")
        print()


def test_single_retriever():
    """单独测试 Multi-Query 检索器"""

    print("\n" + "=" * 80)
    print("测试 Multi-Query 检索器")
    print("=" * 80)

    retriever = MultiQueryRetriever(SAMPLE_DOCS, embeddings, llm, num_queries=4)

    query = "深度学习和机器学习有什么关系？"
    print(f"\n查询: {query}\n")

    results = retriever.retrieve(query, k=3)

    print("\n检索结果:")
    for i, doc in enumerate(results, 1):
        print(f"  [{i}] {doc.page_content}")

    return results


def test_hyde():
    """单独测试 HyDE 检索器"""

    print("\n" + "=" * 80)
    print("测试 HyDE 检索器")
    print("=" * 80)

    retriever = HyDERetriever(SAMPLE_DOCS, embeddings, llm)

    query = "什么是神经网络？"
    print(f"\n查询: {query}\n")

    results = retriever.retrieve(query, k=3)

    print("\n检索结果:")
    for i, doc in enumerate(results, 1):
        print(f"  [{i}] {doc.page_content}")

    return results


def test_subquery():
    """单独测试 Sub-Query 检索器"""

    print("\n" + "=" * 80)
    print("测试 Sub-Query 检索器")
    print("=" * 80)

    retriever = SubQueryRetriever(SAMPLE_DOCS, embeddings, llm)

    query = "2023年诺贝尔物理学奖得主是谁？他们的主要贡献是什么？"
    print(f"\n查询: {query}\n")

    results = retriever.retrieve(query, k=3)

    print("\n检索结果:")
    for i, doc in enumerate(results, 1):
        print(f"  [{i}] {doc.page_content}")

    return results


if __name__ == "__main__":
    print("Query Transformation 实战")
    print("=" * 80)

    # 对比所有检索器
    query1 = "深度学习和机器学习有什么关系？"
    compare_retrievers(query1, k=3)

    query2 = "什么是神经网络？"
    compare_retrievers(query2, k=3)

    query3 = "GPT模型和Transformer架构有什么关系？"
    compare_retrievers(query3, k=3)

    # 单独测试（取消注释可以单独测试某个检索器）
    # test_single_retriever()
    # test_hyde()
    # test_subquery()
