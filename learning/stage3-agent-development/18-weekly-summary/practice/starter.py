"""研究助手 Agent — 阶段 3 综合实战

整合能力：
  - FC Agent 循环（ch15）— bind_tools + ToolMessage
  - 工具工程（ch13）— 信息抽象 + 结构化输出 + 状态反馈
  - 双层记忆（ch16）— ShortTermMemory + LongTermMemory
  - 错误反射（ch17）— 三分类 + 结构化反馈 + 降级策略

已提供的模块（可直接 import）：
  - knowledge_base.py  → 知识库文档 + FAISS vectorstore
  - error_handler.py   → 错误分类系统（ErrorCategory / classify_error）
  - memory.py          → 双层记忆（ShortTermMemory / LongTermMemory）

你需要完成的 TODO：
  TODO 1: 实现三个工具函数 + FC JSON Schema
  TODO 2: 实现 FC Agent 循环
  TODO 3: 集成错误反射机制
  TODO 4: 编写 5 个测试场景

运行：
  make run f=learning/stage3-agent-development/18-weekly-summary/practice/starter.py
"""

import json
from dataclasses import asdict

from error_handler import classify_error
from knowledge_base import vectorstore
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from memory import LongTermMemory, ShortTermMemory

from common import get_or_create_llm, load_dotenv_if_needed, reset, summary
from common.check import check, section

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

# ═══════════════════════════════════════════════════════════════
# TODO 1: 实现三个工具函数 + FC JSON Schema
# ═══════════════════════════════════════════════════════════════
#
# 提示：
# - search_knowledge(query, top_k=5): 用 vectorstore.similarity_search() 检索知识库
#   - 信息抽象：只返回前 top_k 条的前 150 字，加序号和来源
#   - 空查询参数校验：返回 {"success": False, "error": "..."}
#   - 空结果给引导："未找到，建议换关键词"
#   - 返回 JSON 字符串
#
# - summarize_text(text, max_words=80): 调用 llm.invoke() 做中文摘要
#   - 空文本参数校验
#   - 超长输入截断到 2000 字符
#   - 返回 JSON 字符串，格式 {"success": True, "summary": llm_response}
#
# - save_note(content, tags=None): 写入 LongTermMemory
#   - 空内容参数校验
#   - 返回 memory_id 和当前记忆总数
#   - 返回 JSON 字符串
#
# TOOLS_SCHEMA: 按 FC 格式定义三个工具的 JSON Schema
#   - type: "function", function: { name, description, parameters }
#   - parameters 用 JSON Schema 格式: type, properties, required


# TODO 1a: 实现 search_knowledge
def search_knowledge(query: str, top_k: int = 5) -> dict:
    """搜索知识库——信息抽象：截断 top_k 条 + 摘要引导。"""
    if not query.strip():
        return {"success": False, "error": "query 不能为空，请提供有效的查询关键词", "category": "parameter_error"}
    try:
        docs = vectorstore.similarity_search(query, k=top_k)
    except Exception as e:
        return {"success": False, "error": f"知识库检索失败: {e}", "category": "retryable"}

    result: dict = {"success": True, "results": [], "summary": "", "count": 0}

    if not docs:
        result["summary"] = "未找到相关文档，建议换个关键词试试。"
        return result

    for i, d in enumerate(docs):
        result_item = {
            "rank": i + 1,
            "content": d.page_content[:150] + "..." if len(d.page_content) > 150 else d.page_content,
        }
        result["results"].append(result_item)

    result["count"] = len(result["results"])
    result["summary"] = f"共找到 {result['count']} 条相关文档。如需更详细的信息，请用 summarize_text 对指定文档做摘要"
    return result


# TODO 1b: 实现 summarize_text
def summarize_text(text: str, max_words: int = 80) -> dict:
    """调用 LLM 做文本摘要——结构化输出。"""
    if not text.strip():
        return {"success": False, "error": "text 不能为空，请提供有效的文本内容", "category": "parameter_error"}
    if len(text) > 2000:
        text = text[:2000]
    try:
        response = llm.invoke(
            [
                SystemMessage(content="你是一个中文文本摘要助手。"),
                HumanMessage(content=f"请对以下文本进行摘要，控制在 {max_words} 个字以内：{text}"),
            ]
        )
        return {"success": True, "summary": response.content}
    except Exception as e:
        return {"success": False, "error": f"文本摘要失败: {e}", "category": "retryable"}


