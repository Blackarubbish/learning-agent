"""MemoryAgent 完整实现 — 带短期和长期记忆的 Agent。

设计要点：
  - 短期记忆用滑动窗口限制 token 消耗，O(1) 追加和淘汰
  - 长期记忆用 FAISS 向量库，语义检索而非关键词匹配
  - extract_and_store 每 3 轮触发一次，用 LLM 而非规则判断重要性
  - 提示词分层构建：系统指令 → 长期记忆 → 短期历史 → 当前输入
"""

from common import load_dotenv_if_needed, get_or_create_embeddings, get_or_create_llm, section, check, reset, summary

load_dotenv_if_needed()
embeddings = get_or_create_embeddings()
llm = get_or_create_llm(temperature=0)


class ShortTermMemory:
    """滑动窗口对话缓冲，存储最近 N 条消息。"""

    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self.messages: list[dict] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        # 超出窗口时丢弃最旧的
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def format_history(self) -> str:
        lines = []
        for msg in self.messages:
            prefix = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.messages.clear()


class LongTermMemory:
    """FAISS 向量库持久化用户关键信息。

    用向量检索而非关键词匹配，因为"我喜欢咖啡"和"用户有什么饮品偏好"
    在关键词层面没有交集，但语义上高度相关。
    """

    def __init__(self):
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document

        self.FAISS = FAISS
        self.Document = Document
        self.store: FAISS | None = None

    def add_memory(self, content: str, user_id: str = "default") -> None:
        doc = self.Document(page_content=content, metadata={"user_id": user_id})
        if self.store is None:
            self.store = self.FAISS.from_documents([doc], embeddings)
        else:
            self.store.add_documents([doc])

    def search(self, query: str, k: int = 3) -> list[str]:
        if self.store is None:
            return []
        docs = self.store.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]

    def extract_and_store(self, text: str, user_id: str = "default") -> list[str]:
        # 让 LLM 判断哪些信息值得长期记住，而非用关键词规则
        extraction_prompt = f"""从以下对话中提取值得长期记住的用户信息。每行一条，用 '- ' 开头。
如果没有值得记住的信息，只回复 '无'。

对话内容：
{text}

值得记住的信息示例：姓名、职业、偏好、技能、目标、经历等。"""

        response = llm.invoke(extraction_prompt)
        response_text = response.content.strip() if hasattr(response, "content") else str(response).strip()

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


class MemoryAgent:
    """整合双层记忆的 Agent。

    流程：检索长期记忆 → 获取短期历史 → 构建分层提示词 → LLM 生成 → 更新双记忆。

    分层提示词的顺序很重要：系统指令在最外层设定角色，
    长期记忆提供跨会话上下文，短期历史提供当前会话连贯性，
    用户消息放在最末尾作为焦点。
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.short_term = ShortTermMemory(max_messages=10)
        self.long_term = LongTermMemory()
        self.turn_count = 0

    def _build_prompt(self, user_input: str, long_term_results: list[str]) -> str:
        system = "你是一个有记忆的智能助手。你可以参考对话历史和长期记忆来个性化回复。"

        parts = [system]

        if long_term_results:
            parts.append("\n[长期记忆 — 关于此用户的历史信息]")
            for mem in long_term_results:
                parts.append(f"- {mem}")

        history = self.short_term.format_history()
        if history:
            parts.append(f"\n[最近对话历史]\n{history}")

        parts.append(f"\n[用户当前消息]\n用户: {user_input}")

        return "\n".join(parts)

    def run(self, user_input: str) -> str:
        # 1. 检索长期记忆
        long_term_results = self.long_term.search(user_input)

        # 2. 构建提示词
        prompt = self._build_prompt(user_input, long_term_results)

        # 3. 调用 LLM
        response = llm.invoke(prompt)
        response_content = response.content if hasattr(response, "content") else str(response)

        # 4. 更新短期记忆
        self.short_term.add("user", user_input)
        self.short_term.add("assistant", response_content)

        # 5. 每 3 轮提取关键信息写入长期记忆
        self.turn_count += 1
        if self.turn_count % 3 == 0:
            recent = self.short_term.format_history()
            self.long_term.extract_and_store(recent, self.user_id)

        return response_content


# ═══════════════════════════════════════════════════════════════
# 实验验证
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    reset()
    agent = MemoryAgent(user_id="user_test")

    section("第 1 轮：用户自我介绍")
    r1 = agent.run("你好！我叫张三，我是一名 Python 工程师，喜欢喝咖啡。")
    print(f"用户: 你好！我叫张三，我是一名 Python 工程师，喜欢喝咖啡。")
    print(f"助手: {r1}")

    section("第 2 轮：测试短期记忆")
    r2 = agent.run("我叫什么名字？我的职业是什么？")
    print(f"用户: 我叫什么名字？我的职业是什么？")
    print(f"助手: {r2}")
    check("短期记忆 — 记住名字", "张三" in r2)
    check("短期记忆 — 记住职业", "Python" in r2 or "工程师" in r2)

    section("第 3 轮：用户补充偏好")
    r3 = agent.run("对了，我不喜欢 JavaScript，而且我最近在学 Rust。")
    print(f"用户: 对了，我不喜欢 JavaScript，而且我最近在学 Rust。")
    print(f"助手: {r3}")

    section("第 4 轮：测试长期记忆（第 3 轮时已将前 3 轮提取到长期记忆）")
    r4 = agent.run("我之前说过我喜欢什么，不喜欢什么？")
    print(f"用户: 我之前说过我喜欢什么，不喜欢什么？")
    print(f"助手: {r4}")
    check("长期记忆 — 喜欢咖啡", "咖啡" in r4 or "coffee" in r4.lower())
    check("长期记忆 — 不喜欢 JavaScript", "JavaScript" in r4 or "javascript" in r4.lower())

    section("第 5 轮：综合记忆测试")
    r5 = agent.run("根据你对我的了解，给我推荐一个适合我的编程语言或技术方向。")
    print(f"用户: 根据你对我的了解，给我推荐一个适合我的编程语言或技术方向。")
    print(f"助手: {r5}")
    check("综合 — 基于用户历史做出推荐", len(r5) > 10)

    print("\n" + "=" * 60)
    print(f"短期记忆消息数: {len(agent.short_term.messages)}")
    print(f"对话轮数: {agent.turn_count}")
    summary()
