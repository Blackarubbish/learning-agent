# Agent Study — AI Agent 引导的 RAG 学习项目

> **核心理念**：让 AI Agent（Cline / Claude Code / Cursor）当你的学习教练，而非代码生成器。

## 快速开始

```bash
# 1. 克隆并安装依赖
git clone git@github.com:Blackarubbish/learning-agent.git
cd agent-study
uv sync

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 ZHIPU_API_KEY

# 3. 让 AI Agent 带你看学习进度
# 在 Cline / Claude Code / Cursor 中输入：
#   "我要学习 RAG 评估体系"
```

## 项目结构

```
agent-study/
├── AGENT.md              # 🔑 AI Agent 行为指令（所有 AI 助手的规则）
├── CONCEPT_MAP.md        # 🗺️ 概念地图（知识网络可视化）
├── STUDY_PROGRESS.md     # 📊 学习进度 + 能力自评
├── README.md             # 本文件
├── common/               # 🧰 共享基础设施（一行 import 搞定所有 boilerplate）
│   ├── __init__.py
│   ├── env.py            # 环境变量自动加载
│   ├── embeddings.py     # ZhipuEmbeddings 单例
│   ├── llm.py            # LLM 工厂（DeepSeek / Zhipu）
│   └── check.py          # 自检工具（section / check / summary）
└── learning/
    ├── stage1-rag-basics/      # 第一阶段：RAG 基础
    │   ├── 01-fastapi/
    │   ├── 02-langchain/
    │   ├── 03-rag-part1/
    │   ├── 04-rag-part2/
    │   └── 05-naive-rag/
    └── stage2-advanced-rag/    # 第二阶段：高级 RAG
        ├── 06-query-transformation/
        ├── 07-hybrid-retriever-rerank/
        ├── 08-rag-evaluation/
        ├── 09-milvus/
        ├── 10-advanced-data-processing/
        └── 11-weekly-summary/
```

## 学习流程

一位 AI Agent 全程引导，按照 `AGENT.md` 中的规则执行：

```
建立上下文 → 主动编码(starter.py) → 费曼笔记 → 自检验证 → 更新进度
```

### 每天的学习节奏

1. **打开项目**，AI Agent 自动读取 `STUDY_PROGRESS.md` 和 `CONCEPT_MAP.md`
2. **告诉 Agent 想学什么**（比如"学 08 评估"）
3. Agent **引导你写代码**，不是直接给答案
4. 运行 `python starter.py`，**自检断言**告诉你对不对
5. 用**自己的话**写费曼笔记
6. Agent **更新进度和能力自评**

## 跨平台使用

| 平台 | 方式 |
|------|------|
| **Cline** (VS Code) | 打开工作区即可，根目录 `AGENT.md` 自动生效 |
| **Claude Code** | `claude` 启动后在项目目录对话 |
| **Cursor** | 复制 `AGENT.md` 到 `.cursor/rules/` |
| **Copilot** | 在 `.github/copilot-instructions.md` 引用规则 |

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| LLM 编排 | LangChain |
| LLM | DeepSeek Chat / 智谱 GLM-4 |
| Embedding | 智谱 Embedding-3 |
| 向量存储 | FAISS / Milvus |
| 检索 | BM25 + 向量检索 + RRF + Rerank |
| 评估 | Ragas / DeepEval |

## 学习进度

👉 [STUDY_PROGRESS.md](./STUDY_PROGRESS.md)

- ✅ 第一阶段 (5/5) — RAG 基础完成
- 🔄 第二阶段 (2/6) — 高级 RAG 进行中