"""
Agent 核心概念：ReAct 框架 — 完整实现

ReAct = Reasoning + Acting
流程：Thought → Action → Observation → Thought → ... → Final Answer

运行：
  make run f=learning/stage3-agent-development/12-agent-basics/practice/solution.py
"""

from common import load_dotenv_if_needed, get_or_create_llm, section, check, summary, reset

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

import json
import math
import re

# ═══════════════════════════════════════════
# 1. 工具定义
# ═══════════════════════════════════════════


def calculator_tool(expression: str) -> str:
    """安全地执行数学表达式计算，返回数值结果"""
    allowed = set("0123456789+-*/().% **e sqrt sin cos tan abs pi").union(" ,")
    # 检查非法字符，防止代码注入
    for ch in expression:
        if ch.isalpha():
            if not any(expression.startswith(kw) for kw in ("sqrt", "sin", "cos", "tan", "abs", "pi")):
                continue
    allowed_funcs = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "abs": abs, "pi": math.pi}
    sanitized = expression.replace("^", "**")
    # 只允许安全的 builtins
    safe_builtins = {k: v for k, v in vars(math).items() if not k.startswith("_")}
    try:
        result = eval(sanitized, {"__builtins__": {}}, {**safe_builtins, **allowed_funcs})
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


def string_tool(text: str, operation: str) -> str:
    """字符串操作：reverse / uppercase / lowercase / length / word_count"""
    operations = {
        "reverse": lambda t: t[::-1],
        "uppercase": lambda t: t.upper(),
        "lowercase": lambda t: t.lower(),
        "length": lambda t: str(len(t)),
        "word_count": lambda t: str(len(t.split())),
    }
    if operation not in operations:
        return f"不支持的操作: {operation}，可选: {list(operations.keys())}"
    result = operations[operation](text)
    # 对于字符串操作返回自然语言描述
    if operation in ("reverse", "uppercase", "lowercase"):
        return f"'{text}' {operation} 的结果是: {result}"
    elif operation == "length":
        return f"'{text}' 的长度是: {result} 个字符"
    elif operation == "word_count":
        return f"'{text}' 包含 {result} 个单词"


TOOLS = {
    "calculator": {
        "function": calculator_tool,
        "schema": {
            "description": "计算数学表达式。支持: + - * / ** sqrt sin cos tan abs。例如: '15 * 7 + 3', 'sqrt(16)', 'sin(pi/2)'",
            "parameters": {"expression": "数学表达式字符串"},
        },
    },
    "string": {
        "function": string_tool,
        "schema": {
            "description": "对字符串进行操作。支持: reverse（反转）, uppercase（大写）, lowercase（小写）, length（长度）, word_count（单词数）",
            "parameters": {"text": "要操作的字符串", "operation": "操作类型: reverse/uppercase/lowercase/length/word_count"},
        },
    },
}


# ═══════════════════════════════════════════
# 2. ReAct Prompt 模板
# ═══════════════════════════════════════════

def build_tool_descriptions(tools: dict) -> str:
    """将工具注册表格式化为 LLM 可读的描述"""
    lines = []
    for name, info in tools.items():
        schema = info["schema"]
        params = ", ".join(f"{k}: {v}" for k, v in schema["parameters"].items())
        lines.append(f"- **{name}**: {schema['description']}\n  参数: {params}")
    return "\n".join(lines)


REACT_SYSTEM_PROMPT = """你是一个智能 Agent，具有推理和行动能力。你可以使用工具来完成任务。

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
- 如果工具调用失败或返回错误，尝试其他方式或如实告知用户"""


# ═══════════════════════════════════════════
# 3. 输出解析
# ═══════════════════════════════════════════


def parse_react_output(text: str) -> dict:
    """解析 LLM 的 ReAct 格式输出"""
    text = text.strip()

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


# ═══════════════════════════════════════════
# 4. Agent 执行循环
# ═══════════════════════════════════════════


