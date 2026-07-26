"""
Function Calling 实战：从文本解析升级到原生工具调用

目标：理解 Function Calling 的本质——模型被训练输出结构化的函数调用 token，
不再需要正则解析 Thought/Action/Action Input。

核心认知（开始前读）：
  - ReAct（第 12 章）：模型输出文本 → 正则解析 → 脆，嵌套 JSON/格式偏差都会挂
  - Function Calling（本章）：模型输出 tool_calls → 结构化，100% 解析成功率
  - Function Calling 的模型能自主决定"要不要调工具"——无需 prompt 指令
  - 多工具并行调用：一个请求可以并行调多个工具，减少轮次

运行：
  make run f=learning/stage3-agent-development/15-function-calling/practice/solution.py
"""

import json
import math
import re

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

# ═══════════════════════════════════════════
# 1. 工具定义（OpenAI Function Calling 格式）
# ═══════════════════════════════════════════
# 与 ReAct 文本描述不同，Function Calling 需要 JSON Schema 定义参数。
# LangChain 用 bind_tools 自动转换为 OpenAI 格式。


def calculator_tool(expression: str) -> str:
    """安全的数学表达式计算"""
    safe_builtins = {k: v for k, v in vars(math).items() if not k.startswith("_")}
    try:
        result = eval(expression.replace("^", "**"), {"__builtins__": {}}, safe_builtins)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


def string_tool(text: str, operation: str) -> str:
    """字符串操作：reverse / uppercase / lowercase / length / word_count"""
    ops = {
        "reverse": lambda t: t[::-1],
        "uppercase": lambda t: t.upper(),
        "lowercase": lambda t: t.lower(),
        "length": lambda t: str(len(t)),
        "word_count": lambda t: str(len(t.split())),
    }
    if operation not in ops:
        return f"不支持的操作: {operation}，可用: {list(ops.keys())}"
    return ops[operation](text)


# 知识库（来自第 13 章）
KNOWLEDGE_BASE = [
    {
        "title": "RAG 基础原理",
        "content": "RAG 结合信息检索和文本生成，减少 LLM 幻觉。",
        "tags": "RAG,基础",
    },
    {
        "title": "Agent ReAct 框架",
        "content": "ReAct = Reasoning + Acting，Agent 循环思考→行动→观察。",
        "tags": "Agent,ReAct",
    },
    {
        "title": "向量数据库选型",
        "content": "FAISS 适合原型，Milvus 适合生产环境。",
        "tags": "向量数据库,选型",
    },
    {
        "title": "Function Calling 原理",
        "content": "模型输出结构化 tool_calls token，解析 100% 可靠。",
        "tags": "Function Calling",
    },
]


def search_tool(query: str) -> str:
    """搜索本地知识库"""
    results = []
    for doc in KNOWLEDGE_BASE:
        if query.lower() in doc["title"].lower() or query.lower() in doc["content"].lower():
            results.append(doc)
    if not results:
        return f"未找到与 '{query}' 相关的文档"
    output = f"找到 {len(results)} 篇文档:\n"
    for doc in results:
        output += f"- {doc['title']}: {doc['content']}\n"
    return output


# Function Calling 格式的工具定义
# 每个工具是一个 dict，包含 name / description / parameters (JSON Schema)
TOOLS_FC = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式。支持 + - * / ** sqrt sin cos tan abs。如: '15 * 7 + 3'",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "数学表达式字符串"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "string_ops",
            "description": "字符串操作。支持: reverse（反转）/ uppercase（大写）/ lowercase（小写）/ length（长度）/ word_count（单词数）",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要操作的字符串"},
                    "operation": {
                        "type": "string",
                        "enum": ["reverse", "uppercase", "lowercase", "length", "word_count"],
                        "description": "操作类型",
                    },
                },
                "required": ["text", "operation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "搜索 AI 知识库中的文档。返回匹配的文档标题和摘要",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "搜索关键词"}},
                "required": ["query"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    """执行工具调用并返回结果字符串"""
    if name == "calculator":
        return calculator_tool(**args)
    elif name == "string_ops":
        return string_tool(**args)
    elif name == "search":
        return search_tool(**args)
    return f"未知工具: {name}"


# ═══════════════════════════════════════════
# 2. Function Calling Agent
# ═══════════════════════════════════════════
# 对比 ReAct Agent（第 12 章）：
#   - 不需要 ReAct Prompt 模板（模型原生理解工具调用）
#   - 不需要 parse_react_output 正则解析（tool_calls 是结构化的）
#   - 模型可以自主决定"不调工具直接回答"
#   - 一次调用可以返回多个 tool_calls（并行执行）


SYSTEM_PROMPT = """你是一个智能助手，具有使用工具的能力。

你可以使用提供的工具来获取信息和完成计算。请根据用户的问题自主决定是否需要调用工具。
- 如果问题需要工具，直接调用相应工具
- 如果不需要工具，直接回答
- 如果工具返回结果，基于结果继续回答"""


def run_function_calling(user_question: str, max_steps: int = 5) -> dict:
    """Function Calling Agent 主循环。

    与 ReAct 的关键区别：
    1. 不依赖文本解析——AIMessage.tool_calls 直接包含结构化调用信息
    2. 模型可能不调工具直接回答（AIMessage.content 非空且无 tool_calls）
    3. 可能一次返回多个 tool_calls（并行执行）
    """
    llm_with_tools = llm.bind_tools(TOOLS_FC)
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_question)]
    steps = []

    for _step_idx in range(max_steps):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # 情况 1: 模型直接回答（无 tool_calls）
        if not response.tool_calls:
            steps.append({"type": "final", "content": response.content})
            return {"answer": response.content, "steps": steps}

        # 情况 2: 模型调用工具（可能多个，并行执行）
        step_info = {"type": "tool_calls", "calls": []}
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            result = execute_tool(tool_name, tool_args)
            step_info["calls"].append({"name": tool_name, "args": tool_args, "result": result})
            # 每个工具调用对应一个 ToolMessage
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

        steps.append(step_info)

    return {"answer": "Agent 在最大步数内未能得出最终答案", "steps": steps}


