# Agent Study

AI Agent 学习项目，基于 FastAPI + LangChain + RAG 技术栈。

## 技术栈

- **FastAPI** - Web 框架
- **LangChain** - LLM 应用开发
- **FAISS** - 向量数据库
- **DeepSeek / 智谱AI** - LLM 和 Embeddings

## 项目结构

```
.
├── learning/              # 学习笔记和实践代码
│   ├── 01-fastapi/      # FastAPI 基础
│   ├── 02-langchain/    # LangChain 入门
│   ├── 03-rag-part1/    # RAG Part 1 - 文档加载与分割
│   ├── 04-rag-part2/    # RAG Part 2 - Embeddings 与向量检索
│   └── 05-naive-rag/    # Naive RAG 实战
├── pyproject.toml        # uv 依赖配置
└── uv.lock              # 锁定依赖版本
```

## 快速开始

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 运行练习
cd learning/05-naive-rag/practice
uv run uvicorn main:app --reload --port 8000
```

## 学习进度

参见 [STUDY_PROGRESS.md](./STUDY_PROGRESS.md)
