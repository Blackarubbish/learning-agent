# RAG Part 2：向量化与存储

## 概述

RAG 流程的第二步：把文本块转为向量，存入向量数据库，支持语义检索。

**类比 Node.js**：
- Embedding ≈ 文本 → 向量的"翻译器"
- VectorStore ≈ 支持语义查询的"数据库"

---

## 1. Embeddings - 文本转向量

### 什么是 Embedding？

把文字变成一串数字（向量），语义相似的文字在向量空间中距离更近。

```
"苹果" → [0.12, -0.34, 0.78, ...]
"水果" → [0.11, -0.31, 0.75, ...]  # 距离近

"苹果" → [0.12, -0.34, 0.78, ...]
"汽车" → [-0.89, 0.23, 0.11, ...]   # 距离远
```

### LangChain Embeddings

```python
from langchain_openai import OpenAIEmbeddings

# 需要设置 OPENAI_API_KEY 环境变量
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 单文本
vec = embeddings.embed_query("你好，世界")
print(len(vec))  # 1536 维度

# 多文本
texts = ["苹果", "水果", "汽车"]
vecs = embeddings.embed_documents(texts)
```

---

## 2. VectorStore - 向量存储

### 常用 VectorStore 对比

| 数据库 | 说明 | 适用场景 | Node.js 类比 |
|--------|------|---------|-------------|
| FAISS | Facebook 开源，本地 | 小规模数据、demo | 内存数据库 |
| Chroma | 专门为 LLM 设计 | 原型开发 | SQLite |
| Milvus | 生产级分布式 | 大规模数据 | PostgreSQL |

### FAISS - 最简单的选择

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# 1. 创建 Embeddings
embeddings = OpenAIEmbeddings()

# 2. 从文档创建 VectorStore
vectorstore = FAISS.from_documents(
    documents=chunks,  # 上一步分割的文档块
    embedding=embeddings,
)

# 3. 保存到本地
vectorstore.save_local("faiss_index")

# 4. 加载
loaded = FAISS.load_local("faiss_index", embeddings)
```

---

## 3. 检索 (Retrieval)

### 基本检索

```python
# 相似度搜索
results = vectorstore.similarity_search("什么是机器学习？", k=3)

for doc in results:
    print(doc.page_content)
    print("---")
```

### 带相似度分数

```python
results = vectorstore.similarity_search_with_score("什么是机器学习？", k=3)

for doc, score in results:
    print(f"分数: {score:.4f}")
    print(doc.page_content)
    print("---")
```

### MMR (Maximum Marginal Relevance)

多样性检索，避免返回重复内容：

```python
results = vectorstore.max_marginal_relevance_search(
    "机器学习",
    k=3,
    fetch_k=10,  # 从更多结果中选
)
```

---

## 4. Retriever - 封装检索接口

把 VectorStore 封装成 Retriever，方便 Chain 调用：

```python
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 3}  # 默认返回 3 个
)

# 在 Chain 中使用
from langchain.chains import RetrievalQA

qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
```

---

## 5. 完整 RAG 流程

```python
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# 1. 加载
loader = TextLoader("data.txt")
docs = loader.load()

# 2. 分割
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# 3. 向量化存储
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(chunks, embeddings)

# 4. 检索
results = vectorstore.similarity_search("什么是深度学习？", k=2)

# 5. 查看结果
for doc in results:
    print(doc.page_content)
```

---

## 核心问题自测

1. **Embedding 的作用是什么？**
   - 把文本转为数值向量，让语义相似的文本在向量空间中距离更近。

2. **FAISS 和 Chroma 的区别是什么？**
   - FAISS 更底层、性能高，适合大规模数据；Chroma 上手简单，专为 LLM 设计。

3. **similarity_search 和 max_marginal_relevance_search 的区别？**
   - similarity_search 返回最相似的；MMR 在相似和多样间平衡，避免重复。

4. **Retriever 和 VectorStore 的关系？**
   - Retriever 是封装后的检索接口，VectorStore 是底层存储。

---

## 安装依赖

```bash
pip install faiss langchain-openai
```

---

## 下一步

Day 5-6 将整合 FastAPI + LangChain + RAG，构建完整的 Naive RAG 应用。