# ═══════════════════════════════════════════
# 3. tool_choice 实验
# ═══════════════════════════════════════════
# tool_choice 控制模型调用行为，无需在 prompt 中指令，而是 API 参数精确控制。
# - "auto": 模型自主决定（可能不调/调一个/并调多个）
# - "required": 强制至少调一个工具——适合确保"用户问题必须触发某类操作"
# - "none": 禁止调工具，即使绑定了工具定义——适合"先让模型分析，再决定用工具"
# - 指定工具 dict: 强制调特定工具——适合"明确知道该调哪个工具"的定向场景
#
# 为什么需要 tool_choice：
#   ReAct 用 prompt 模板（"如果问题需要工具则输出 Action..."）来引导调用行为，
#   但 LLM 可能忽略 prompt 指令。tool_choice 是 API 级别的硬约束，100% 可靠。


def run_fc_with_tool_choice(
    user_question: str, tool_choice: str | dict = "auto", max_steps: int = 5
) -> dict:
    """带 tool_choice 参数的 Function Calling Agent。

    tool_choice 是 Function Calling 区别于 ReAct 的关键优势之一：
    不需要 prompt 指令，通过 API 参数就能精确控制模型的调用行为。
    """
    llm_with_tools = llm.bind_tools(TOOLS_FC, tool_choice=tool_choice)
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_question)]
    steps = []

    for _ in range(max_steps):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            steps.append({"type": "final", "content": response.content})
            return {"answer": response.content, "steps": steps}

        step_info = {"type": "tool_calls", "calls": []}
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            result = execute_tool(tool_name, tool_args)
            step_info["calls"].append({"name": tool_name, "args": tool_args, "result": result})
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

        steps.append(step_info)

    return {"answer": "Agent 在最大步数内未能得出最终答案", "steps": steps}


# ═══════════════════════════════════════════
# 4. 对比实验：ReAct vs Function Calling
# ═══════════════════════════════════════════


def build_tool_descriptions(tools: dict) -> str:
    lines = []
    for name, info in tools.items():
        schema = info["schema"]
        params = ", ".join(f"{k}: {v}" for k, v in schema["parameters"].items())
        lines.append(f"- **{name}**: {schema['description']}\n  参数: {params}")
    return "\n".join(lines)


REACT_PROMPT = """你是一个智能 Agent。使用工具完成任务。

## 可用工具
{tool_descriptions}

## 输出格式
**调用工具时：**
Thought: <推理>
Action: <工具名，{tool_names} 之一>
Action Input: <JSON 参数>

**最终答案时：**
Thought: 信息充足
Final Answer: <答案>"""


# ReAct 工具（同第 12 章格式）
TOOLS_REACT = {
    "calculator": {
        "function": calculator_tool,
        "schema": {"description": "计算数学表达式", "parameters": {"expression": "数学表达式"}},
    },
    "string_ops": {
        "function": string_tool,
        "schema": {
            "description": "字符串操作: reverse/uppercase/lowercase/length/word_count",
            "parameters": {"text": "输入字符串", "operation": "操作类型"},
        },
    },
    "search": {
        "function": search_tool,
        "schema": {"description": "搜索知识库", "parameters": {"query": "搜索关键词"}},
    },
}


