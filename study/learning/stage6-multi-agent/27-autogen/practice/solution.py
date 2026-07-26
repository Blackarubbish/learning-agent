"""
第 27 章 — AutoGen 风格的多 Agent 对话协作（参考实现）

说明：本实现不依赖 autogen-agentchat，而是用手写 Python 复现其核心概念，
以便复用项目已有的 DeepSeek/Zhipu LLM，同时聚焦原理而非框架 API。
"""

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


class Agent:
    """模拟 AutoGen 的 AssistantAgent：每个 Agent 有名字和 system prompt。"""

    def __init__(self, name: str, system_prompt: str) -> None:
        self.name = name
        self.system_prompt = system_prompt

    def run(self, task: str, history: list[dict]) -> str:
        """根据 system_prompt + 共享 history + 当前任务生成回复。"""
        messages = [{"role": "system", "content": self.system_prompt}]

        # 把内部 history 转成 LLM 可接受的格式，保留发言人名字便于理解上下文
        for msg in history:
            content = msg["content"]
            if msg["role"] == "assistant" and "name" in msg:
                content = f"[{msg['name']}] {content}"
            messages.append({"role": msg["role"], "content": content})

        messages.append({"role": "user", "content": f"现在轮到你了。请基于上文回复：{task}"})

        response = llm.invoke(messages)
        return response.content


class TerminationCondition:
    """终止条件基类，支持 | 组合。"""

    def check(self, messages: list[dict]) -> bool:
        raise NotImplementedError

    def __or__(self, other: "TerminationCondition") -> "TerminationCondition":
        return CombinedTermination(self, other)


class CombinedTermination(TerminationCondition):
    def __init__(self, a: TerminationCondition, b: TerminationCondition) -> None:
        self.a = a
        self.b = b

    def check(self, messages: list[dict]) -> bool:
        return self.a.check(messages) or self.b.check(messages)


class MaxMessageTermination(TerminationCondition):
    """当消息总数达到 max_messages 时终止。"""

    def __init__(self, max_messages: int) -> None:
        self.max_messages = max_messages

    def check(self, messages: list[dict]) -> bool:
        return len(messages) >= self.max_messages


class TextMentionTermination(TerminationCondition):
    """当某条消息包含指定文本时终止。"""

    def __init__(self, text: str) -> None:
        self.text = text

    def check(self, messages: list[dict]) -> bool:
        return any(self.text in str(m.get("content", "")) for m in messages)


class SpeakerSelector:
    """发言人选择器基类。"""

    def select(self, participants: list[Agent], history: list[dict]) -> Agent:
        raise NotImplementedError


class RoundRobinSelector(SpeakerSelector):
    """固定轮询：按 participants 顺序循环选择。"""

    def __init__(self) -> None:
        self._index = 0

    def select(self, participants: list[Agent], history: list[dict]) -> Agent:
        agent = participants[self._index % len(participants)]
        self._index += 1
        return agent


class LLMSelector(SpeakerSelector):
    """由 LLM 根据 history 和角色描述选择下一个发言人。"""

    def __init__(self, llm_client) -> None:
        self.llm = llm_client

    def select(self, participants: list[Agent], history: list[dict]) -> Agent:
        names = [p.name for p in participants]
        roles_desc = "\n".join(f"- {p.name}: {p.system_prompt}" for p in participants)

        prompt = f"""你是 GroupChat 的协调员。请根据对话上下文，从以下角色中选择最合适下一个发言的人。

可选角色：
{roles_desc}

要求：
1. 只返回一个名字，必须是以下之一：{", ".join(names)}
2. 不要解释、不要标点、不要多余内容
3. 如果是第一轮且没有历史，优先让研究员（researcher）先发言

当前对话历史：
{self._format_history(history)}

下一个发言人："""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        chosen_name = self._parse_name(response.content, names)

        # 兜底：如果解析失败，按 RoundRobin 返回第一个
        if chosen_name is None:
            return participants[0]
        return next(p for p in participants if p.name == chosen_name)

    def _format_history(self, history: list[dict]) -> str:
        if not history:
            return "（无）"
        lines = []
        for msg in history:
            if msg["role"] == "user":
                lines.append(f"用户: {msg['content']}")
            else:
                lines.append(f"{msg.get('name', '助手')}: {msg['content']}")
        return "\n".join(lines)

    def _parse_name(self, text: str, names: list[str]) -> str | None:
        text = text.strip().lower()
        # 先尝试精确匹配
        for name in names:
            if text == name.lower():
                return name
        # 再尝试包含匹配
        for name in names:
            if name.lower() in text:
                return name
        return None


class GroupChat:
    """模拟 AutoGen 的 GroupChat：容器 + 协调器。"""

    def __init__(
        self,
        participants: list[Agent],
        selector: SpeakerSelector,
        termination_condition: TerminationCondition,
        max_turns: int = 10,
    ) -> None:
        self.participants = participants
        self.selector = selector
        self.termination_condition = termination_condition
        self.max_turns = max_turns
        self.history: list[dict] = []

    def _format_history_message(self, agent_name: str, content: str) -> dict:
        return {"role": "assistant", "name": agent_name, "content": content}

    def run(self, task: str) -> list[dict]:
        self.history = [{"role": "user", "content": task}]

        for _ in range(self.max_turns):
            if self.termination_condition.check(self.history):
                break

            agent = self.selector.select(self.participants, self.history)
            content = agent.run(task, self.history)
            self.history.append(self._format_history_message(agent.name, content))

        return self.history


if __name__ == "__main__":
    reset()

    section("定义角色")

    researcher = Agent(
        name="researcher",
        system_prompt="你是研究员。你的任务是搜索和总结背景信息。只输出事实，不输出观点。",
    )
    analyst = Agent(
        name="analyst",
        system_prompt="你是分析师。你基于研究员提供的事实进行分析，提炼关键洞察。",
    )
    writer = Agent(
        name="writer",
        system_prompt="你是写手。你基于分析师的洞察撰写一段简洁的总结。当总结完成时，在末尾加上 'TERMINATE'。",
    )

    section("测试 RoundRobin 轮询")

    rr_selector = RoundRobinSelector()
    rr_termination = MaxMessageTermination(5)
    chat = GroupChat(
        participants=[researcher, analyst, writer],
        selector=rr_selector,
        termination_condition=rr_termination,
        max_turns=5,
    )
    history = chat.run("请介绍 RAG 的基本概念")

    check("RoundRobin 产生了 5 条消息", len(history) == 5)
    check("三个 Agent 都参与了", len({m["name"] for m in history if m["role"] == "assistant"}) == 3)

    section("测试 LLM 动态选人")

    selector_llm = LLMSelector(llm)
    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(8)
    chat2 = GroupChat(
        participants=[researcher, analyst, writer],
        selector=selector_llm,
        termination_condition=termination,
        max_turns=8,
    )
    history2 = chat2.run("请介绍 RAG 的基本概念")

    check("LLM 选择让 researcher 先发言", history2[1]["name"] == "researcher")
    check("对话以 TERMINATE 结束", any("TERMINATE" in m["content"] for m in history2))

    summary()
