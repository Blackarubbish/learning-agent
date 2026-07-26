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
  make run f=learning/stage3-agent-development/15-function-calling/practice/starter.py
"""

import json
import math
import re

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

# ═══════════════════════════════════════════
# 1. 工具函数（已提供——同第 12/13 章）
# ═══════════════════════════════════════════


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


KNOWN_DOCS = [
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
    for doc in KNOWN_DOCS:
        if query.lower() in doc["title"].lower() or query.lower() in doc["content"].lower():
            results.append(doc)
    if not results:
        return f"未找到与 '{query}' 相关的文档"
    output = f"找到 {len(results)} 篇文档:\n"
    for doc in results:
        output += f"- {doc['title']}: {doc['content']}\n"
    return output


def execute_tool(name: str, args: dict) -> str:
    """执行工具调用并返回结果字符串（已提供）"""
    if name == "calculator":
        return calculator_tool(**args)
    elif name == "string_ops":
        return string_tool(**args)
    elif name == "search":
        return search_tool(**args)
    return f"未知工具: {name}"


# ═══════════════════════════════════════════
# TODO 1: Function Calling 工具定义
# ═══════════════════════════════════════════
# Function Calling 和 ReAct 工具格式完全不同。
# ReAct 的"工具描述"是 prompt 中的一段文本，LLM 需要理解描述后输出文本格式的 Action。
# Function Calling 的"工具定义"是 JSON Schema——模型被训练直接输出结构化的 tool_call。
#
# 每个工具是一个 dict，格式为:
# {
#     "type": "function",
#     "function": {
#         "name": "工具名",
#         "description": "工具描述——很重要！LLM 据此决定是否调用",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "参数名": {"type": "类型", "description": "参数说明"},
#                 ...
#             },
#             "required": ["必填参数列表"]
#         }
#     }
# }
#
# TODO 1: 将 calculator / string_ops / search 三个工具转换为上述格式
# 提示: string_ops 的 operation 参数可以用 "enum" 字段限制可选值

TOOLS_FC = [
    # TODO: 填写 calculator 工具定义
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，支持 + - * / % ** 和 math 模块函数，如 sqrt, sin, cos, tan, abs, pi",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式，如 '2 + 2 * 3'",
                    },
                },
                "required": ["expression"],
            },
        },
    },
    # TODO: 填写 string_ops 工具定义（提示: operation 用 "enum" 限制为可选值）
    {
        "type": "function",
        "function": {
            "name": "string_ops",
            "description": "字符串操作工具，支持 reverse/uppercase/lowercase/length/word_count",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "输入字符串"},
                    "operation": {
                        "type": "string",
                        "description": "要执行的操作",
                        "enum": ["reverse", "uppercase", "lowercase", "length", "word_count"],
                    },
                },
                "required": ["text", "operation"],
            },
        },
    },
    # TODO: 填写 search 工具定义
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "搜索本地知识库，返回与查询相关的文档列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    },
]


# ═══════════════════════════════════════════
# TODO 2: Function Calling Agent 主循环
# ═══════════════════════════════════════════
# 对比 ReAct（第 12 章）：
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

    TODO 2: 实现 Function Calling 循环

    关键 API（LangChain + ChatOpenAI）:
      1. llm.bind_tools(TOOLS_FC) → 返回绑定了工具定义的 LLM
      2. llm_with_tools.invoke(messages) → 返回 AIMessage
      3. AIMessage.tool_calls → 工具调用列表（可能为空，可能有多个）
         每个 tool_call 是 {"name": 工具名, "args": dict, "id": str}
      4. AIMessage.content → 当 tool_calls 为空时，这是直接回答

    循环逻辑:
      1. 初始化 messages = [SystemMessage(系统提示), HumanMessage(用户问题)]
      2. 调用 llm_with_tools.invoke(messages)
      3. 把 response 添加到 messages 中
      4. 如果 response 无 tool_calls → response.content 就是答案 → 返回
      5. 如果 response 有 tool_calls → 遍历每个 tc:
         - 调用 execute_tool(tc["name"], tc["args"]) 得到结果
         - 创建 ToolMessage(content=结果, tool_call_id=tc["id"])
         - 添加到 messages
      6. 回到步骤 2（直到得出答案或达到 max_steps）

    ToolMessage 格式:
      ToolMessage(content="工具返回的结果", tool_call_id="<tc中的id>")
    """
    llm_with_tools = llm.bind_tools(TOOLS_FC)

    # TODO: 初始化 messages（SystemMessage + HumanMessage）
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_question),
    ]
    steps = []
    for _ in range(max_steps):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            return {"answer": response.content, "steps": steps}

        print(
            f"模型调用了 {len(response.tool_calls)} 个工具: {[tc['name'] for tc in response.tool_calls]}"
        )

        # 情况 2: 模型调用工具（可能多个，并行执行）
        tool_calls = response.tool_calls
        step_info = {"type": "tool_calls", "calls": []}
        for tc in tool_calls:
            result = execute_tool(tc["name"], tc["args"])
            tool_message = ToolMessage(content=result, tool_call_id=tc["id"])
            messages.append(tool_message)
            step_info["calls"].append({"name": tc["name"], "args": tc["args"], "result": result})
        steps.append(step_info)
    return {"answer": "Agent reached maximum steps", "steps": steps}


