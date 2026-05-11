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

import json
import math
import re

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

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
    try:
        # 这里我们使用 eval，但在实际生产环境中应该使用更安全的解析器
        # 例如：mathjs、sympy 或者自己实现一个简单的解析器
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expression, {"__builtins__": None}, allowed_names)
        return f"{result}"
    except Exception as e:
        return f"Error: {str(e)}"


# TODO 1.2: 实现字符串工具函数
def string_tool(text: str, operation: str) -> str:
    """字符串操作：reverse / uppercase / length / word_count"""
    if operation == "reverse":
        return text[::-1]
    elif operation == "uppercase":
        return text.upper()
    elif operation == "length":
        return f"{len(text)}"
    elif operation == "word_count":
        return f"{len(text.split())}"
    else:
        return f"Error: 未知操作 '{operation}'"


# TODO 1.3: 把工具注册为 tool registry
# 格式: {"name": ..., "function": callable, "schema": {"description": ..., "parameters": {...}}}
TOOLS = {
    "calculator": {
        "name": "calculator",
        "schema": {
            "description": "计算数学表达式，支持 + - * / ** sqrt() sin() cos() 等",
            "parameters": {"expression": "数学表达式字符串，如 '2 + 3 * 4'"},
        },
        "function": calculator_tool,
    },
    "string_tool": {
        "name": "string_tool",
        "schema": {
            "description": "字符串操作：reverse / uppercase / length / word_count",
            "parameters": {
                "text": "输入字符串",
                "operation": "操作类型，reverse/uppercase/length/word_count",
            },
        },
        "function": string_tool,
    },
}


def build_tool_descriptions(tools: dict) -> str:
    """构建工具描述字符串，供 LLM 参考"""
    descriptions = []
    for tool in tools.values():
        desc = f"{tool['name']}: {tool['schema']['description']} 参数: {json.dumps(tool['schema']['parameters'])}"
        descriptions.append(desc)
    return "\n".join(descriptions)


def build_tool_names(tools: dict) -> str:
    """构建工具名称列表字符串，供 LLM 参考"""
    return ", ".join(tool["name"] for tool in tools.values())


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
你是一个智能 Agent，具有推理和行动能力。你可以使用工具来完成任务。

## 可用工具

{tool_descriptions}

## 输出格式

你必须严格按照以下格式输出。每次只输出一个 Thought 加上一个 Action 或一个 Final Answer。

**调用工具时：**
Thought: <你的推理过程>
Action: <工具名称，必须是 {tool_names} 之一>
Action Input: <JSON 格式的参数，key 必须和工具定义一致>

**得到最终答案时：**
Thought: 我现在已经收集到足够的信息来回答问题
Final Answer: <简洁的最终答案>

