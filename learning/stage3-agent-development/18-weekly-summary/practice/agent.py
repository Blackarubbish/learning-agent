"""研究助手 Agent（ch12 + ch15 + ch16 + ch17 整合）。

FC 模式的 Agent 循环，集成双层记忆和错误反射机制。

架构：
  用户输入
    → [长期记忆检索] 从 FAISS 检索相关偏好
    → [短期记忆注入] 加载最近对话历史
    → [FC Agent 循环]
        ├── search_knowledge → 向量检索知识库
        ├── summarize_text    → LLM 摘要
        ├── save_note         → 写入长期记忆
        └── 失败 → 错误分类 → 反馈 → 重试/降级
    → [更新短期记忆]
    → 最终答案
"""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from error_handler import ErrorCategory, classify_error
from knowledge_base import vectorstore
from memory import LongTermMemory, ShortTermMemory
from tools import TOOLS_SCHEMA, save_note, search_knowledge, summarize_text

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


class ResearchAssistant:
    """FC 模式 Agent，集成双层记忆和错误反射。

    与 SimpleAgent（ch12）的区别：
    - 用 bind_tools 替代文本解析工具调用（ch15）
    - 每轮注入记忆上下文（ch16）
    - 工具失败时走分类→反馈→重试或降级分支（ch17）
    """

    def __init__(
        self,
        llm,
        short_term: ShortTermMemory | None = None,
        long_term: LongTermMemory | None = None,
        max_retries: int = 5,
        degradation_threshold: int = 3,
    ):
        self.llm = llm
        self.short_term = short_term or ShortTermMemory()
        self.long_term = long_term or LongTermMemory()
        self.max_retries = max_retries
        self.degradation_threshold = degradation_threshold

    def _execute_tool(self, name: str, params: dict) -> str:
        """工具执行适配器 — 将模块函数签名适配到 Agent 的依赖注入。

        模块中的工具函数需要额外参数（vectorstore/llm/ltm），
        此方法完成依赖绑定，对外暴露统一的 (name, params) → JSON 接口。
        """
        try:
            if name == "search_knowledge":
                return search_knowledge(query=params.get("query", ""), vectorstore=vectorstore, top_k=params.get("top_k", 5))
            elif name == "summarize_text":
                return summarize_text(text=params.get("text", ""), llm=self.llm, max_words=params.get("max_words", 80))
            elif name == "save_note":
                return save_note(content=params.get("content", ""), ltm=self.long_term, tags=params.get("tags"))
            else:
                return json.dumps({"success": False, "error": f"unknown tool: '{name}'"})
        except TypeError as e:
            return json.dumps({"success": False, "error": f"parameter error calling '{name}': {e}"})

    def run(self, user_input: str) -> dict:
        # 1. 检索长期记忆
        long_term_context = self.long_term.format_for_prompt(user_input)

        # 2. 构建初始消息
        system_content = SYSTEM_PROMPT
        if long_term_context:
            system_content += "\n\n" + long_term_context

        messages: list = [SystemMessage(content=system_content)]

        for m in self.short_term.get_recent(10):
            if m["role"] == "user":
                messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                messages.append(AIMessage(content=m["content"]))

        messages.append(HumanMessage(content=user_input))
        self.short_term.add("user", user_input)

        # 3. FC Agent 循环 + 错误反射
        tool_attempts = 0
        consecutive_failures = 0

        while tool_attempts < self.max_retries:
            llm_with_tools = self.llm.bind_tools(TOOLS_SCHEMA)
            response = llm_with_tools.invoke(messages)

            tool_calls = response.tool_calls if hasattr(response, "tool_calls") and response.tool_calls else []

            if not tool_calls:
                answer = response.content if hasattr(response, "content") else str(response)
                self.short_term.add("assistant", answer)
                return {"success": True, "answer": answer, "attempts": tool_attempts}

            messages.append(response)
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                params = tc.get("args", {})
                tool_attempts += 1

                result = self._execute_tool(tool_name, params)
                parsed = json.loads(result) if isinstance(result, str) else result

                if parsed.get("success"):
                    consecutive_failures = 0
                    messages.append(ToolMessage(content=result, tool_call_id=tc.get("id", "")))
                else:
                    consecutive_failures += 1
                    error = classify_error(parsed.get("error", ""))

                    if error.category == ErrorCategory.PERMANENT:
                        return {"success": False, "answer": f"任务无法完成: {error.summary}", "attempts": tool_attempts}

                    if consecutive_failures >= self.degradation_threshold:
                        return {
                            "success": False,
                            "answer": f"连续 {consecutive_failures} 次操作失败，已将问题转交人类处理。最后错误: {error.summary}",
                            "attempts": tool_attempts,
                        }

                    category_labels = {
                        ErrorCategory.RETRYABLE: "RETRYABLE (可重试)",
                        ErrorCategory.PARAMETER_ERROR: "PARAMETER_ERROR (参数错误 — 请修正后重试)",
                        ErrorCategory.PERMANENT: "PERMANENT (永久错误)",
                    }
                    feedback = (
                        f"[工具调用失败]\n"
                        f"工具: {tool_name}\n"
                        f"错误类型: {category_labels[error.category]}\n"
                        f"错误摘要: {error.summary}\n"
                        f"建议修复: {error.suggested_fix}\n"
                        f"请根据以上信息决定下一步动作。"
                    )
                    messages.append(ToolMessage(content=feedback, tool_call_id=tc.get("id", "")))

        return {
            "success": False,
            "answer": f"已达到最大工具调用次数 ({self.max_retries})，任务未能完成。请简化需求后重试。",
            "attempts": tool_attempts,
        }
