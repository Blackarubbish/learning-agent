"""双层记忆系统（来自 ch16）。

ShortTermMemory: 会话内滑动窗口缓冲区，存储原始对话消息。
LongTermMemory:  FAISS 向量存储，跨会话持久化关键信息（偏好、知识、决策）。
"""

import uuid

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from common import get_or_create_embeddings

embeddings = get_or_create_embeddings()


class ShortTermMemory:
    """短期记忆：会话内滑动窗口缓冲区。

    存储原始对话消息，超出 max_size 时截断最早的消息。
    使用全文存储而非向量检索——短期记忆追求精确，不需要语义近似。
    """

    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self.messages: list[dict] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_size:
            self.messages = self.messages[-self.max_size :]

    def get_recent(self, n: int = 10) -> list[dict]:
        return self.messages[-n:]

    def clear(self) -> None:
        self.messages.clear()


class LongTermMemory:
    """长期记忆：FAISS 向量存储，跨会话持久化关键信息。

    不存原始对话——只存 LLM 提取后的结构化事实。
    检索方式为语义搜索，因为跨会话的提问措辞可能不同。
    """

    def __init__(self):
        self.store: dict[str, Document] = {}
        self._vectorstore: FAISS | None = None

    def add(self, content: str, tags: list[str] | None = None) -> str:
        memory_id = str(uuid.uuid4())[:8]
        metadata = {"memory_id": memory_id, "tags": ",".join(tags or [])}
        doc = Document(page_content=content, metadata=metadata)
        self.store[memory_id] = doc
        self._vectorstore = None  # 下次检索时重建索引
        print(
            f"__LOG__ LongTermMemory 添加记忆: {content[:50]}..., tags: {tags}, memory_id: {memory_id}, store_size: {len(self.store)}"
        )
        return memory_id

    def _ensure_index(self) -> FAISS | None:
        if self._vectorstore is None and self.store:
            self._vectorstore = FAISS.from_documents(list(self.store.values()), embeddings)
        return self._vectorstore

    def retrieve(self, query: str, k: int = 3) -> list[Document]:
        index = self._ensure_index()
        if index is None:
            return []
        return index.similarity_search(query, k=k)

    def format_for_prompt(self, query: str, k: int = 3) -> str:
        """将检索到的长期记忆格式化为 prompt 片段。"""
        docs = self.retrieve(query, k)
        if not docs:
            return ""
        lines = [f"- {d.page_content}" for d in docs]
        return "长期记忆（用户偏好和历史）：\n" + "\n".join(lines)
