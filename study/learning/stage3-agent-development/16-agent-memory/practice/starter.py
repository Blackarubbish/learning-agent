"""MemoryAgent — 带短期和长期记忆的 Agent。

TODO 清单：
  1. ShortTermMemory.format_history() — 将消息列表格式化为 LLM 可读的字符串
  2. LongTermMemory.add_memory() — 将文本写入 FAISS 向量库
  3. LongTermMemory.search() — 从向量库检索相关记忆
  4. LongTermMemory.extract_and_store() — 用 LLM 从对话中提取关键事实并存入长期记忆
  5. MemoryAgent.run() — 整合记忆 → 构建提示词 → 调用 LLM → 更新记忆
"""

from common import (
    check,
    get_or_create_embeddings,
    get_or_create_llm,
    load_dotenv_if_needed,
    reset,
    section,
    summary,
)

load_dotenv_if_needed()
embeddings = get_or_create_embeddings()
llm = get_or_create_llm(temperature=0)


# ═══════════════════════════════════════════════════════════════
# TODO 1: ShortTermMemory — 滑动窗口对话缓冲
# ═══════════════════════════════════════════════════════════════


class ShortTermMemory:
    """短期记忆：用滑动窗口保存最近 N 轮对话。

    内部用 list[dict] 存储消息，每条消息格式为 {"role": "user"|"assistant", "content": str}。
    """

    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self.messages: list[dict] = []

    def add(self, role: str, content: str) -> None:
        """添加一条消息，超出窗口时自动丢弃最旧的。"""
        # TODO 1a: 将消息追加到 self.messages，如果超过 max_messages 则弹出最旧的消息
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def format_history(self) -> str:
        """将对话历史格式化为一个字符串，供 LLM 提示词使用。

        格式示例：
          用户: 你好
          助手: 你好！有什么可以帮你的？
          用户: 我叫张三
          助手: 好的，我记住了

        提示：遍历 self.messages，role=="user" 用"用户:"前缀，role=="assistant" 用"助手:"前缀。
        """
        # TODO 1b: 按要求格式化为字符串并返回
        formatted = []
        for msg in self.messages:
            prefix = "用户:" if msg["role"] == "user" else "助手:"
            formatted.append(f"{prefix} {msg['content']}")
        return "\n".join(formatted)

    def clear(self) -> None:
        self.messages.clear()


# ═══════════════════════════════════════════════════════════════
# TODO 2: LongTermMemory — FAISS 向量存储
# ═══════════════════════════════════════════════════════════════


class LongTermMemory:
    """长期记忆：用 FAISS 向量库持久化用户的关键信息。

    每条记忆存储为纯文本，附带 metadata（如 user_id、timestamp）。
    """

    def __init__(self):
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document

        self.FAISS = FAISS
        self.Document = Document
        self.store: FAISS | None = None

    def add_memory(self, content: str, user_id: str = "default") -> None:
        """将一条记忆写入向量库。

        提示：
        1. 创建一个 Document（page_content=content, metadata={"user_id": user_id}）
        2. 如果 self.store 为 None，用 FAISS.from_documents([doc], embeddings) 初始化
        3. 否则用 self.store.add_documents([doc]) 追加
        """
        # TODO 2a: 创建 Document 并写入 FAISS 向量库
        mem_doc = self.Document(page_content=content, metadata={"user_id": user_id})
        if self.store is None:
            self.store = self.FAISS.from_documents([mem_doc], embeddings)
        else:
            self.store.add_documents([mem_doc])

    def search(self, query: str, k: int = 3) -> list[str]:
        """从长期记忆中检索与 query 最相关的记忆。

        提示：用 self.store.similarity_search(query, k=k) 检索，
        返回每个 doc 的 page_content 列表。如果 store 为空则返回空列表。
        """
        # TODO 2b: 检索并返回 page_content 列表
        if self.store is None:
            return []
        results = self.store.similarity_search(query, k=k)
        return [doc.page_content for doc in results]

    def extract_and_store(self, text: str, user_id: str = "default") -> list[str]:
        """用 LLM 从对话文本中提取关键用户信息，存入长期记忆。

        提示：
        1. 构造提示词，让 LLM 从 text 中提取值得记住的用户信息（姓名、偏好、职业等）
        2. 每行一条事实，格式为 "- 事实内容"
        3. 解析 LLM 回复，将每条事实调用 self.add_memory() 存入
        4. 返回提取的事实列表

        提示词参考：
          "从以下对话中提取值得长期记住的用户信息。每行一条，用 '- ' 开头。如果没有值得记住的信息，回复 '无'。
          对话内容：{text}"
        """
        extraction_prompt = f"""从以下对话中提取值得长期记住的用户信息。每行一条，用 '- ' 开头。
如果没有值得记住的信息，只回复 '无'。

对话内容：
{text}

值得记住的信息示例：姓名、职业、偏好、技能、目标、经历等。"""
        # TODO 2c: 用 LLM 提取关键信息并存入长期记忆
        response = llm.invoke(extraction_prompt)
        response_text = (
            response.content.strip() if hasattr(response, "content") else str(response).strip()
        )
        if response_text == "无":
            return []
        facts = []
        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                fact = line[2:].strip()
                if fact and fact != "无":
                    self.add_memory(fact, user_id)
                    facts.append(fact)
        return facts


