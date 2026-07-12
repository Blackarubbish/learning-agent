"""
第 27 章 — AutoGen 风格的多 Agent 对话协作

目标：手动实现一个极简 GroupChat，理解：
- RoundRobin 固定轮询
- LLM 动态选择发言人
- 可组合的终止条件
- AgentTool 的递归组合思想（本文件只实现前者，思想在 README 中）
"""

import json

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


class Agent:
    """模拟 AutoGen 的 AssistantAgent：每个 Agent 有名字和 system prompt。"""

    def __init__(self, name: str, system_prompt: str) -> None:
        self.name = name
        self.system_prompt = system_prompt

    def run(self, task: str, history: list[dict]) -> str:
        """
        根据 system_prompt + 共享 history + 当前任务生成回复。

        Args:
            task: 本轮需要处理的内容
            history: GroupChat 的共享历史，格式 [{"role": "user"|"assistant", "name": str, "content": str}]
        """
        messages = [{"role": "system", "content": self.system_prompt}]

        # 把内部 history 转成 LLM 可接受的格式（role + content），保留发言人名字便于理解上下文
        for msg in history:
            content = msg["content"]
            if msg["role"] == "assistant" and "name" in msg:
                content = f"[{msg['name']}] {content}"
            messages.append({"role": msg["role"], "content": content})

        messages.append({"role": "user", "content": f"现在轮到你了。请基于上文回复：{task}"})

        response = llm.invoke(messages)
        return response.content


class TerminationCondition:
    """终止条件基类。"""

    def check(self, messages: list[dict]) -> bool:
        raise NotImplementedError

    def __or__(self, other: "TerminationCondition") -> "TerminationCondition":
        """支持 termination_a | termination_b 组合。"""
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
        # TODO 1: 实现消息数量判断
        return len(messages) >= self.max_messages


class TextMentionTermination(TerminationCondition):
    """当某条消息包含指定文本时终止。"""

    def __init__(self, text: str) -> None:
        self.text = text

    def check(self, messages: list[dict]) -> bool:
        # TODO 2: 实现文本匹配判断
        for msg in messages:
            msg_content = msg["content"]
            if self.text in msg_content:
                return True
        return False


class SpeakerSelector:
    """发言人选择器基类。"""

    def select(self, participants: list[Agent], history: list[dict]) -> Agent:
        raise NotImplementedError


class RoundRobinSelector(SpeakerSelector):
    """固定轮询：按 participants 顺序循环选择。"""

    def __init__(self) -> None:
        self._index = 0

    def select(self, participants: list[Agent], history: list[dict]) -> Agent:
        next_agent = participants[self._index]
        print(f"🔁 RoundRobin 选择: {next_agent.name} (index={self._index})")
        if self._index >= len(participants) - 1:
            self._index = 0
        else:
            self._index = self._index + 1
        return next_agent


