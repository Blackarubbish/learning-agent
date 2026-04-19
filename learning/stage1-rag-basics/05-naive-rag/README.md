# Naive RAG 实战：端到端文档问答系统

## 概述

整合 FastAPI + LangChain + RAG，构建一个完整的文档问答 API 服务。

**类比 Node.js**：就像 Express 整合 Mongoose 操作 MongoDB，这里 FastAPI 整合 LangChain 操作向量数据库。

---

## 1. 完整 RAG 流程回顾

```
用户问题 → 检索(Retriever) → 向量数据库(FAISS) → 获取相关文档 → LLM 生成回答
```

前面两节我们学了：
- Part 1: 文档加载与分割
- Part 2: 向量化与存储

今天整合成完整系统。

---

## 2. 项目结构

```
05-naive-rag/
├── README.md           # 学习大纲
├── practice/
│   ├── main.py         # 主程序（完整 RAG API）
│   ├── requirements.txt
│   └── data/
│       └── sample.txt  # 示例文档
└── notes/
    └── qa.md          # 问题汇总
```

---

## 3. Naive RAG 核心代码

### 3.1 初始化 RAG（一次性准备）

```python
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

def initialize_rag(file_path: str):
    """初始化 RAG 系统（加载文档、分割、向量化）"""
    # 1. 加载文档
    loader = TextLoader(file_path)
    docs = loader.load()

    # 2. 分割
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)

    # 3. 向量化存储
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # 4. 保存
    vectorstore.save_local("faiss_index")

    return vectorstore
```

### 3.2 构建问答 Chain

```python
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

def build_qa_chain(vectorstore):
    """构建问答 Chain"""
    llm = ChatOpenAI(model="gpt-4o-mini")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True  # 返回来源文档
    )

    return qa_chain
```

### 3.3 问答函数

```python
def ask_question(qa_chain, question: str):
    """问答"""
    result = qa_chain({"query": question})

    print(f"问题: {result['query']}")
    print(f"回答: {result['result']}")
    print(f"\n参考文档:")
    for i, doc in enumerate(result['source_documents'], 1):
        print(f"  [{i}] {doc.page_content[:100]}...")
```

---

## 4. FastAPI 封装

### 4.1 主程序

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
import os

app = FastAPI(title="Naive RAG API")

class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    answer: str
    sources: list[str]

vectorstore = None
qa_chain = None

@app.on_event("startup")
def startup():
    """启动时初始化 RAG"""
    global vectorstore, qa_chain

    data_path = os.path.join(os.path.dirname(__file__), "data", "sample.txt")

    # 已有索引则加载，否则创建
    if os.path.exists("faiss_index"):
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.load_local("faiss_index", embeddings)
    else:
        loader = TextLoader(data_path)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(docs)
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_documents(chunks, embeddings)
        vectorstore.save_local("faiss_index")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = ChatOpenAI(model="gpt-4o-mini")
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True
    )

@app.post("/ask", response_model=QuestionResponse)
def ask_question(req: QuestionRequest):
    """问答接口"""
    if not qa_chain:
        raise HTTPException(status_code=500, detail="RAG 未初始化")

    result = qa_chain({"query": req.question})

    return QuestionResponse(
        answer=result["result"],
        sources=[doc.page_content for doc in result["source_documents"]]
    )

@app.get("/health")
def health():
    return {"status": "ok"}
```

### 4.2 运行服务

```bash
cd practice
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### 4.3 测试

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是深度学习？"}'
```

---

## 5. 完整示例运行

```python
# 一次性初始化和问答
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA

# 初始化
loader = TextLoader("data/sample.txt")
docs = loader.load()
chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
vectorstore = FAISS.from_documents(chunks, OpenAIEmbeddings())

# 构建 Chain
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o-mini"),
    retriever=retriever,
    return_source_documents=True
)

# 问答
result = qa_chain({"query": "什么是机器学习？"})
print(result["result"])
```

---

## 核心问题自测

1. **Naive RAG 的完整流程是什么？**
   - 文档加载 → 分割 → 向量化 → 存储 → 检索 → 生成

2. **FastAPI 在 RAG 系统中的作用？**
   - 提供 HTTP API 接口，让用户可以通过 HTTP 请求进行问答

3. **为什么要保存向量索引到本地？**
   - 避免重复向量化，直接加载已构建好的索引加快启动速度

4. **return_source_documents=True 的作用？**
   - 返回参考文档来源，增加回答的可信度和可解释性

---

## 安装依赖

```bash
cd practice
pip install fastapi uvicorn faiss langchain-openai langchain-community langchain
```

---

## 下一步

Week 2 将学习 **Advanced RAG**：Query Transformation、混合检索、Reranker 等优化技术。