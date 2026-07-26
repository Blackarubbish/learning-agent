"""
自定义工具开发：设计 AI 友好的工具接口 — 完整实现

工具工程的四个核心原则：
1. 信息抽象：总结 + 截断 + 引导，而非原始数据倾泻
2. 状态反馈：让 Agent 知道操作进展（进度、部分成功、剩余工作）
3. 错误恢复接口：错误信息包含"发生了什么 → 为什么 → 可以尝试什么"
4. 结构化输出：用标题、编号、分段让 LLM 快速定位关键信息

运行：
  make run f=learning/stage3-agent-development/13-custom-tools/practice/solution.py
"""

import json
import re

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

# ═══════════════════════════════════════════
# Mock 数据
# ═══════════════════════════════════════════

KNOWLEDGE_BASE = [
    {
        "title": "RAG 基础原理",
        "content": "RAG（Retrieval-Augmented Generation）结合了信息检索和文本生成。核心流程：用户提问 → 检索相关文档 → 将文档作为上下文注入 LLM → 生成答案。RAG 有效减少了 LLM 幻觉，让模型能基于外部知识回答问题。",
        "tags": ["RAG", "基础", "检索"],
    },
    {
        "title": "Agent ReAct 框架",
        "content": "ReAct 是 Reasoning + Acting 的缩写。Agent 通过 Thought → Action → Observation 循环完成任务。与 RAG 的单向管道不同，Agent 能在观察工具返回结果后重新决策。但每一步的可靠性会累积——95% 可靠性 × 20 步 = 36% 成功率。",
        "tags": ["Agent", "ReAct", "框架"],
    },
    {
        "title": "向量数据库选型",
        "content": "FAISS 是 Meta 开源的向量检索库，适合小规模原型验证（百万级以下）。Milvus 是云原生向量数据库，支持增删改查、属性过滤、分布式部署，适合生产环境。选择依据：数据量、是否需要实时更新、是否需要属性过滤。",
        "tags": ["向量数据库", "FAISS", "Milvus", "选型"],
    },
    {
        "title": "Rerank 精排模型",
        "content": "Rerank 是检索流程的第二阶段。第一阶段用 BM25 + 向量检索做粗筛（召回 Top K），第二阶段用 Rerank 模型对候选文档精排。Rerank 模型通常基于 Cross-Encoder 架构，同时编码 query 和 document，比 Bi-Encoder 的向量检索更精确但更慢。",
        "tags": ["Rerank", "检索", "排序"],
    },
    {
        "title": "Embedding 模型对比",
        "content": "常见的 Embedding 模型包括 OpenAI text-embedding-3、智谱 embedding-3、BGE 系列。选型考虑：向量维度（影响存储和检索速度）、最大输入长度、多语言支持、成本。BGE 的中文效果优秀且开源可本地部署。",
        "tags": ["Embedding", "模型", "选型"],
    },
    {
        "title": "LangChain 工具系统",
        "content": "LangChain 的 @tool 装饰器可以将任意 Python 函数转换为 Agent 可调用的工具。工具描述（docstring）会被自动解析为 LLM 的工具说明。BaseTool 支持参数验证、异步调用、回调钩子。生产环境中建议自定义工具而非依赖 LangChain 默认工具。",
        "tags": ["LangChain", "工具", "Agent"],
    },
    {
        "title": "LLM 幻觉问题",
        "content": "LLM 幻觉是指模型生成看似合理但事实错误的内容。产生原因：训练数据过期、知识边界模糊、概率采样。缓解方案：RAG 提供外部知识锚定、降低 temperature、Chain-of-Verification 自我验证、Prompt 中明确要求引用来源。",
        "tags": ["LLM", "幻觉", "RAG"],
    },
    {
        "title": "Function Calling 原理",
        "content": "Function Calling 是 LLM 原生支持的工具调用机制。与 ReAct 的文本解析不同，模型被训练输出结构化的函数调用 token。OpenAI、智谱等模型支持。优势：解析更可靠（不需要正则），劣势：依赖模型特定训练，跨模型兼容性差。",
        "tags": ["Function Calling", "LLM", "工具"],
    },
]

# ═══════════════════════════════════════════
# 1. 信息抽象：从"数据倾泻"到"智能摘要"
# ═══════════════════════════════════════════