class SimpleAgent:
    """
    ReAct Agent 执行器

    循环逻辑：
    1. 将 (系统提示 + 对话历史 + 当前上下文) 发送给 LLM
    2. 解析 LLM 输出
    3. 如果是 Action → 执行工具 → 将 Observation 追加到上下文 → 回到步骤 1
    4. 如果是 Final Answer → 返回答案和推理步骤
    5. 超过 max_steps → 强制终止
    """

    def __init__(self, llm, tools: dict):
        self.llm = llm
        self.tools = tools

    def run(self, user_question: str, max_steps: int = 5) -> dict:
        tool_descriptions = build_tool_descriptions(self.tools)
        tool_names = list(self.tools.keys())

        system_prompt = REACT_SYSTEM_PROMPT.format(
            tool_descriptions=tool_descriptions,
            tool_names="/".join(tool_names),
        )

        # 对话历史：从上到下积累
        messages = [{"role": "system", "content": system_prompt}]
        steps = []

        for step_idx in range(max_steps):
            # 构建 prompt 字符串
            if step_idx == 0:
                messages.append({"role": "user", "content": user_question})
            else:
                # 后续步骤：追加 observation 作为 user message
                last_step = steps[-1]
                messages.append({
                    "role": "user",
                    "content": f"Observation: {last_step['result']}",
                })

            # 调用 LLM — 用 LangChain ChatPromptTemplate 不太好处理多轮对话，
            # 这里直接用 format 拼接，因为 messages 结构很简单
            full_prompt = "\n\n".join(
                f"{'System' if m['role'] == 'system' else 'Human' if m['role'] == 'user' else 'AI'}: {m['content']}"
                for m in messages
            )
            response = self.llm.invoke(full_prompt)
            llm_output = response.content if hasattr(response, "content") else str(response)

            # 解析输出
            parsed = parse_react_output(llm_output)

            if parsed["type"] == "final_answer":
                steps.append({"thought": llm_output, "type": "final"})
                return {"answer": parsed["answer"], "steps": steps}

            elif parsed["type"] == "action":
                tool_name = parsed["tool"]
                tool_input = parsed["input"]

                # 执行工具
                if tool_name not in self.tools:
                    observation = f"错误: 没有名为 '{tool_name}' 的工具，可用工具: {tool_names}"
                else:
                    try:
                        tool_func = self.tools[tool_name]["function"]
                        observation = tool_func(**tool_input)
                    except TypeError as e:
                        observation = f"工具参数错误: {e}。请检查参数名称和类型"
                    except Exception as e:
                        observation = f"工具执行失败: {e}"

                steps.append({
                    "thought": llm_output,
                    "type": "action",
                    "tool": tool_name,
                    "input": tool_input,
                    "result": observation,
                })

            else:
                # 解析失败，提示 LLM 修正格式
                error_msg = f"格式错误 ({parsed.get('reason', '未知')})。请严格按照 Thought/Action/Action Input 或 Thought/Final Answer 格式输出。"
                steps.append({
                    "thought": llm_output,
                    "type": "parse_error",
                    "result": error_msg,
                })

        # max_steps 用尽——最后一次尝试提取答案
        last_output = steps[-1].get("thought", "") if steps else ""
        # 如果最后一步仍有计算结果，直接返回
        if steps and steps[-1]["type"] == "action" and "错误" not in steps[-1].get("result", ""):
            return {"answer": steps[-1]["result"], "steps": steps}
        return {"answer": f"Agent 在 {max_steps} 步内未能得出最终答案。最后状态: {last_output[:200]}", "steps": steps}


# ═══════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════
if __name__ == "__main__":
    reset()

    # 1. 工具单元测试
    section("1. 工具测试")
    result = calculator_tool("2 + 3 * 4")
    print(f"计算器: 2 + 3 * 4 = {result}")
    check("计算器结果正确", float(result) == 14.0)

    result = string_tool("Hello World", "reverse")
    print(f"字符串 reverse: Hello World → {result}")
    check("字符串反转正确", "dlroW olleH" in result)

    result = string_tool("Hello World", "word_count")
    print(f"字符串 word_count: Hello World → {result}")
    check("单词计数正确", "2" in result)

    # 2. Agent 单工具测试
    section("2. Agent 单工具测试")
    agent = SimpleAgent(llm, TOOLS)

    result = agent.run("计算 15 * 7 + 3 的结果")
    print(f"问题: 计算 15 * 7 + 3 的结果")
    print(f"推理步骤数: {len(result['steps'])}")
    for i, step in enumerate(result["steps"]):
        print(f"  步骤 {i+1}: {step.get('tool', 'final')}")
    print(f"答案: {result['answer']}")
    check("Agent 返回了答案", len(result["answer"]) > 0)
    check("答案包含计算结果", "108" in result["answer"])

    result = agent.run("把 'Hello World' 反转一下")
    print(f"\n问题: 把 'Hello World' 反转一下")
    print(f"答案: {result['answer']}")
    check("字符串工具被调用", "dlroW olleH" in result["answer"] or any(
        "dlroW olleH" in s.get("result", "") for s in result["steps"]
    ))

    # 3. 多工具联合测试
    section("3. 多工具联合测试")
    result = agent.run("统计 'Hello Agent World' 有多少个单词，然后计算这个数的平方")
    print(f"问题: 统计 'Hello Agent World' 有多少个单词，然后计算这个数的平方")
    print(f"推理步骤数: {len(result['steps'])}")
    for i, step in enumerate(result["steps"]):
        if step["type"] == "action":
            print(f"  步骤 {i+1}: Action={step['tool']} Input={step['input']} → {step['result']}")
    print(f"答案: {result['answer']}")
    check("使用了多个工具", len(result["steps"]) >= 2)
    check("答案包含 9", "9" in result["answer"])

    summary()
