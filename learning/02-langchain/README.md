# LangChain 快速入门

## 概述

LangChain 是一个用于构建 LLM 应用的框架，核心价值：**组件化 + Chain 组合**。

**类比 Node.js**：
- LangChain ≈ Node.js 的 `langchain` 版工具库
- LCEL ≈ Node.js 的 `pipe()` 或 `compose()`
- Chain ≈ Node.js 的 middleware pipeline

---

## 核心概念速览

| 概念 | 说明 | Node.js 类比 |
|------|------|-------------|
| Model I/O | LLM 调用 + Prompt 管理 | `openai` SDK |
| Retrieval | 文档加载、分割、向量检索 | 数据库查询 |
| Chains | 把多个组件串联执行 | `pipe()` / `compose()` |
| Agents | 模型决定调用什么工具 | 策略模式 |
| Memory | 对话上下文存储 | Session/Redis |
| Callbacks | 事件钩子 | EventEmitter |

---

## 1. Model I/O - LLM 调用

**Node.js (OpenAI SDK)**:
```javascript
import OpenAI from 'openai'
const client = new OpenAI()
const response = await client.chat.completions.create({
  model: 'gpt-4',
  messages: [{ role: 'user', content: 'Hello' }]
})
```

**LangChain**:
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
response = llm.invoke("Hello")
```

---

## 2. Prompt Templates - 可复用 Prompt

**问题**：Hardcode prompt 不灵活。

**LangChain 方案**：
```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 {language} 专家"),
    ("user", "用 {language} 写一个 {task}")
])

chain = prompt | llm
response = chain.invoke({
    "language": "Python",
    "task": "快速排序"
})
```

**Node.js 类比**：
```javascript
// Node.js 没有官方方案，通常自己实现模板
const prompt = `你是 ${language} 专家，用 ${language} 写 ${task}`
```

---

## 3. Output Parsers - 结构化输出

```python
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

class Answer(BaseModel):
    score: int
    explanation: str

parser = JsonOutputParser(pydantic_object=Answer)

prompt = ChatPromptTemplate.from_messages([
    ("user", "{question}")
])

chain = prompt | llm | parser
result = chain.invoke({"question": "解释光合作用"})
# result = {"score": 8, "explanation": "..."}
```

---

## 4. LCEL - LangChain Expression Language

**核心语法**：`|` 管道操作符，把组件串联成 Chain。

```python
chain = prompt | llm | output_parser
```

**对比 Node.js**：
```javascript
// Node.js 的 pipe 模式
const result = await pipe(
  transformInput,
  callAPI,
  parseOutput
)(input)
```

### 常用组件

| 组件 | 作用 |
|------|------|
| `prompt` | 输入模板 |
| `llm` / `chat_model` | 模型调用 |
| `output_parser` | 输出解析 |
| ` RunnablePassthrough` | 透传数据 |
| `RunnableBranch` | 条件分支 |

---

## 5. Chains - 组合执行

### LLMChain（简单链）

```python
from langchain.chains import LLMChain

chain = LLMChain(prompt=prompt, llm=llm)
result = chain.invoke({"language": "Go", "task": "HTTP server"})
```

### Sequential Chain（顺序链）

```python
from langchain.chains import SequentialChain

chain = SequentialChain(
    chains=[chain1, chain2],
    input_variables=["input"],
    output_variables=["output"]
)
```

### LCEL 写法（更推荐）

```python
chain = (
    {"context": lambda x: x["input"]}
    | prompt
    | llm
    | parser
)
```

---

## 6. Retrieval - RAG 核心

### 文档加载

```python
from langchain_community.document_loaders import TextLoader

loader = TextLoader("data.txt")
docs = loader.load()
```

### 文档分割

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)
```

### 向量存储

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

vectorstore = FAISS.from_documents(chunks, OpenAIEmbeddings())
retriever = vectorstore.as_retriever()
```

---

## 7. 构建 RAG Chain

```python
from langchain.chains import RetrievalQA

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
)

result = qa_chain.invoke({"query": "文档里说了什么？"})
```

---

## 核心问题自测

1. **LangChain 的 LCEL 管道操作符 `|` 是什么意思？**
   - 将多个组件串联，前一个的输出作为后一个的输入，类似 Unix 管道。

2. **Prompt Template 的作用是什么？**
   - 模板化 prompt，动态注入变量，提高复用性。

3. **Output Parser 解决什么问题？**
   - 将 LLM 的自由文本输出转为结构化数据（JSON、Pydantic 等）。

4. **Retrieval 流程中的 Document Loader、Splitter、VectorStore 分别负责什么？**
   - Loader 加载文档，Splitter 分割文本，VectorStore 建向量索引支持检索。

5. **RAG Chain 的核心组件有哪些？**
   - Retriever（检索）+ LLM（生成），检索相关文档后交给 LLM 生成答案。

---

## 安装

```bash
pip install langchain langchain-openai langchain-community
```

## 学习资源

- [LangChain Quickstart](https://python.langchain.com/v0.1/docs/get_started/quickstart/)
- [吴恩达 LangChain 课程](https://learn.deeplearning.ai/langchain/lesson/1/introduction/)
- [动手学大模型应用开发](https://datawhalechina.github.io/llm-universe/)

## 下一步

接下来我们将学习 RAG Part 1：文档加载与分割。