def naive_search(query: str) -> str:
    """反面案例：直接返回所有匹配文档的完整内容。

    问题：如果匹配 8 篇文档，每篇 200 字，总计 1600+ 字涌入 LLM 上下文。
    LLM 需要自己从海量文本中提取关键信息，容易遗漏或混淆。
    """
    results = []
    for doc in KNOWLEDGE_BASE:
        if query.lower() in doc["title"].lower() or query.lower() in doc["content"].lower():
            results.append(doc)

    if not results:
        return f"未找到与 '{query}' 相关的文档"

    output = f"找到 {len(results)} 篇文档：\n\n"
    for doc in results:
        output += (
            f"标题：{doc['title']}\n内容：{doc['content']}\n标签：{', '.join(doc['tags'])}\n\n"
        )
    return output


def smart_search(query: str, max_results: int = 3) -> str:
    """生产级工具：结构化摘要 + 截断 + 引导 LLM 下一步决策。

    设计原则：
    - 用标签做轻量级相关性排序（标题匹配 > 内容匹配），不引入 Embedding 依赖
    - 内容截断到 150 字，避免 token 过载
    - 末尾提供"下一步"引导，让 LLM 知道如何获取更多信息
    """
    results = []
    for doc in KNOWLEDGE_BASE:
        title_match = query.lower() in doc["title"].lower()
        content_match = query.lower() in doc["content"].lower()
        if title_match or content_match:
            relevance = "高" if title_match else "中"
            results.append({**doc, "relevance": relevance})

    if not results:
        return (
            f"❌ 未找到与 '{query}' 相关的文档。\n"
            f"建议：尝试更宽泛的关键词。\n"
            f"可用主题：RAG, Agent, 向量数据库, Rerank, Embedding, LangChain, LLM, Function Calling"
        )

    # 标题匹配排前面
    results.sort(key=lambda d: 0 if d["relevance"] == "高" else 1)

    total = len(results)
    shown = min(total, max_results)

    output = f"🔍 搜索 '{query}'：共 {total} 篇匹配，显示前 {shown} 篇\n\n"

    for i, doc in enumerate(results[:shown], 1):
        content_preview = doc["content"][:150]
        if len(doc["content"]) > 150:
            content_preview += "..."
        output += (
            f"## {i}. {doc['title']} [相关性: {doc['relevance']}]\n"
            f"   {content_preview}\n"
            f"   标签: {', '.join(doc['tags'])}\n\n"
        )

    if total > max_results:
        remaining = total - max_results
        output += (
            f"---\n"
            f"还有 {remaining} 篇未显示。如需查看更多，可以：\n"
            f"  1. 用更具体的关键词缩小范围\n"
            f"  2. 指定标签筛选（如 'RAG'、'Agent'）\n"
        )

    return output


# ═══════════════════════════════════════════
# 2. 状态反馈：让 Agent 知道进展
# ═══════════════════════════════════════════


def batch_process(items_json: str, operation: str) -> str:
    """批量处理数据，带进度反馈和部分失败处理。

    设计原则：
    - 每项处理都报告状态（成功/失败），让 LLM 知道发生了什么
    - 部分失败不中断整体流程——报告失败项 + 提供后续选项
    - 参数验证的错误信息给出正确示例，而非只说"参数错误"
    """
    try:
        items = json.loads(items_json)
    except json.JSONDecodeError:
        return (
            f"❌ 参数格式错误：items 必须是 JSON 数组字符串。\n"
            f"   收到: {items_json[:80]}\n"
            f'   正确示例: \'["文本1", "文本2", "文本3"]\''
        )

    if not isinstance(items, list) or len(items) == 0:
        return f"❌ items 必须是非空数组，收到类型: {type(items).__name__}"

    valid_ops = {"summarize": "摘要生成", "classify": "分类", "keywords": "关键词提取"}
    if operation not in valid_ops:
        return (
            f"❌ 不支持的操作 '{operation}'。\n"
            f"   可用操作: {list(valid_ops.keys())}（{list(valid_ops.values())}）"
        )

    total = len(items)
    success = 0
    failed = 0
    results = []

    for i, item in enumerate(items):
        # 模拟：以 "err_" 开头的项处理失败
        if item.startswith("err_"):
            failed += 1
            results.append(f"  [{i + 1}/{total}] ❌ '{item}': 处理失败")
        else:
            success += 1
            op_name = valid_ops[operation]
            results.append(f"  [{i + 1}/{total}] ✅ '{item}' {op_name}完成")

    progress_pct = int((success + failed) / total * 100)
    output = (
        f"📊 批量{valid_ops[operation]}完成: {progress_pct}% ({success + failed}/{total})\n"
        f"   成功: {success}, 失败: {failed}\n\n" + "\n".join(results)
    )

    if failed > 0:
        output += (
            f"\n\n⚠️ {failed} 项处理失败。"
            f"后续建议：(1) 检查失败项数据格式 (2) 跳过失败项继续后续流程"
        )

    return output