class LLMSelector(SpeakerSelector):
    """由 LLM 根据 history 和角色描述选择下一个发言人。"""

    def __init__(self, llm_client) -> None:
        self.llm = llm_client

    def select(self, participants: list[Agent], history: list[dict]) -> Agent:
        """
        TODO 4: 让 LLM 从 participants 中选出最合适的下一个发言人。

        提示：
        1. 构造一个 selector_prompt，包含所有候选人的 name 和 system_prompt 摘要
        2. 附加当前的对话 history
        3. 明确要求 LLM 只返回一个名字（如 "researcher"），不要解释
        4. 从 participants 中找到名字匹配的 Agent 返回
        """
        history_str = "\n".join(json.dumps(h, ensure_ascii=False) for h in history)
        roles_desc = "\n".join(f"- {p.name}: {p.system_prompt}" for p in participants)
        prompt = f"""你是 GroupChat 的协调员，负责根据对话上下文选择下一个最合适的 Agent 发言。

可选角色：
{roles_desc}

选择规则（按优先级）：
1. 如果对话历史为空或只有用户任务，必须选择 researcher 先发言
2. 只有 researcher 提供了事实后，analyst 才能发言
3. 只有 analyst 提供了洞察后，writer 才能发言
4. 如果当前讨论需要补充事实，可以再次选择 researcher

当前对话历史：
{history_str if history_str else "（对话刚开始，请选择 researcher）"}

只返回一个名字，必须是以下之一：{", ".join(p.name for p in participants)}。不要解释、不要标点。"""
        response = llm.invoke([{"role": "user", "content": prompt}])
        # 提取文本（兼容不同模型类型）
        chosen_name = (
            response.content.strip() if hasattr(response, "content") else str(response).strip()
        )
        chosen_name = chosen_name.strip().strip('"').strip("'").lower()
        print(
            f"🧠 LLM 原始选择: '{getattr(response, 'content', str(response))}' → 解析后: '{chosen_name}'"
        )

        for agent in participants:
            if agent.name.lower() == chosen_name:
                print(f"✅ 匹配到 Agent: {agent.name}")
                return agent
        print(f"⚠️ 未匹配到 '{chosen_name}'，兜底返回第一个 Agent")
        return participants[0]


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
        """把 Agent 的回复加入共享 history。"""
        return {"role": "assistant", "name": agent_name, "content": content}

    def run(self, task: str) -> list[dict]:
        """
        TODO 5: 实现 GroupChat 主循环。

        流程：
        1. 把 task 作为第一条 user 消息加入 history
        2. 循环最多 max_turns 轮：
           a. 用 selector 选出下一个发言人
           b. 调用 agent.run(task, history) 获取回复
           c. 把回复加入 history
           d. 检查 termination_condition，若满足则 break
        3. 返回完整 history
        """
        self.history.append({"role": "user", "content": task})
        print(f"\n🚀 GroupChat 开始，任务: {task}")
        for turn in range(self.max_turns):
            print(f"\n--- 第 {turn + 1} 轮 ---")
            current_agent = self.selector.select(
                participants=self.participants, history=self.history
            )
            response = current_agent.run(task=task, history=self.history)
            print(f"💬 {current_agent.name} 说: {response[:100]}...")
            response_format = self._format_history_message(current_agent.name, response)
            self.history.append(response_format)
            is_end = self.termination_condition.check(self.history)
            print(f"⛔ 终止条件满足? {is_end} (当前 {len(self.history)} 条消息)")
            if is_end:
                print("🏁 GroupChat 终止")
                return self.history
        print("🏁 达到最大轮数")
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

    # TODO 6: 创建 RoundRobinSelector + MaxMessageTermination(5)
    # 创建 GroupChat，运行一个简单任务，验证三个 Agent 按顺序各发言一次
    # chat = GroupChat(...)
    # history = chat.run("请介绍 RAG 的基本概念")
    participants = [researcher, analyst, writer]
    chat = GroupChat(
        participants=participants,
        selector=RoundRobinSelector(),
        termination_condition=MaxMessageTermination(5),
    )
    history = chat.run("请介绍 RAG 的基本概念")

    check("RoundRobin 产生了 5 条消息", len(history) == 5)
    check(
        "三个 Agent 都参与了", len(set(m["name"] for m in history if m["role"] == "assistant")) == 3
    )
    section("测试 LLM 动态选人")

    # TODO 7: 创建 LLMSelector + TextMentionTermination("TERMINATE")
    # 再次、运行 GroupChat，验证 writer 说完 TERMINATE 后对话终止
    selector_llm = LLMSelector(llm)
    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(8)
    chat2 = GroupChat([researcher, analyst, writer], selector_llm, termination, max_turns=8)
    history2 = chat2.run("请介绍 RAG 的基本概念")

    check("LLM 选择让 researcher 先发言", history2[1]["name"] == "researcher")
    check("对话以 TERMINATE 结束", any("TERMINATE" in m["content"] for m in history2))

    summary()