# TODO 1c: 实现 save_note
def save_note(content: str, tags: list[str] | None = None, ltm: LongTermMemory | None = None) -> dict:
    """将关键信息写入长期记忆——状态反馈。"""
    if not content.strip():
        return {"success": False, "error": "content 不能为空，请提供有效的笔记内容", "category": "parameter_error"}
    try:
        if ltm is None:
            ltm = LongTermMemory()
        memory_id = ltm.add(content, tags=tags)
        total_count = len(ltm.store) if ltm.store else 0
        return {"success": True, "memory_id": memory_id, "total_count": total_count}
    except Exception as e:
        return {"success": False, "error": f"笔记保存失败: {e}", "category": "retryable"}


# TODO 1d: 定义 TOOLS_SCHEMA（FC JSON Schema 格式，参考 ch15）
TOOLS_SCHEMA: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "在知识库中搜索相关文档，返回摘要结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "top_k": {"type": "integer", "description": "返回的文档数量，默认为5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": "对输入文本进行摘要，返回摘要结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "需要摘要的文本内容"},
                    "max_words": {"type": "integer", "description": "摘要的最大字数，默认为80"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "将重要信息保存到长期记忆",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "需要保存的笔记内容"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "笔记标签列表，默认为空"},
                },
                "required": ["content"],
            },
        },
    },
]

# 工具名→函数映射表
TOOL_FUNCTIONS = {"search_knowledge": search_knowledge, "summarize_text": summarize_text, "save_note": save_note}

# ═══════════════════════════════════════════════════════════════
# ResearchAssistant Agent
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是一个 AI 研究助手，帮助用户探索和整理知识。

你可以：
- 搜索知识库获取相关文档（search_knowledge）
- 对文本做摘要提取关键信息（summarize_text）
- 将重要发现保存到长期记忆（save_note）