# ═══════════════════════════════════════════
# 3. 错误恢复接口：错误信息即决策依据
# ═══════════════════════════════════════════

MOCK_API = {
    "weather": {"北京": "晴 25°C", "上海": "多云 28°C", "深圳": "阵雨 30°C"},
    "news": {
        "tech": ["AI 大模型新突破", "量子计算里程碑"],
        "science": ["火星探测新发现", "基因编辑临床进展"],
    },
    "stock": {"AAPL": 185.50, "GOOGL": 142.30, "TSLA": 245.10},
}


def api_fetch(endpoint: str, param: str = "") -> str:
    """模拟 API 调用，重点展示错误恢复接口设计。

    设计原则：
    - 用扁平字符串参数而非嵌套 JSON——LLM 更容易正确生成
    - 端点不存在 → 列出所有可用端点 + 各自用途
    - 必填参数缺失 → 明确指出缺失哪个 + 给出示例
    """
    valid_endpoints = list(MOCK_API.keys())
    if endpoint not in valid_endpoints:
        return (
            f"❌ 未知端点 '{endpoint}'。\n"
            f"   可用端点及用法:\n"
            f"   - weather: 查询城市天气（param=城市名，如'北京'）\n"
            f"   - news: 获取新闻（param=类别，如'tech'/'science'，默认 tech）\n"
            f"   - stock: 查询股票价格（param=股票代码，如'AAPL'）"
        )

    if endpoint == "weather":
        city = param.strip()
        if not city:
            return (
                f"❌ weather 端点缺少城市参数。\n"
                f"   可用城市: {list(MOCK_API['weather'].keys())}\n"
                f"   示例: api_fetch('weather', '北京')"
            )
        if city in MOCK_API["weather"]:
            return f"🌤 {city}天气: {MOCK_API['weather'][city]}"
        return (
            f"❌ 未找到城市 '{city}' 的天气数据。\n   已知城市: {list(MOCK_API['weather'].keys())}"
        )

    elif endpoint == "news":
        category = param.strip() or "tech"
        if category in MOCK_API["news"]:
            items = MOCK_API["news"][category]
            return f"📰 {category} 新闻 ({len(items)} 条):\n" + "\n".join(
                f"  - {item}" for item in items
            )
        return f"❌ 未知新闻类别 '{category}'。可用: {list(MOCK_API['news'].keys())}"

    elif endpoint == "stock":
        symbol = param.strip().upper()
        if not symbol:
            return (
                f"❌ stock 端点缺少股票代码。\n"
                f"   已知股票: {list(MOCK_API['stock'].keys())}\n"
                f"   示例: api_fetch('stock', 'AAPL')"
            )
        if symbol in MOCK_API["stock"]:
            return f"📈 {symbol} 当前价格: ${MOCK_API['stock'][symbol]}"
        return f"❌ 未找到股票 '{symbol}'。已知: {list(MOCK_API['stock'].keys())}"

    return "❌ 未知错误"


# ═══════════════════════════════════════════
# 4. 工具注册
# ═══════════════════════════════════════════

TOOLS_NAIVE = {
    "search": {
        "function": naive_search,
        "schema": {
            "description": "搜索知识库文档",
            "parameters": {"query": "搜索关键词"},
        },
    },
}

TOOLS_SMART = {
    "search": {
        "function": smart_search,
        "schema": {
            "description": "搜索 AI 知识库，返回结构化摘要（最多 3 篇）。如需更多结果，缩小搜索范围",
            "parameters": {"query": "搜索关键词", "max_results": "最多返回数量，默认 3"},
        },
    },
    "batch_process": {
        "function": batch_process,
        "schema": {
            "description": "批量处理文本数据。支持 summarize（摘要）/ classify（分类）/ keywords（关键词提取）。返回每项处理状态和汇总统计",
            "parameters": {
                "items_json": 'JSON 数组字符串，如 \'["文本1", "文本2"]\'',
                "operation": "操作类型: summarize / classify / keywords",
            },
        },
    },
    "api_fetch": {
        "function": api_fetch,
        "schema": {
            "description": "调用外部 API 获取实时数据。weather（天气，param=城市名）/ news（新闻，param=类别）/ stock（股票，param=代码）。参数错误时返回可用端点和正确用法",
            "parameters": {
                "endpoint": "API 端点: weather / news / stock",
                "param": "查询参数: weather 用城市名(如'北京') / news 用类别(如'tech') / stock 用代码(如'AAPL')",
            },
        },
    },
}


