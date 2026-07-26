# RAG Part 1 学习问题记录

## Q&A

---

### Q: 怎么分割 PDF？

```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("your_file.pdf")
docs = loader.load()

# 分割
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)
```

pypdf 已安装，无需额外依赖。
