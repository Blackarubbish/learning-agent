"""
Function Calling 综合挑战：知识库分析助手

场景：构建一个"知识库分析助手" Agent，能搜索文档、计算统计信息、格式化输出。

需求：
  1. 用户输入一个主题关键词
  2. Agent 搜索知识库，找到相关文档
  3. Agent 计算：文档数量、标题总长度、平均标题长度
  4. Agent 用 string_ops 格式化最终输出（uppercase 标题）
  5. 至少使用 tool_choice="required" 确保工具被调用

提示：
  - 复用 solution.py 中的 TOOLS_FC 和 execute_tool
  - 用 bind_tools + tool_choice="required" 强制调用
  - 思考：一次对话需要多轮还是多步？FC 循环应该处理多轮工具调用

运行：
  make run f=learning/stage3-agent-development/15-function-calling/practice/challenge.py
"""

import json
import math

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

# ── 工具函数（从 solution.py 复制）──


def calculator_tool(expression: str) -> str:
    """安全的数学表达式计算"""
    allowed = set("0123456789+-*/().% **e sqrt sin cos tan abs pi").union(" ,")
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


KNOWLEDGE_BASE = [
    {"title": "RAG 基础原理", "content": "RAG 结合信息检索和文本生成，减少 LLM 幻觉。", "tags": "RAG,基础"},
    {"title": "Agent ReAct 框架", "content": "ReAct = Reasoning + Acting，Agent 循环思考→行动→观察。", "tags": "Agent,ReAct"},
    {"title": "向量数据库选型", "content": "FAISS 适合原型，Milvus 适合生产环境。", "tags": "向量数据库,选型"},
    {"title": "Function Calling 原理", "content": "模型输出结构化 tool_calls token，解析 100% 可靠。", "tags": "Function Calling"},
    {"title": "上下文工程实践", "content": "Offload/Retrieve/Compress/Isolate 四种策略管理 Agent 上下文。", "tags": "Agent,上下文工程"},
    {"title": "Agent Memory 设计", "content": "短期记忆+长期记忆+工作记忆三层架构支撑复杂任务。", "tags": "Agent,Memory"},
    {"title": "混合检索策略", "content": "BM25 关键词检索与向量语义检索互补，RRF 融合排序。", "tags": "RAG,检索"},
    {"title": "SQL Agent 安全", "content": "只读围栏+Schema 探索防止 Agent 幻觉导致数据灾难。", "tags": "Agent,SQL,安全"},
]


def search_tool(query: str) -> str:
    """搜索本地知识库"""
    results = []
    for doc in KNOWLEDGE_BASE:
        if query.lower() in doc["title"].lower() or query.lower() in doc["content"].lower() or query.lower() in doc["tags"].lower():
            results.append(doc)
    if not results:
        return f"未找到与 '{query}' 相关的文档"
    output = f"找到 {len(results)} 篇文档:\n"
    for doc in results:
        output += f"- {doc['title']}: {doc['content']}\n"
    return output


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


# ────── 你来实现 ──────


SYSTEM_PROMPT = """你是一个知识库分析助手。你可以搜索文档、执行计算、格式化文本。

工作流程：
1. 首先搜索用户指定的主题
2. 基于搜索结果计算统计信息（文档数量、标题统计等）
3. 如果需要，格式化输出

请逐步使用工具完成分析任务。"""


def knowledge_analyzer(topic: str) -> dict:
    """知识库分析助手：搜索 → 计算 → 格式化。

    要求：
      1. 使用 tool_choice="required" 强制第一步就调用搜索工具
      2. 搜索后基于结果计算统计信息
      3. 最后用 string_ops 格式化关键标题
      4. 返回完整的分析结果

    返回格式: {"answer": str, "steps": list}
    """
    # TODO: 实现综合 FC Agent
    # 提示:
    #   1. llm.bind_tools(TOOLS_FC, tool_choice="required")
    #   2. 首次对话应触发 search 工具
    #   3. 基于搜索结果继续调用 calculator 和 string_ops
    #   4. 使用 FC 循环（参考 solution.py 的 run_function_calling）

    return {"answer": "TODO: 实现知识库分析助手", "steps": []}


# ── 自检 ──
if __name__ == "__main__":
    reset()

    section("知识库分析助手")
    result = knowledge_analyzer("Agent")

    print(f"主题: Agent")
    print(f"步骤数: {len(result['steps'])}")
    for s in result["steps"]:
        if s["type"] == "tool_calls":
            for c in s["calls"]:
                print(f"  调用: {c['name']}({json.dumps(c['args'], ensure_ascii=False)})")
                # 只显示结果的前 80 字符
                short = c["result"][:80].replace("\n", " ")
                print(f"    → {short}...")
    print(f"\n答案:\n{result['answer']}")

    search_calls = []
    calc_calls = []
    str_calls = []
    for s in result["steps"]:
        if s["type"] == "tool_calls":
            for c in s["calls"]:
                if c["name"] == "search":
                    search_calls.append(c)
                elif c["name"] == "calculator":
                    calc_calls.append(c)
                elif c["name"] == "string_ops":
                    str_calls.append(c)

    check("至少调用了 search", len(search_calls) >= 1)
    check("至少调用了 calculator", len(calc_calls) >= 1)
    check("返回了非空答案", len(result["answer"]) > 0)
    check("答案提及了 Agent 相关文档", any(
        keyword in result["answer"].lower() for keyword in ["文档", "篇", "agent"]
    ))

    summary()