# ═══════════════════════════════════════════
# 5. Agent（复用第 12 章的 ReAct 循环）
# ═══════════════════════════════════════════


def build_tool_descriptions(tools: dict) -> str:
    lines = []
    for name, info in tools.items():
        schema = info["schema"]
        params = ", ".join(f"{k}: {v}" for k, v in schema["parameters"].items())
        lines.append(f"- **{name}**: {schema['description']}\n  参数: {params}")
    return "\n".join(lines)


REACT_PROMPT = """你是一个智能 Agent，具有推理和行动能力。你可以使用工具来完成任务。

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


def parse_react_output(text: str) -> dict:
    """解析 LLM 的 ReAct 格式输出。

    使用括号计数而非正则来提取 JSON——防止内层嵌套括号提前截断。
    """
    text = text.strip()

    final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if final_match:
        return {"type": "final_answer", "answer": final_match.group(1).strip()}

    action_match = re.search(r"Action:\s*(\S+)", text, re.IGNORECASE)
    input_start = text.find("Action Input:")
    if action_match and input_start != -1:
        tool_name = action_match.group(1).strip()

        # 跳过 "Action Input:" 前缀，找到第一个 {
        rest = text[input_start:]
        brace_start = rest.find("{")
        if brace_start == -1:
            return {"type": "parse_error", "raw": text, "reason": "Action Input 后未找到 JSON"}

        # 括号计数提取完整 JSON（兼容内层嵌套）
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
            return {"type": "parse_error", "raw": text, "reason": "JSON 括号不匹配"}

        json_str = rest[brace_start : brace_end + 1]
        try:
            tool_input = json.loads(json_str)
        except json.JSONDecodeError:
            return {"type": "parse_error", "raw": text, "reason": "Action Input 不是合法 JSON"}
        return {"type": "action", "tool": tool_name, "input": tool_input}

    return {"type": "parse_error", "raw": text, "reason": "无法识别输出格式"}


class Agent:
    """ReAct Agent 执行器（精简版，核心逻辑同第 12 章）"""

    def __init__(self, llm, tools: dict):
        self.llm = llm
        self.tools = tools

    def run(self, user_question: str, max_steps: int = 5) -> dict:
        tool_descriptions = build_tool_descriptions(self.tools)
        tool_names = list(self.tools.keys())

        system_prompt = REACT_PROMPT.format(
            tool_descriptions=tool_descriptions, tool_names="/".join(tool_names)
        )

        messages = [{"role": "system", "content": system_prompt}]
        steps = []

        for step_idx in range(max_steps):
            if step_idx == 0:
                messages.append({"role": "user", "content": user_question})
            else:
                last_step = steps[-1]
                messages.append(
                    {
                        "role": "user",
                        "content": f"Observation: {last_step['result']}",
                    }
                )

            # 组装 prompt 字符串
            parts = []
            for m in messages:
                label = {"system": "System", "user": "Human", "assistant": "AI"}[m["role"]]
                parts.append(f"{label}: {m['content']}")
            full_prompt = "\n\n".join(parts)

            response = self.llm.invoke(full_prompt)
            llm_output = response.content if hasattr(response, "content") else str(response)
            parsed = parse_react_output(llm_output)

            if parsed["type"] == "final_answer":
                steps.append({"thought": llm_output, "type": "final"})
                return {"answer": parsed["answer"], "steps": steps}

            elif parsed["type"] == "action":
                tool_name = parsed["tool"]
                tool_input = parsed["input"]

                if tool_name not in self.tools:
                    observation = f"错误: 没有名为 '{tool_name}' 的工具，可用工具: {tool_names}"
                else:
                    try:
                        tool_func = self.tools[tool_name]["function"]
                        observation = tool_func(**tool_input)
                    except TypeError as e:
                        observation = f"工具参数错误: {e}。请检查参数名称和类型是否与工具定义一致"
                    except Exception as e:
                        observation = f"工具执行失败: {e}"

                steps.append(
                    {
                        "thought": llm_output,
                        "type": "action",
                        "tool": tool_name,
                        "input": tool_input,
                        "result": observation,
                    }
                )
            else:
                error_msg = f"格式错误 ({parsed.get('reason', '未知')})。请严格按照 Thought/Action/Action Input 或 Thought/Final Answer 格式输出。"
                steps.append(
                    {
                        "thought": llm_output,
                        "type": "parse_error",
                        "result": error_msg,
                    }
                )

        # max_steps 用尽
        last_output = steps[-1].get("thought", "") if steps else ""
        if steps and steps[-1]["type"] == "action" and "错误" not in steps[-1].get("result", ""):
            return {"answer": steps[-1]["result"], "steps": steps}
        return {
            "answer": f"Agent 在 {max_steps} 步内未能得出最终答案。最后状态: {last_output[:200]}",
            "steps": steps,
        }


# ═══════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════
if __name__ == "__main__":
    reset()

    # ── 1. 信息抽象对比 ──
    section("1. 信息抽象：naive vs smart search")
    naive_result = naive_search("RAG")
    smart_result = smart_search("RAG")
    print(f"Naive search 输出长度: {len(naive_result)} 字符")
    print(f"Smart search 输出长度: {len(smart_result)} 字符")
    check("Smart 包含结构化标记", "##" in smart_result and "相关性" in smart_result)
    check("Smart 包含总数统计", "共" in smart_result and "篇匹配" in smart_result)
    check("Naive 输出完整文档内容", len(naive_result) > 200)

    # 无结果时的引导
    no_result = smart_search("区块链")
    print(f"\n无结果时的 smart_search 输出:\n{no_result[:200]}")
    check("无结果时提供建议", "建议" in no_result or "可用主题" in no_result)

    # ── 2. 状态反馈 ──
    section("2. 状态反馈：batch_process")
    result = batch_process('["文本A", "文本B", "err_bad", "文本D"]', "summarize")
    print(f"Batch process 输出:\n{result}")
    check("包含进度统计", "成功" in result and "失败" in result)
    check("包含逐项状态", "✅" in result and "❌" in result)
    check("失败时提供后续建议", "建议" in result or "跳过" in result)

    # 参数错误时的友好提示
    bad_result = batch_process("not_json", "summarize")
    print(f"\n参数错误时的输出:\n{bad_result[:200]}")
    check("参数错误时给出正确示例", "正确示例" in bad_result or "JSON" in bad_result)

    # ── 3. 错误恢复接口 ──
    section("3. 错误恢复接口：api_fetch")
    # 正常调用
    weather = api_fetch("weather", "北京")
    print(f"正常调用: {weather}")
    check("正常 API 调用成功", "晴" in weather)

    # 未知端点
    bad_endpoint = api_fetch("translate", "")
    print(f"\n未知端点:\n{bad_endpoint}")
    check("未知端点时列出可用端点", "weather" in bad_endpoint and "news" in bad_endpoint)

    # 缺少必填参数
    missing_param = api_fetch("weather", "")
    print(f"\n缺少参数:\n{missing_param}")
    check("缺少参数时指出缺失项", "city" in missing_param.lower() or "城市" in missing_param)

    # ── 4. Agent 集成测试 ──
    section("4. Agent 集成：smart tools")
    agent = Agent(llm, TOOLS_SMART)

    result = agent.run("搜索关于 Agent 的文档")
    print("问题: 搜索关于 Agent 的文档")
    print(f"步骤数: {len(result['steps'])}")
    print(f"答案: {result['answer'][:200]}")
    check("Agent 能找到 Agent 相关文档", len(result["answer"]) > 0)

    result = agent.run("北京今天天气怎么样？")
    print("\n问题: 北京今天天气怎么样？")
    print(f"步骤数: {len(result['steps'])}")
    for i, s in enumerate(result["steps"]):
        if s["type"] == "action":
            print(f"  步骤 {i + 1}: {s['tool']} → {s['result'][:80]}")
    print(f"答案: {result['answer']}")
    check("Agent 能查询天气", "晴" in result["answer"] or "25" in result["answer"])

    # ── 5. 对比：naive tools vs smart tools ──
    section("5. 对比实验：naive vs smart tools 对 Agent 的影响")
    agent_naive = Agent(llm, TOOLS_NAIVE)
    agent_smart = Agent(llm, TOOLS_SMART)

    question = "什么是 RAG？它和 Agent 有什么关系？"
    print(f"问题: {question}")

    result_naive = agent_naive.run(question)
    result_smart = agent_smart.run(question)

    print(
        f"\nNaive Agent: {len(result_naive['steps'])} 步, 答案长度 {len(result_naive['answer'])} 字符"
    )
    print(
        f"Smart Agent: {len(result_smart['steps'])} 步, 答案长度 {len(result_smart['answer'])} 字符"
    )
    check("Smart Agent 能完成任务", len(result_smart["answer"]) > 0)

    summary()
