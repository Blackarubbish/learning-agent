"""知识库 — 示例文档 + FAISS 向量存储。

提供 search_knowledge 工具使用的检索后端。
"""

from common import get_or_create_embeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

embeddings = get_or_create_embeddings()

KNOWLEDGE_BASE = [
    Document(
        page_content="RAG（Retrieval-Augmented Generation）结合了信息检索和文本生成。核心流程：用户提问 → 检索相关文档 → 将文档作为上下文注入 LLM → 生成答案。RAG 有效减少了 LLM 幻觉。"
    ),
    Document(
        page_content="ReAct 是 Reasoning + Acting 的缩写。Agent 通过 Thought → Action → Observation 循环完成任务。与 RAG 的单向管道不同，Agent 能在观察结果后重新决策。"
    ),
    Document(
        page_content="Function Calling 让 LLM 原生支持工具调用。用 JSON Schema 定义工具参数，模型直接返回结构化 ToolCall，解析可靠性从 ~80% 提升到 ~99%。"
    ),
    Document(
        page_content="Agent Memory 分为短期记忆和长期记忆。短期记忆是会话内的滑动窗口缓冲，长期记忆用向量数据库跨会话持久化关键信息。"
    ),
    Document(
        page_content="错误处理是生产环境 Agent 的核心挑战。单步 95% 可靠性走 20 步后成功率只有 36%。错误三分类（可重试/参数错误/永久）让 Agent 能自主决定重试、修正还是放弃。"
    ),
    Document(
        page_content="Embedding 模型将文本映射为向量。常见模型包括 OpenAI text-embedding-3、智谱 embedding-3、BGE 系列。选型考虑维度、最大长度、多语言支持、成本。"
    ),
    Document(
        page_content="FAISS 是 Meta 开源的向量相似度搜索库，适合小规模原型验证。Milvus 是云原生向量数据库，支持增删改查、属性过滤、分布式部署，适合生产环境。"
    ),
    Document(
        page_content="工具工程决定 Agent 的上限。同样的 LLM + 不同的工具 = 完全不同的 Agent。好的工具输出要信息抽象（截断+摘要+引导），而非原始数据倾泻。"
    ),
    Document(
        page_content="LangChain 是一个 LLM 应用开发框架，提供了 Chains、Agents、Tools 等抽象。但它的 AgentExecutor 对生产环境不够灵活，复杂场景建议用 LangGraph。"
    ),
    Document(
        page_content="Prompt Engineering 是优化 LLM 输出的关键技术。包括 few-shot、chain-of-thought、role prompting 等策略。简单的 prompt 优化往往比复杂的 Agent 架构更有效。"
    ),
]

# 模块级单例，tools.py 和 agent.py 直接 import 使用
vectorstore = FAISS.from_documents(KNOWLEDGE_BASE, embeddings)