规则：
1. 优先搜索知识库回答问题，而非凭记忆编造
2. 当用户表达偏好或发现重要结论时，主动保存到长期记忆
3. 工具调用失败时，仔细阅读错误信息中的建议，修正参数后重试
4. 多次重试失败后，如实告知用户并建议替代方案
5. 用中文回复"""


def _structured_error(msg: str) -> dict:
    """将 classify_error 返回的 StructuredError 转为 JSON 可序列化的 dict。"""
    err = asdict(classify_error(msg))
    err["category"] = err["category"].value
    return err


class ResearchAssistant:
    """FC 模式的 Agent，集成双层记忆和错误反射。"""

    def __init__(
        self,
        short_term: ShortTermMemory | None = None,
        long_term: LongTermMemory | None = None,
        max_retries: int = 5,
        degradation_threshold: int = 3,
    ):
        self.short_term = short_term or ShortTermMemory()
        self.long_term = long_term or LongTermMemory()
        self.max_retries = max_retries
        self.degradation_threshold = degradation_threshold

    # ═══════════════════════════════════════════════════════════
    # TODO 2: 实现 FC Agent 循环（核心）
    # TODO 3: 集成错误反射（在工具失败分支中）
    # ═══════════════════════════════════════════════════════════
    #
    # 流程：
    # 1. 检索长期记忆 → self.long_term.format_for_prompt(user_input)
    # 2. 构建初始消息 [SystemMessage, ...短期历史, HumanMessage(user_input)]
    # 3. 更新短期记忆 self.short_term.add("user", user_input)
    # 4. 循环 while tool_attempts < self.max_retries:
    #    a. llm.bind_tools(TOOLS_SCHEMA).invoke(messages)
    #    b. 检查 response.tool_calls —— 为空则返回最终答案
    #    c. 遍历 tool_calls，执行对应函数
    #       - save_note 需要额外传入 ltm=self.long_term
    #    d. 解析 JSON 结果，判断 success：
    #       - 成功 → ToolMessage(content=result)，重置 consecutive_failures
    #       - 失败 → 进入错误反射（TODO 3）：
    #         * consecutive_failures += 1
    #         * classify_error(parsed["error"]) → StructuredError
    #         * PERMANENT → 立即 return
    #         * 连续失败 >= degradation_threshold → 降级 return
    #         * RETRYABLE/PARAMETER_ERROR → 构建结构化反馈 ToolMessage
    # 5. 超出 max_retries → 返回降级信息
    # 6. 成功返回最终答案时，更新短期记忆 self.short_term.add("assistant", answer)

    def run(self, user_input: str) -> dict:
        # 检索长期记忆
        long_term_context = self.long_term.format_for_prompt(user_input)

        # 构建初始消息
        system_content = SYSTEM_PROMPT
        if long_term_context:
            system_content += "\n\n" + long_term_context

        messages: list = [SystemMessage(content=system_content)]

        # 注入短期历史
        for m in self.short_term.get_recent(10):
            if m["role"] == "user":
                messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                messages.append(AIMessage(content=m["content"]))

        messages.append(HumanMessage(content=user_input))
        self.short_term.add("user", user_input)

        # TODO 2+3: 实现 FC Agent 循环 + 错误反射
        tool_attempts = 0
        consecutive_failures = 0

        # 你的代码从这里开始...
        # while tool_attempts < self.max_retries:
        #     ...
        while tool_attempts < self.max_retries:
            response = llm.bind_tools(TOOLS_SCHEMA).invoke(messages)
            tool_calls = getattr(response, "tool_calls", [])

            if not tool_calls:
                # 没有工具调用，直接返回答案
                answer = response.content if hasattr(response, "content") else str(response)
                self.short_term.add("assistant", answer)
                return {"success": True, "answer": answer, "attempts": tool_attempts}

            messages.append(response)  # 将 LLM 的工具调用请求记入历史
            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {})
                if tool_name not in TOOL_FUNCTIONS:
                    continue  # 忽略未知工具调用
                try:
                    target_function = TOOL_FUNCTIONS[tool_name]
                    if not callable(target_function):
                        notcallable_msg = json.dumps(
                            {
                                "success": False,
                                "error": _structured_error(f"invalid parameter: {tool_name} 不是一个可调用的函数"),
                            },
                            ensure_ascii=False,
                        )
                        messages.append(ToolMessage(content=notcallable_msg, tool_call_id=call["id"]))
                        continue

                    # save_note 需要注入 ltm，让记忆写入测试可见的 LongTermMemory 实例
                    if tool_name == "save_note":
                        result = target_function(**tool_args, ltm=self.long_term)
                    else:
                        result = target_function(**tool_args)
                    tool_attempts += 1

                    if result.get("success"):
                        messages.append(
                            ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"])
                        )
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        category = result.get("category", "retryable")

                        # PERMANENT: 立即停止
                        if category == "permanent":
                            return {
                                "success": False,
                                "answer": f"遇到永久性错误: {result.get('error', '未知')}",
                                "attempts": tool_attempts,
                            }

                        # 连续失败达到降级阈值
                        if consecutive_failures >= self.degradation_threshold:
                            return {
                                "success": False,
                                "answer": f"已连续 {consecutive_failures} 次工具调用失败，降级停止。最后错误: {result.get('error', '未知')}",
                                "attempts": tool_attempts,
                            }

                        # 错误反馈使用工具自身分类（权威来源），不重新 classify
                        messages.append(
                            ToolMessage(
                                content=json.dumps(
                                    {
                                        "success": False,
                                        "error": {
                                            "category": category,
                                            "summary": result.get("error", "未知错误"),
                                            "suggested_fix": (
                                                "请检查参数后重试"
                                                if category == "parameter_error"
                                                else "操作失败，请重试"
                                            ),
                                        },
                                    },
                                    ensure_ascii=False,
                                ),
                                tool_call_id=call["id"],
                            )
                        )
                except Exception as e:
                    consecutive_failures += 1
                    error_msg = _structured_error(f"running error: 工具 {tool_name} 执行失败: {e}")
                    messages.append(
                        ToolMessage(
                            content=json.dumps({"success": False, "error": error_msg}, ensure_ascii=False),
                            tool_call_id=call["id"],
                        )
                    )

        # 超出 max_retries 降级（while 循环退出后触发）
        return {
            "success": False,
            "answer": f"已进行 {tool_attempts} 次工具调用仍未完成，降级停止。",
            "attempts": tool_attempts,
        }


# ═══════════════════════════════════════════════════════════════
# TODO 4: 编写 5 个测试场景
# ═══════════════════════════════════════════════════════════════
#
# 场景 1: 正常知识检索 —— "什么是 RAG？它和 ReAct 有什么区别？"
#   验证：任务成功，工具调用次数合理
def test_normal_retrieval():
    """场景 1：正常知识检索——"什么是 RAG？它和 ReAct 有什么区别？"""
    reset()
    assistant = ResearchAssistant(
        short_term=ShortTermMemory(), long_term=LongTermMemory(), max_retries=5, degradation_threshold=3
    )
    section("场景 1：正常知识检索")
    result = assistant.run("什么是 RAG？它和 ReAct 有什么区别？")
    print(f"Agent 回答: {result['answer']}")
    print(f"工具调用次数: {result['attempts']}")
    check("任务成功", result["success"])
    check("使用了工具", result["attempts"] > 0)
    summary()


