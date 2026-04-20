# Query Transformation (Day 8)

## 概述

Query Transformation 是在检索前对用户查询进行改写优化的技术，用于提升召回质量。核心思想是：原始查询可能与知识库中的文档表达方式不同，通过改写让查询更接近文档风格。

## 三种核心方法

### 1. Multi-Query (多查询)

**原理**：让 LLM 生成多个不同角度的查询版本，并行检索后合并结果。

**适用场景**：覆盖面广、召回率要求高

```
原始查询 → LLM生成5个改写版本 → 并行检索 → RRF融合 → 最终结果
```

**代码示例**：

```python
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# 初始化
embedding = OpenAIEmbeddings()
vectordb = FAISS.load_local("faiss_index", embedding)

# 创建 MultiQueryRetriever
llm = ChatOpenAI(model="gpt-4o-mini")
retriever = MultiQueryRetriever.from_llm(
    retriever=vectordb.as_retriever(search_kwargs={"k": 3}),
    llm=llm,
    verbose=True
)

# 检索
results = retriever.get_relevant_documents("什么是深度学习？")
```

### 2. HyDE (Hypothetical Document Embeddings)

**原理**：先让 LLM 生成一个"假设性答案文档"，再用这个假设文档去检索相似文档。

**适用场景**：复杂问题、抽象概念、查询与文档语义差异大

```
原始查询 → LLM生成假设文档 → 向量化假设文档 → 检索相似真实文档
```

**代码示例**：

```python
from langchain_community.retrievers import ChatGPTMessageEmbeddingsRetriever
from langchain_community.vectorstores import Chroma

# HyDE 需要配合 LangChain CLI 使用
# pip install -U langchain-cli
# langchain app add hyde

# 或者手动实现 HyDE
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# 步骤1: 生成假设文档
hyde_prompt = ChatPromptTemplate.from_template(
    """根据用户问题生成一个假设性的答案文档。
    这个文档应该清晰地回答问题，包含可能出现在真实文档中的关键词。

    问题: {question}
    假设答案:"""
)

hyde_chain = hyde_prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()

# 步骤2: 用假设文档检索
hypothetical_doc = hyde_chain.invoke({"question": "什么是机器学习？"})
results = vectordb.similarity_search(hypothetical_doc, k=3)
```

### 3. Sub-Query / Query Decomposition (子查询分解)

**原理**：将复杂问题拆分为多个简单子问题，分别检索后合并。

**适用场景**：多跳推理、复合问题、需要多维度信息

**代码示例**：

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 问题分解
decompose_prompt = ChatPromptTemplate.from_template(
    """将复杂问题拆分为2-3个简单的子问题。

    复杂问题: {question}
    子问题 (用换行分隔):"""
)

decompose_chain = decompose_prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()

# 分解问题
sub_questions = decompose_chain.invoke({"question": "2023年诺贝尔物理学奖得主是谁？他们的主要贡献是什么？"})
# 输出:
# 1. 2023年诺贝尔物理学奖得主是谁？
# 2. 他们各自的主要贡献是什么？

# 分别检索后合并结果
sub_queries = sub_questions.strip().split("\n")
all_results = []
for sq in sub_queries:
    results = retriever.get_relevant_documents(sq)
    all_results.extend(results)

# 去重合并
unique_results = list({doc.page_content: doc for doc in all_results}.values())
```

---

## 检索结果融合 - RRF (Reciprocal Rank Fusion)

当使用多查询或在多个检索系统（稀疏+密集）时，需要融合结果。RRF 是常用方法：

```python
def rrf_fusion(results_list, k=60):
    """Reciprocal Rank Fusion"""
    score_dict = {}
    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc.page_content[:50]  # 用前50字符作为ID
            score = score_dict.get(doc_id, 0) + 1 / (k + rank + 1)
            score_dict[doc_id] = score

    sorted_docs = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)
    return sorted_docs
```

**参数说明**：
- `k`：通常设为 60，值越小排名靠前的文档权重越高

---

## 方法对比

| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Multi-Query** | 覆盖面广、实现简单 | 增加 LLM 调用次数 | 通用问答 |
| **HyDE** | 语义匹配好 | 假设文档可能不准确 | 抽象概念 |
| **Sub-Query** | 可处理复杂多跳问题 | 延迟增加 | 复合问题 |

---

## 实践任务

1. 实现 Multi-Query 检索，对比单查询 vs 多查询的召回率
2. 实现 HyDE 检索，观察效果
3. 实现 Sub-Query 分解，处理复杂问题

---

## 参考资源

- [LangChain MultiQueryRetriever 源码](https://github.com/langchain-ai/langchain/pull/25035)
- [CSDN: 探索MultiQueryRetriever](https://blog.csdn.net/m0_57781768/article/details/141834427)
- [CSDN: HyDE与LangChain](https://blog.csdn.net/azzxcvhj/article/details/144961546)