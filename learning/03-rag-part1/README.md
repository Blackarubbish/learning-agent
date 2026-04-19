# RAG Part 1：文档加载与分割

## 概述

RAG（Retrieval-Augmented Generation）= 检索 + 生成。Part 1 聚焦**文档处理**：如何把各种格式的文档加载进来并分割成小块。

**类比 Node.js**：
- Document Loader ≈ 文件系统读取 + 解析库
- Text Splitter ≈ 流式处理中的 chunk 逻辑

---

## 1. Document Loader

LangChain 提供统一的文档加载接口 `Document`。

```python
from langchain_core.documents import Document

doc = Document(
    page_content="这是文档内容",
    metadata={"source": "file.txt", "page": 1}
)
```

### 常用 Loader

| Loader | 用途 | Node.js 类比 |
|--------|------|-------------|
| `TextLoader` | 纯文本 | `fs.readFileSync` |
| `PDFPlumberLoader` | PDF | `pdf-parse` |
| `UnstructuredFileLoader` | 通用文件 | `formidable` |
| `WebBaseLoader` | 网页 | `cheerio` |

### 实际用法

```python
from langchain_community.document_loaders import TextLoader, PDFPlumberLoader

# 文本文件
loader = TextLoader("data.txt")
docs = loader.load()

# PDF 文件
loader = PDFPlumberLoader("data.pdf")
docs = loader.load()
```

---

## 2. Text Splitter

**为什么需要分割？**
- LLM 有上下文窗口限制（4K-128K tokens）
- 切割后每个 chunk 独立检索
- 太大导致相似度稀释，太小丢失语义

### 核心参数

| 参数 | 说明 | 经验值 |
|------|------|--------|
| `chunk_size` | 每块字符数 | 500-1000 |
| `chunk_overlap` | 块间重叠字符 | 50-100 |
| `separator` | 分割符 | `\n\n` |

### 常用 Splitter

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "？", "！", ""]
)

chunks = splitter.split_documents(docs)
```

**RecursiveCharacterTextSplitter** 会按 separator 列表递归分割，确保块语义完整。

---

## 3. 完整流程

```python
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 1. 加载
loader = TextLoader("data.txt")
docs = loader.load()

# 2. 分割
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
chunks = splitter.split_documents(docs)

# 3. 查看结果
print(f"原始文档数: {len(docs)}")
print(f"分割后块数: {len(chunks)}")
print(f"示例块: {chunks[0]}")
```

---

## 4. 中文分割策略

中文没有空格，需要特殊处理：

```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=[
        "\n\n",  # 段落
        "\n",    # 换行
        "。",    # 句号
        "！",
        "？",
        "；",    # 分号
        "，",
        " ",     # 空格
        ""       # 按字符
    ]
)
```

---

## 5. 分割策略对比

| 策略 | 适用场景 | 缺点 |
|------|---------|------|
| `RecursiveCharacterTextSplitter` | 通用（推荐） | 需要调参 |
| `CharacterTextSplitter` | 简单文本 | 粗暴按字符切 |
| `TokenTextSplitter` | 精确 token 控制 | 英文为主 |
| `SemanticChunker` | 保持语义完整 | 需额外模型 |

---

## 核心问题自测

1. **Document Loader 和 Text Splitter 的分工是什么？**
   - Loader 负责加载原始文档，Splitter 负责把大文档切成小 chunk。

2. **chunk_size 和 chunk_overlap 的作用是什么？**
   - chunk_size 控制每块大小，chunk_overlap 保持块间上下文连续。

3. **为什么中文分割需要更多 separator？**
   - 中文没有空格分词，需要按标点和换行来切分。

4. **RecursiveCharacterTextSplitter 的递归逻辑是怎样的？**
   - 按 separator 列表依次尝试切分，前一个失败才用下一个。

---

## 安装依赖

```bash
pip install langchain-community pypdf
```

---

## 下一步

Day 4 将学习 RAG Part 2：向量化与存储，使用 Embeddings + VectorStore 构建检索索引。