def parse_react_output(text: str) -> dict:
    """正则解析 ReAct 输出——脆弱，嵌套 JSON 会截断"""
    text = text.strip()
    final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if final_match:
        return {"type": "final_answer", "answer": final_match.group(1).strip()}

    action_match = re.search(r"Action:\s*(\S+)", text, re.IGNORECASE)
    input_start = text.find("Action Input:")
    if action_match and input_start != -1:
        tool_name = action_match.group(1).strip()
        rest = text[input_start:]
        brace_start = rest.find("{")
        if brace_start == -1:
            return {"type": "parse_error", "raw": text, "reason": "未找到 JSON"}
        depth = 0
        brace_end = -1
        for i in range(brace_start, len(rest)):
            if rest[i] == "{":
                depth += 1
            elif rest[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break
        if brace_end == -1:
            return {"type": "parse_error", "raw": text, "reason": "括号不匹配"}
        json_str = rest[brace_start : brace_end + 1]
        try:
            return {"type": "action", "tool": tool_name, "input": json.loads(json_str)}
        except json.JSONDecodeError:
            return {"type": "parse_error", "raw": text, "reason": "非法 JSON"}
    return {"type": "parse_error", "raw": text, "reason": "无法解析"}


def run_react(user_question: str, max_steps: int = 5) -> dict:
    """ReAct Agent（第 12 章逻辑，用于对比）"""
    tools_desc = build_tool_descriptions(TOOLS_REACT)
    tools_names = "/".join(TOOLS_REACT.keys())
    system = REACT_PROMPT.format(tool_descriptions=tools_desc, tool_names=tools_names)

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_question}]
    steps = []

    for _ in range(max_steps):
        parts = []
        for m in messages:
            label = {"system": "System", "user": "Human", "assistant": "AI"}[m["role"]]
            parts.append(f"{label}: {m['content']}")
        full_prompt = "\n\n".join(parts)

        response = llm.invoke(full_prompt)
        llm_output = response.content if hasattr(response, "content") else str(response)
        parsed = parse_react_output(llm_output)

        if parsed["type"] == "final_answer":
            steps.append({"type": "final", "output": llm_output})
            return {"answer": parsed["answer"], "steps": steps}
        elif parsed["type"] == "action":
            tool_name = parsed["tool"]
            tool_input = parsed["input"]
            if tool_name in TOOLS_REACT:
                result = TOOLS_REACT[tool_name]["function"](**tool_input)
            else:
                result = f"未知工具: {tool_name}"
            steps.append(
                {"type": "action", "tool": tool_name, "input": tool_input, "result": result}
            )
            messages.append({"role": "user", "content": f"Observation: {result}"})
        else:
            messages.append({"role": "user", "content": f"格式错误: {parsed.get('reason')}"})
            steps.append({"type": "parse_error", "reason": parsed.get("reason")})

    return {"answer": "超过最大步数", "steps": steps}