注意：
- Action Input 必须是合法的 JSON 对象
- 一次只能调用一个工具
- 如果工具返回了结果，你需要基于结果继续推理
- 如果工具调用失败或返回错误，尝试其他方式或如实告知用户
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
    # 尝试匹配 Final Answer
    final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if final_match:
        return {"type": "final_answer", "answer": final_match.group(1).strip()}

    # 尝试匹配 Action + Action Input
    action_match = re.search(r"Action:\s*(\S+)", text, re.IGNORECASE)
    input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)

    if action_match and input_match:
        tool_name = action_match.group(1).strip()
        try:
            tool_input = json.loads(input_match.group(1).strip())
        except json.JSONDecodeError:
            return {"type": "parse_error", "raw": text, "reason": "Action Input 不是合法 JSON"}
        return {"type": "action", "tool": tool_name, "input": tool_input}

    # 无法解析
    return {"type": "parse_error", "raw": text, "reason": "无法识别输出格式"}


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
        tools_desc = build_tool_descriptions(self.tools)
        tools_names = build_tool_names(self.tools)
        system_prompt = REACT_PROMPT.format(tool_descriptions=tools_desc, tool_names=tools_names)
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        steps = []

        for step in range(max_steps):
            print(f"\n[ReAct] {'=' * 50}")
            print(f"[ReAct] 📍 Step {step + 1}/{max_steps}")
            print(f"[ReAct] {'=' * 50}")

            if step == 0:
                messages.append({"role": "user", "content": user_question})
            else:
                last_step = steps[-1]
                observation = f"Observation: {last_step['result']}"
                print(f"[ReAct] 👀 Observation: {last_step['result'][:120]}")
                messages.append({"role": "user", "content": observation})

            parts = []
            for m in messages:
                if m["role"] == "system":
                    label = "System"
                elif m["role"] == "user":
                    label = "Human"
                else:
                    label = "AI"
                parts.append(f"{label}: {m['content']}")
            full_prompt = "\n\n".join(parts)

            response = self.llm.invoke(full_prompt)
            llm_output = response.content if hasattr(response, "content") else str(response)
            print(f"[ReAct] 🤖 LLM output:\n{llm_output[:300]}")

            parsed = parse_react_output(llm_output)
            if parsed["type"] == "final_answer":
                print("[ReAct] ✅ Final answer")
                steps.append({"thought": llm_output, "type": "final"})
                return {"answer": parsed["answer"], "steps": steps}

            elif parsed["type"] == "action":
                tool_name = parsed["tool"]
                tool_input = parsed["input"]
                print(f"[ReAct] 🔧 Tool call: {tool_name}({tool_input})")
                if tool_name in self.tools:
                    tool_func = self.tools[tool_name]["function"]
                    try:
                        result = tool_func(**tool_input)
                    except TypeError as e:
                        result = f"工具调用错误: 参数不匹配 ({str(e)}). 请检查工具定义和输入参数是否一致。"
                    except Exception as e:
                        result = f"工具执行错误: {str(e)}"
                else:
                    result = f"错误: 没有名为'{tool_name}'的工具, 可用工具: {tools_names}"
                print(f"[ReAct] 📋 Tool result: {result[:120]}")
                steps.append(
                    {
                        "thought": llm_output,
                        "type": "action",
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result,
                    }
                )
            else:
                error_info = f"格式错误: {parsed.get('reason', '未知解析错误')}"
                print(f"[ReAct] ⚠️ Parse error: {error_info}")
                steps.append(
                    {
                        "thought": llm_output,
                        "type": "parse_error",
                        "error_info": error_info,
                    }
                )

            # 5. 如果是 final_answer → 返回
            # 6. 如果超过 max_steps → 强制结束

        last_output = steps[-1].get("thought", "") if steps else ""
        if steps and steps[-1]["type"] == "action" and "错误" not in steps[-1].get("result", ""):
            return {"answer": steps[-1]["result"], "steps": steps}
        return {
            "answer": f"Agent 在 {max_steps} 步内未能得出最终答案。最后状态: {last_output[:200]}",
            "steps": steps,
        }


# ============================================================
# 自检
# ============================================================
if __name__ == "__main__":
    reset()

    section("1. 工具测试")
    # TODO: 取消注释测试
    result = calculator_tool("2 + 3 * 4")
    print(f"计算器: 2 + 3 * 4 = {result}")
    check("计算器正确", result == "14")

    result = string_tool("Hello World", "reverse")
    print(f"字符串 reverse: Hello World → {result}")
    check("字符串反转正确", result == "dlroW olleH")

    result = string_tool("Hello World", "word_count")
    print(f"字符串 word_count: Hello World → {result}")
    check("单词计数正确", result == "2")

    section("2. Agent 测试")
    agent = SimpleAgent(llm, TOOLS)
    result = agent.run("计算 15 * 7 + 3 的结果")
    print("问题: 计算 15 * 7 + 3 的结果")
    print(f"答案: {result['answer']}")
    print(f"步骤数: {len(result['steps'])}")
    check("Agent 返回了非空答案", len(result["answer"]) > 0)

    result = agent.run("把 'Hello World' 反转一下")
    print("问题: 把 'Hello World' 反转一下")
    print(f"答案: {result['answer']}")
    check("Agent 使用了字符串工具", len(result["steps"]) > 0)

    section("3. 多工具联合测试")
    result = agent.run("统计 'Hello Agent World' 有多少个单词，然后计算这个数的平方")
    print("问题: 统计 'Hello Agent World' 有多少个单词，然后计算这个数的平方")
    print(f"答案: {result['answer']}")
    print(f"步骤数: {len(result['steps'])}")
    check("Agent 使用了多个工具", len(result["steps"]) >= 2)

    section("4. 反思：错误恢复测试")
    # 故意调用不存在的工具，观察 Agent 是否能根据错误信息自我修正
    result = agent.run("帮我把 'hello' 变成首字母大写")
    # 注意：如果 Agent 没有 string 工具，或者工具名写错了，观察它如何处理
    print("问题: 帮我把 'hello' 变成大写")
    print(f"结果: {result}")
    # 思考：你的 Agent 在 parse_error 发生后尝试了几次才修正？

    summary()