# ═══════════════════════════════════════════
# TODO 3: tool_choice 实验
# ═══════════════════════════════════════════
# Function Calling 的 tool_choice 参数控制模型"要不要调工具、调哪个"。
# 这是 FC 相比 ReAct 的一个重要优势——不需要在 prompt 里强行指令，而是通过 API 参数精确控制。
#
# tool_choice 的 4 种模式:
#   "auto"       — 默认，模型自主决定（可能不调，可能调一个，可能调多个）
#   "required"   — 强制模型必须调用工具（至少一个）
#   "none"       — 禁止模型调用工具（即使你绑定了工具定义）
#   指定工具      — 强制调用特定工具，如 {"type": "function", "function": {"name": "calculator"}}
#
# TODO 3: 实现 run_fc_with_tool_choice，接收 tool_choice 参数控制行为
#
# 提示: llm.bind_tools(TOOLS_FC, tool_choice="required") 即可设置
# tool_choice 支持的值: "auto"(默认) / "required" / "none" / 或指定工具dict


def run_fc_with_tool_choice(
    user_question: str, tool_choice: str | dict = "auto", max_steps: int = 5
) -> dict:
    """带 tool_choice 参数的 Function Calling Agent。

    TODO:
      1. bind_tools 时传入 tool_choice 参数
      2. 其余循环逻辑和 run_function_calling 相同
      3. 思考: 如何在 "none" 模式下验证绑定了工具但不会被调用？
    """
    # TODO: llm_with_tools = llm.bind_tools(TOOLS_FC, tool_choice=???)
    llm_with_tools = llm.bind_tools(TOOLS_FC, tool_choice=tool_choice)
    # TODO: 复用 FC 循环逻辑（可直接复用 run_function_calling 的模式）
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_question),
    ]
    steps = []
    for _ in range(max_steps):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            return {"answer": response.content, "steps": steps}

        # 情况 2: 模型调用工具（可能多个，并行执行）
        tool_calls = response.tool_calls
        step_info = {"type": "tool_calls", "calls": []}
        for tc in tool_calls:
            result = execute_tool(tc["name"], tc["args"])
            tool_message = ToolMessage(content=result, tool_call_id=tc["id"])
            messages.append(tool_message)
            step_info["calls"].append({"name": tc["name"], "args": tc["args"], "result": result})
        steps.append(step_info)

    return {"answer": "Agent reached maximum steps", "steps": steps}


# 4. 对比实验：ReAct Agent（已提供，来自第 12 章）
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
    """正则解析 ReAct 输出——注意：这是对比基线，FC 不需要这个"""
    text = text.strip()
    final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if final_match:
        return {"type": "final_answer", "answer": final_match.group(1).strip()}
    action_match = re.search(r"Action:\s*(\S+)", text, re.IGNORECASE)
    input_start = text.find("Action Input:")
    if action_match and input_start != -1:
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
        try:
            return {
                "type": "action",
                "tool": action_match.group(1).strip(),
                "input": json.loads(rest[brace_start : brace_end + 1]),
            }
        except json.JSONDecodeError:
            return {"type": "parse_error", "raw": text, "reason": "非法 JSON"}
    return {"type": "parse_error", "raw": text, "reason": "无法解析"}


def run_react(user_question: str, max_steps: int = 5) -> dict:
    """ReAct Agent（第 12 章逻辑，已提供——用于对比 FC 和 ReAct 的区别）"""
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
# 自检函数
# ═══════════════════════════════════════════


def test_single_tool_call():
    """1. Function Calling 基础：单工具调用"""
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


def test_parallel_tool_calls():
    """2. Function Calling: 多工具并行"""
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
    parallel_step = next((s for s in result["steps"] if s["type"] == "tool_calls"), None)
    if parallel_step and len(parallel_step["calls"]) >= 2:
        print("  🚀 检测到并行调用！一次请求同时调用了多个工具")
    check("答案包含两个结果", result["answer"] is not None)


def test_no_tool_needed():
    """3. Function Calling: 模型自主决定不调工具"""
    section("3. 模型自主判断：不需要工具")
    result = run_function_calling("你好，请用中文回答：1+1等于多少？")
    print("问题: 你好，1+1等于多少？")
    print(f"步骤数: {len(result['steps'])}")
    print(f"工具调用数: {sum(1 for s in result['steps'] if s['type'] == 'tool_calls')}")
    print(f"答案: {result['answer']}")
    check("模型直接回答了问题", len(result["answer"]) > 0)


def test_tool_choice_modes():
    """4. tool_choice 实验"""
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


def test_react_vs_fc():
    """5. 对比实验：ReAct vs Function Calling"""
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


def test_complex_params():
    """6. 解析可靠性对比"""
    section("6. 解析可靠性：复杂参数场景")
    complex_question = "把字符串 'hello \"world\"' 反转"
    print(f"复杂参数问题: {complex_question}")

    result_fc2 = run_function_calling(complex_question)
    print(f"FC 步骤数: {len(result_fc2['steps'])}, 答案: {result_fc2['answer']}")
    check("FC 处理复杂参数成功", len(result_fc2["answer"]) > 0)

    result_react2 = run_react(complex_question)
    print(f"ReAct 步骤数: {len(result_react2['steps'])}, 答案: {result_react2['answer']}")
    parse_errors = [s for s in result_react2["steps"] if s["type"] == "parse_error"]
    if parse_errors:
        print(f"  ⚠️ ReAct 遇到了 {len(parse_errors)} 次解析错误")
    check("ReAct 最终也完成了", len(result_react2["answer"]) > 0)


def main():
    """依次运行所有自检验证"""
    reset()
    test_single_tool_call()
    test_parallel_tool_calls()
    test_no_tool_needed()
    test_tool_choice_modes()
    test_react_vs_fc()
    test_complex_params()
    summary()


if __name__ == "__main__":
    main()