#
# 场景 2: 参数错误 —— 空查询触发 PARAMETER_ERROR
#   验证：Agent 未崩溃，未无限循环
def test_empty_query():
    """场景 2：参数错误——空查询触发 PARAMETER_ERROR 反馈。"""
    reset()
    assistant = ResearchAssistant(short_term=ShortTermMemory(), long_term=LongTermMemory())

    section("场景 2：参数错误 — 空查询")
    result = assistant.run("测试一下空查询触发参数错误: search_knowledge 的 query 传空字符串")
    print(f"Agent 回答: {result['answer']}")
    print(f"工具调用次数: {result['attempts']}")
    check("未崩溃", "answer" in result)
    summary()


#
# 场景 3: 长期记忆 —— 保存偏好后下一轮验证被回忆
#   验证：偏好被写入长期记忆，第二轮被注入 prompt
def test_memory_persistence():
    """场景 3：长期记忆——保存偏好后能在后续查询中回忆。"""
    reset()
    ltm = LongTermMemory()
    assistant = ResearchAssistant(short_term=ShortTermMemory(), long_term=ltm)

    section("场景 3：长期记忆 — 保存偏好")
    result1 = assistant.run("记住：我最关注的是 RAG 和 ReAct 相关的内容，我喜欢用表格对比的方式呈现信息")
    print(f"第一轮: {result1['answer']}")
    check("第一轮成功", result1["success"])

    result2 = assistant.run("推荐一些我可能感兴趣的技术话题")
    print(f"第二轮: {result2['answer']}")
    check("第二轮成功", result2["success"])
    check("长期记忆已写入", len(ltm.store) >= 1)
    summary()


#
# 场景 4: 多工具协作 —— 搜索后做摘要
#   验证：使用了 2+ 个工具调用
def test_summarize():
    """场景 4：文本摘要——调用 LLM 对搜索结果做摘要。"""
    reset()
    assistant = ResearchAssistant(short_term=ShortTermMemory(), long_term=LongTermMemory(), max_retries=3)

    section("场景 4：文本摘要")
    result = assistant.run("帮我搜索 Agent Memory 的内容，然后对找到的结果做一个摘要")
    print(f"Agent 回答: {result['answer'][:300]}...")
    print(f"工具调用次数: {result['attempts']}")
    check("任务成功", result["success"])
    check("使用了多个工具", result["attempts"] >= 2)
    summary()


#
# 场景 5: 降级策略 —— 连续失败后停止循环
#   验证：降级阈值触发，未超出 max_retries
#
# 每个场景用 section() 包裹，用 check() 做断言，最后 summary()


def test_degradation():
    """场景 5：降级策略——连续参数错误后停止循环。"""
    reset()
    assistant = ResearchAssistant(
        short_term=ShortTermMemory(), long_term=LongTermMemory(), max_retries=5, degradation_threshold=3
    )

    section("场景 5：降级策略")
    result = assistant.run("帮我保存一个空的笔记，然后搜索空内容，最后再试一次空摘要——重复直到你放弃")
    print(f"Agent 回答: {result['answer']}")
    print(f"工具调用次数: {result['attempts']}")
    check("Agent 未无限循环", result["attempts"] <= 5)
    summary()


if __name__ == "__main__":
    # TODO 4: 编写测试代码
    reset()
    print("TODO: 实现 5 个测试场景")
    test_normal_retrieval()
    test_empty_query()  # 重复测试稳定性
    test_memory_persistence()
    test_summarize()
    test_degradation()
    summary()