# ═══════════════════════════════════════════════════════════════
# TODO 3: MemoryAgent — 整合记忆系统
# ═══════════════════════════════════════════════════════════════


class MemoryAgent:
    """整合短期+长期记忆的 Agent。

    每轮对话流程：
    1. 从长期记忆检索与用户输入相关的历史信息
    2. 获取短期记忆中的最近对话历史
    3. 构建包含系统提示+长期记忆+短期历史+当前输入的提示词
    4. 调用 LLM 生成响应
    5. 更新短期记忆（用户消息+助手回复）
    6. 定期提取关键信息存入长期记忆
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.short_term = ShortTermMemory(max_messages=10)
        self.long_term = LongTermMemory()
        self.turn_count = 0

    def _build_prompt(self, user_input: str, long_term_results: list[str]) -> str:
        """构建发送给 LLM 的完整提示词。"""
        system = "你是一个有记忆的智能助手。你可以参考对话历史和长期记忆来个性化回复。"

        prompt_parts = [system]

        # 添加长期记忆
        if long_term_results:
            prompt_parts.append("\n[长期记忆 — 关于此用户的历史信息]")
            for mem in long_term_results:
                prompt_parts.append(f"- {mem}")

        # 添加短期对话历史
        history = self.short_term.format_history()
        if history:
            prompt_parts.append(f"\n[最近对话历史]\n{history}")

        # 当前输入
        prompt_parts.append(f"\n[用户当前消息]\n用户: {user_input}")

        return "\n".join(prompt_parts)

    def run(self, user_input: str) -> str:
        """处理一轮用户输入，返回 Agent 响应。"""
        # TODO 3a: 从长期记忆检索与 user_input 相关的信息
        long_term_results = self.long_term.search(
            user_input
        )  # 替换为 self.long_term.search(user_input)

        # TODO 3b: 构建提示词并调用 LLM
        prompt = self._build_prompt(user_input, long_term_results)
        # response = ...  # 调用 llm.invoke(prompt)
        response = llm.invoke(prompt)
        response_content = response.content if hasattr(response, "content") else str(response)
        # TODO 3c: 更新短期记忆（添加用户消息和助手回复）
        self.short_term.add("user", user_input)
        self.short_term.add("assistant", response_content)

        # TODO 3d: 每 3 轮提取一次关键信息存入长期记忆
        self.turn_count += 1
        if self.turn_count % 3 == 0:
            recent = self.short_term.format_history()
            self.long_term.extract_and_store(recent, self.user_id)

        return response_content  # 替换为 response_content


# ═══════════════════════════════════════════════════════════════
# 实验：验证记忆能力
# ═══════════════════════════════════════════════════════════════


def test_short_term():
    """测试短期记忆：同一会话中跨轮次记住用户信息。

    不依赖长期记忆，只验证 ShortTermMemory + MemoryAgent.run() 的基本整合。
    """
    reset()
    agent = MemoryAgent(user_id="test_st")

    section("第 1 轮：用户自我介绍")
    r1 = agent.run("你好！我叫张三，我是一名 Python 工程师，喜欢喝咖啡。")
    print("用户: 你好！我叫张三，我是一名 Python 工程师，喜欢喝咖啡。")
    print(f"助手: {r1}")

    section("第 2 轮：测试短期记忆")
    r2 = agent.run("我叫什么名字？我的职业是什么？")
    print("用户: 我叫什么名字？我的职业是什么？")
    print(f"助手: {r2}")
    check("短期记忆 — 记住名字", "张三" in r2)
    check("短期记忆 — 记住职业", "Python" in r2 or "工程师" in r2)

    summary()


def test_long_term():
    """测试长期记忆：extract_and_store 自动提取关键信息并在后续轮次中使用。

    依赖 extract_and_store 在第 3 轮触发，第 4 轮验证长期记忆检索。
    """
    reset()
    agent = MemoryAgent(user_id="test_lt")

    # 前 2 轮建立对话历史
    section("第 1 轮：用户自我介绍")
    r1 = agent.run("你好！我叫张三，我是一名 Python 工程师，喜欢喝咖啡。")
    print("用户: 你好！我叫张三，我是一名 Python 工程师，喜欢喝咖啡。")
    print(f"助手: {r1}")

    section("第 2 轮：确认短期记忆")
    r2 = agent.run("我叫什么名字？")
    print("用户: 我叫什么名字？")
    print(f"助手: {r2}")

    # 第 3 轮触发 extract_and_store（turn_count % 3 == 0）
    section("第 3 轮：补充偏好（触发长期记忆提取）")
    r3 = agent.run("对了，我不喜欢 JavaScript，而且我最近在学 Rust。")
    print("用户: 对了，我不喜欢 JavaScript，而且我最近在学 Rust。")
    print(f"助手: {r3}")

    # 第 4 轮验证长期记忆
    section("第 4 轮：测试长期记忆")
    r4 = agent.run("我之前说过我喜欢什么，不喜欢什么？")
    print("用户: 我之前说过我喜欢什么，不喜欢什么？")
    print(f"助手: {r4}")
    check("长期记忆 — 喜欢咖啡", "咖啡" in r4 or "coffee" in r4.lower())
    check("长期记忆 — 不喜欢 JavaScript", "JavaScript" in r4 or "javascript" in r4.lower())

    summary()


def test_comprehensive():
    """测试综合记忆：跨多轮对话后基于用户历史做个性化推荐。"""
    reset()
    agent = MemoryAgent(user_id="test_comp")

    section("第 1 轮：用户自我介绍")
    r1 = agent.run("你好！我叫张三，我是一名 Python 工程师，喜欢喝咖啡。")
    print("用户: 你好！我叫张三，我是一名 Python 工程师，喜欢喝咖啡。")
    print(f"助手: {r1}")

    section("第 2 轮")
    r2 = agent.run("我叫什么名字？我的职业是什么？")
    print("用户: 我叫什么名字？我的职业是什么？")
    print(f"助手: {r2}")

    section("第 3 轮：补充偏好（触发长期记忆提取）")
    r3 = agent.run("对了，我不喜欢 JavaScript，而且我最近在学 Rust。")
    print("用户: 对了，我不喜欢 JavaScript，而且我最近在学 Rust。")
    print(f"助手: {r3}")

    section("第 4 轮")
    r4 = agent.run("我之前说过我喜欢什么，不喜欢什么？")
    print("用户: 我之前说过我喜欢什么，不喜欢什么？")
    print(f"助手: {r4}")

    section("第 5 轮：综合记忆测试")
    r5 = agent.run("根据你对我的了解，给我推荐一个适合我的编程语言或技术方向。")
    print("用户: 根据你对我的了解，给我推荐一个适合我的编程语言或技术方向。")
    print(f"助手: {r5}")
    check("综合 — 基于用户历史做出推荐", len(r5) > 10)

    summary()


if __name__ == "__main__":
    test_short_term()
    test_long_term()
    test_comprehensive()
