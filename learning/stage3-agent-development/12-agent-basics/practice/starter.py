"""
Agent 核心概念：从零理解 ReAct 框架

目标：构建一个能使用工具的 Agent，理解 "思考 → 行动 → 观察" 循环。

核心认知（开始前读）：
  - Agent ≠ 管道：Agent 是 循环 而非 单向流程，关键区别在于"观察结果后重新决策"
  - 不是所有场景都需要 Agent：固定流程用普通代码更可靠（Anthropic 原则）
  - 错误会累积：每一步可靠性 95%，20 步后只有 36%

运行：
  make run f=learning/stage3-agent-development/12-agent-basics/practice/starter.py
"""

from common import load_dotenv_if_needed, get_or_create_llm, section, check, summary, reset

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

import json
import math
import re
from typing import Callable

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# ============================================================
# TODO 1: 定义工具
# ============================================================
# 工具是一个函数 + 一段描述（告诉 LLM 这个工具做什么、参数是什么）
# LLM 通过描述来决定是否调用这个工具

# 工具定义格式：
# {
#     "name": "calculator",
#     "description": "计算数学表达式，支持 + - * / ** sqrt() sin() cos() 等",
#     "parameters": {"expression": "数学表达式字符串，如 '2 + 3 * 4'"},
# }

# TODO 1.1: 实现计算器工具函数
def calculator_tool(expression: str) -> str:
    """安全地执行数学表达式计算"""
    pass

# TODO 1.2: 实现字符串工具函数
def string_tool(text: str, operation: str) -> str:
    """字符串操作：reverse / uppercase / length / word_count"""
    pass

# TODO 1.3: 把工具注册为 tool registry
# 格式: {"name": ..., "function": callable, "schema": {"description": ..., "parameters": {...}}}
TOOLS = {}  # TODO: 填入上面两个工具


# ============================================================
# TODO 2: ReAct Prompt 模板
# ============================================================
# ReAct 的核心是让 LLM 按特定格式输出：
#   Thought: 我需要做一个计算
#   Action: calculator
#   Action Input: {"expression": "2 + 3"}
# 或者：
#   Thought: 我已经有答案了
#   Final Answer: 结果是 5

REACT_PROMPT = """
TODO: 编写 ReAct 提示词模板

要求：
1. 告诉 LLM 它有哪些工具可用（从 TOOLS 中读取）
2. 要求 LLM 按 Thought/Action/Action Input 格式输出（需要调用工具时）
3. 要求 LLM 按 Thought/Final Answer 格式输出（有最终答案时）
4. 每次只输出一个 Action 或一个 Final Answer
""".strip()


# ============================================================
# TODO 3: 解析 LLM 输出
# ============================================================
def parse_react_output(text: str) -> dict:
    """
    解析 LLM 的 ReAct 格式输出

    返回格式:
        {"type": "action", "tool": "calculator", "input": {"expression": "2+3"}}
        {"type": "final_answer", "answer": "结果是 5"}
        {"type": "parse_error", "raw": text}
    """
    pass


# ============================================================
# TODO 4: Agent 执行循环
# ============================================================
class SimpleAgent:
    """
    简单的 ReAct Agent

    流程：
    1. 将用户问题 + 工具描述填入 prompt → 调用 LLM
    2. 解析 LLM 输出
    3. 如果是 Action: 执行工具 → 将结果拼回 context → 返回步骤 1
    4. 如果是 Final Answer: 结束循环，返回答案
    5. 如果是 parse_error: 将错误信息反馈给 LLM → 让它自我修正（这就是 Reflection 的雏形）

    关键设计：工具返回的结果会作为 Observation 拼回下轮 prompt。
    这意味着 Agent 能看到自己的行动结果，并据此重新推理。
    如果工具执行失败，把错误信息作为 Observation 返回——Agent 会尝试修正（反思）。
    """

    def __init__(self, llm, tools: dict):
        self.llm = llm
        self.tools = tools

    def run(self, user_question: str, max_steps: int = 5) -> dict:
        """
        运行 Agent 循环

        返回: {"answer": ..., "steps": [{"thought": ..., "action": ..., "result": ...}, ...]}
        """
        # TODO: 实现 ReAct 循环
        # 1. 构建初始 prompt
        # 2. 调用 LLM
        # 3. 解析输出
        # 4. 如果是 action → 执行工具 → 追加结果 → 回到步骤 2
        # 5. 如果是 final_answer → 返回
        # 6. 如果超过 max_steps → 强制结束
        pass


# ============================================================
# 自检
# ============================================================
if __name__ == "__main__":
    reset()

    section("1. 工具测试")
    # TODO: 取消注释测试
    # result = calculator_tool("2 + 3 * 4")
    # print(f"计算器: 2 + 3 * 4 = {result}")
    # check("计算器正确", result == 14.0)

    # result = string_tool("Hello World", "reverse")
    # print(f"字符串 reverse: Hello World → {result}")
    # check("字符串反转正确", result == "dlroW olleH")

    # result = string_tool("Hello World", "word_count")
    # print(f"字符串 word_count: Hello World → {result}")
    # check("单词计数正确", result == 2)

    section("2. Agent 测试")
    # agent = SimpleAgent(llm, TOOLS)
    # result = agent.run("计算 15 * 7 + 3 的结果")
    # print(f"问题: 计算 15 * 7 + 3 的结果")
    # print(f"答案: {result['answer']}")
    # print(f"步骤数: {len(result['steps'])}")
    # check("Agent 返回了非空答案", len(result["answer"]) > 0)

    # result = agent.run("把 'Hello World' 反转一下")
    # print(f"问题: 把 'Hello World' 反转一下")
    # print(f"答案: {result['answer']}")
    # check("Agent 使用了字符串工具", len(result["steps"]) > 0)

    section("3. 多工具联合测试")
    # result = agent.run("统计 'Hello Agent World' 有多少个单词，然后计算这个数的平方")
    # print(f"问题: 统计 'Hello Agent World' 有多少个单词，然后计算这个数的平方")
    # print(f"答案: {result['answer']}")
    # print(f"步骤数: {len(result['steps'])}")
    # check("Agent 使用了多个工具", len(result["steps"]) >= 2)

    section("4. 反思：错误恢复测试")
    # 故意调用不存在的工具，观察 Agent 是否能根据错误信息自我修正
    # result = agent.run("帮我把 'hello' 变成大写")
    # 注意：如果 Agent 没有 string 工具，或者工具名写错了，观察它如何处理
    # print(f"问题: 帮我把 'hello' 变成大写")
    # print(f"结果: {result}")
    # 思考：你的 Agent 在 parse_error 发生后尝试了几次才修正？

    summary()