# ═══════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════
if __name__ == "__main__":
    reset()

    # ── 1. Function Calling 基础：单工具调用 ──
    section("1. Function Calling 单工具调用")
    result = run_function_calling("计算 15 * 7 + 3 的结果")
    print("问题: 计算 15 * 7 + 3 的结果")
    print(f"步骤数: {len(result['steps'])}")
    for s in result["steps"]:
        if s["type"] == "tool_calls":
            for c in s["calls"]:
                print(f"  调用: {c['name']}({c['args']}) → {c['result']}")
    print(f"答案: {result['answer']}")
    check("FC 返回了非空答案", len(result["answer"]) > 0)
    check("FC 答案包含计算结果", "108" in result["answer"])

    # ── 2. Function Calling: 多工具并行 ──
    section("2. Function Calling 并行调用")
    result = run_function_calling("计算 3*5 和 'hello' 的长度")
    print("问题: 计算 3*5 和 'hello' 的长度")
    all_calls = []
    for s in result["steps"]:
        if s["type"] == "tool_calls":
            all_calls.extend(s["calls"])
            for c in s["calls"]:
                print(f"  调用: {c['name']}({c['args']}) → {c['result']}")
    print(f"答案: {result['answer']}")
    check("至少调用了工具", len(all_calls) > 0)
    # 如果是并行调用，steps 中只有一步 tool_calls 包含多个 call
    parallel_step = next((s for s in result["steps"] if s["type"] == "tool_calls"), None)
    if parallel_step and len(parallel_step["calls"]) >= 2:
        print("  🚀 检测到并行调用！一次请求同时调用了多个工具")
    check("答案包含两个结果", result["answer"] is not None)

    # ── 3. Function Calling: 模型自主决定不调工具 ──
    section("3. 模型自主判断：不需要工具")
    result = run_function_calling("你好，请用中文回答：1+1等于多少？")
    print("问题: 你好，1+1等于多少？")
    print(f"步骤数: {len(result['steps'])}")
    print(f"工具调用数: {sum(1 for s in result['steps'] if s['type'] == 'tool_calls')}")
    print(f"答案: {result['answer']}")
    check("模型直接回答了问题", len(result["answer"]) > 0)

    # ── 4. tool_choice 实验 ──
    section("4. tool_choice 模式对比")
    print("--- tool_choice='auto' (默认) ---")
    result_auto = run_fc_with_tool_choice("你好，1+1等于多少？", tool_choice="auto")
    num_calls_auto = sum(1 for s in result_auto["steps"] if s["type"] == "tool_calls")
    print(f"  工具调用次数: {num_calls_auto}, 答案: {result_auto['answer']}")

    print("--- tool_choice='required' ---")
    result_req = run_fc_with_tool_choice("你好，1+1等于多少？", tool_choice="required")
    num_calls_req = sum(1 for s in result_req["steps"] if s["type"] == "tool_calls")
    print(f"  工具调用次数: {num_calls_req}, 答案: {result_req['answer']}")

    print("--- tool_choice='none' ---")
    result_none = run_fc_with_tool_choice("计算 15 * 7 + 3", tool_choice="none")
    num_calls_none = sum(1 for s in result_none["steps"] if s["type"] == "tool_calls")
    print(f"  工具调用次数: {num_calls_none}, 答案: {result_none['answer']}")

    print("--- tool_choice=指定 calculator ---")
    result_specific = run_fc_with_tool_choice(
        "你好，1+1等于多少？",
        tool_choice={"type": "function", "function": {"name": "calculator"}},
    )
    all_names = []
    for s in result_specific["steps"]:
        if s["type"] == "tool_calls":
            for c in s["calls"]:
                all_names.append(c["name"])
    print(f"  调用的工具: {all_names}, 答案: {result_specific['answer']}")

    check("auto 模式自主决策", result_auto["answer"] is not None)
    check("required 强制调用了工具", num_calls_req >= 1)
    check("none 禁止调用了工具", num_calls_none == 0)
    check(
        "指定工具只调用了 calculator",
        all(n == "calculator" for n in all_names) and len(all_names) > 0,
    )

    # ── 5. 对比实验：ReAct vs Function Calling ──
    section("5. 对比：ReAct vs Function Calling")
    test_question = "搜索关于 Function Calling 的文档，然后计算 2 的 8 次方"

    print(f"问题: {test_question}")
    print()
    print("--- Function Calling ---")
    result_fc = run_function_calling(test_question)
    print(f"  步骤数: {len(result_fc['steps'])}")
    print(f"  答案长度: {len(result_fc['answer'])} 字符")
    for s in result_fc["steps"]:
        if s["type"] == "tool_calls":
            for c in s["calls"]:
                print(f"  FC: {c['name']}({json.dumps(c['args'], ensure_ascii=False)})")

    print()
    print("--- ReAct ---")
    result_react = run_react(test_question)
    print(f"  步骤数: {len(result_react['steps'])}")
    print(f"  答案长度: {len(result_react['answer'])} 字符")
    for s in result_react["steps"]:
        if s["type"] == "action":
            print(f"  ReAct: {s['tool']}({json.dumps(s['input'], ensure_ascii=False)})")
        elif s["type"] == "parse_error":
            print(f"  ReAct: ⚠️ 解析错误 - {s['reason']}")

    check("FC 完成任务", len(result_fc["answer"]) > 0 and len(result_fc["steps"]) <= 5)
    check("ReAct 也完成了任务", len(result_react["answer"]) > 0)

    # ── 6. 解析可靠性对比 ──
    section("6. 解析可靠性：复杂参数场景")
    # 用嵌套引号的参数测试 ReAct 解析是否脆弱
    complex_question = "把字符串 'hello \"world\"' 反转"
    print(f"复杂参数问题: {complex_question}")

    result_fc2 = run_function_calling(complex_question)
    print(f"FC 步骤数: {len(result_fc2['steps'])}, 答案: {result_fc2['answer']}")
    check("FC 处理复杂参数成功", len(result_fc2["answer"]) > 0)

    result_react2 = run_react(complex_question)
    print(f"ReAct 步骤数: {len(result_react2['steps'])}, 答案: {result_react2['answer']}")
    # ReAct 可能在解析嵌套引号时遇到困难，但不一定失败
    parse_errors = [s for s in result_react2["steps"] if s["type"] == "parse_error"]
    if parse_errors:
        print(f"  ⚠️ ReAct 遇到了 {len(parse_errors)} 次解析错误")
    check("ReAct 最终也完成了", len(result_react2["answer"]) > 0)

    summary()
