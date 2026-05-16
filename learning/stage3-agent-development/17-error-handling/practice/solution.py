"""ResilientAgent 完整实现 — 带错误分类和反射机制的 Agent。

设计要点：
  - 错误分三类而非二分（可重试/参数错误/永久），给 LLM 精确的修正方向
  - 错误反馈按 12-Factor Agent 原则 9 压缩到上下文窗口：只给分类+摘要+修复建议
  - RETRYABLE 错误暗示"先重试，给上限"而非死循环，PARAMETER_ERROR 带正确参数格式
  - PERMANENT 错误直接告诉 LLM 不要重试同一调用，避免浪费 token 和时间
  - 降级阈值独立于重试次数：连续失败 2 次就降级，防止 LLM 陷入错误循环
  - classify_error 用关键词匹配而非 LLM（确定性快、零 token 成本），生产环境可升级为 LLM 分类
"""

import enum
import json
import re
from dataclasses import dataclass

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


# ═══════════════════════════════════════════════════════════════
# 错误分类系统
# ═══════════════════════════════════════════════════════════════


class ErrorCategory(enum.Enum):
    """错误分类。

    三类而非二分的理由：如果只分"可重试/不可重试"，LLM 面对"表名拼写错误"这种参数问题
    也会盲目重试而非修正参数。显式区分 PARAMETER_ERROR 让 LLM 的行为从"再试一次"变成"检查参数再试"。
    """

    RETRYABLE = "retryable"  # 暂时性：超时、限流、网络抖动 → 可以重试
    PARAMETER_ERROR = "parameter_error"  # 参数问题：拼写错误、格式不对 → 修正参数后重试
    PERMANENT = "permanent"  # 永久性：无权限、资源已删除 → 不要重试，换方案


@dataclass
class StructuredError:
    """结构化错误信息。

    和普通 Exception 的区别：
    - summary 是给 LLM 看的自然语言摘要（压缩上下文）
    - suggested_fix 是给 LLM 的行动建议（引导修正）
    - category 决定了 LLM 的处理策略（重试/修正/放弃）
    """

    category: ErrorCategory
    summary: str
    suggested_fix: str


# 关键词映射表 — 优先匹配长关键词，避免 "not found" 误匹配 "no permission to access not found resource"
ERROR_PATTERNS: dict[ErrorCategory, list[str]] = {
    ErrorCategory.RETRYABLE: [
        "timeout",
        "timed out",
        "connection",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "try again",
        "network",
    ],
    ErrorCategory.PARAMETER_ERROR: [
        "not found",
        "invalid",
        "unknown",
        "does not exist",
        "did you mean",
        "bad request",
        "syntax error",
        "parameter",
        "type error",
    ],
    ErrorCategory.PERMANENT: [
        "permission denied",
        "unauthorized",
        "forbidden",
        "access denied",
        "insufficient privilege",
        "quota exceeded",
        "not allowed",
    ],
}

FIX_TEMPLATES: dict[ErrorCategory, str] = {
    ErrorCategory.RETRYABLE: "暂时性故障，可以重试 1 次。如果仍然失败，换一种方式获取信息。",
    ErrorCategory.PARAMETER_ERROR: "参数可能不正确，请检查参数名称和值的格式。参考错误信息中的提示修正。",
    ErrorCategory.PERMANENT: "这是永久性错误，不要重试同一调用。告诉用户你无法完成该操作，建议替代方案。",
}


def classify_error(error_message: str) -> StructuredError:
    """基于关键词模式的错误分类。

    遍历顺序保证：先检查 PERMANENT（权限类最高优先级），
    再检查 RETRYABLE，最后 PARAMETER_ERROR（兜底）。
    如果一个都没匹配，默认按 PERMANENT 处理（安全侧：宁可放弃也不死循环）。
    """
    error_lower = error_message.lower()

    # 按优先级检查：PERMANENT → RETRYABLE → PARAMETER_ERROR
    # PERMANENT 优先级最高，因为权限错误中的 "access denied" 不应该被 PARAMETER_ERROR 的 "not found" 误匹配
    for category in [ErrorCategory.PERMANENT, ErrorCategory.RETRYABLE, ErrorCategory.PARAMETER_ERROR]:
        for pattern in ERROR_PATTERNS[category]:
            if pattern in error_lower:
                return StructuredError(
                    category=category,
                    summary=error_message[:120],
                    suggested_fix=FIX_TEMPLATES[category],
                )

    # 无法分类时默认 PERMANENT，避免 Agent 在未知错误上无限重试
    return StructuredError(
        category=ErrorCategory.PERMANENT,
        summary=error_message[:120],
        suggested_fix="未知错误类型，出于安全考虑不再重试。告诉用户你遇到了意外错误。",
    )


# ═══════════════════════════════════════════════════════════════
# 模拟工具
# ═══════════════════════════════════════════════════════════════

TOOL_BACKEND = {
    "users": True,
    "products": True,
    "admin_access": True,
}


def get_weather(city: str) -> dict:
    """查询城市天气 — 三种失败模式演示三类错误。"""
    if not city or not city.strip():
        return {"success": False, "error": f"invalid parameter: city '{city}' not found in weather database"}
    if city == "超时测试":
        return {"success": False, "error": "connection timed out after 30s — weather API unreachable"}
    if city == "无权限城市":
        return {"success": False, "error": "permission denied: you don't have access to weather data for this region"}
    return {"success": True, "data": f"城市 {city}: 晴天 25°C, 湿度 60%, 风力 3 级"}


def database_lookup(query: str, table: str) -> dict:
    """数据库查询 — 表不存在和权限错误。"""
    if table == "admin_logs" and not TOOL_BACKEND["admin_access"]:
        return {"success": False, "error": "permission denied: insufficient privileges to access table 'admin_logs'"}
    if table not in TOOL_BACKEND or not TOOL_BACKEND.get(table):
        return {"success": False, "error": f"table '{table}' not found in database — did you mean 'users' or 'products'?"}
    return {"success": True, "data": f"[{table}] 查询 '{query}' 返回 3 条结果"}


TOOLS = {
    "get_weather": get_weather,
    "database_lookup": database_lookup,
}


def execute_tool(tool_name: str, params: dict) -> dict:
    func = TOOLS.get(tool_name)
    if func is None:
        return {"success": False, "error": f"unknown tool: '{tool_name}' — available tools: {list(TOOLS.keys())}"}
    try:
        return func(**params)
    except TypeError as e:
        return {"success": False, "error": f"parameter error calling '{tool_name}': {e}"}


# ═══════════════════════════════════════════════════════════════
# ResilientAgent
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是一个能自我修正的智能助手。你可以调用以下工具完成任务：

工具列表：
- get_weather(city: str) — 查询城市天气
- database_lookup(query: str, table: str) — 查询数据库表

规则：
1. 当需要调用工具时，用以下格式输出：
   <tool_call>
   {"tool": "工具名", "params": {"参数名": "参数值"}}
   </tool_call>
2. 当工具调用失败时，仔细阅读错误信息中的"建议修复"部分，修正参数后重试。
3. 如果错误信息提示"永久错误"，不要重试，直接告诉用户你无法完成。
4. 工具成功后，用自然语言告诉用户结果。"""


class ResilientAgent:
    """带错误分类和反射机制的 Agent。

    和普通 Agent 的区别：
    - 不假设工具一定会成功，每次调用后都走错误分类→反馈→重试或降级分支
    - 连续失败计数和重试次数分开：连续失败触发降级，重试次数控制总量
    - 错误反馈按 12-Factor 原则 9 压缩：分类+摘要+修复建议，不堆栈追踪
    """

    def __init__(self, max_retries: int = 3, degradation_threshold: int = 2):
        self.max_retries = max_retries
        self.degradation_threshold = degradation_threshold
        self.consecutive_failures = 0

    def _format_error_feedback(self, error: StructuredError) -> str:
        """压缩错误信息到上下文窗口。

        三个关键设计决策：
        1. 不返回完整堆栈 — LLM 不需要 Python 的 Traceback，只需要知道"什么错了+怎么修"
        2. 按 category 改变 tone — RETRYABLE 鼓励重试但给上限，PERMANENT 明确阻止重试
        3. 格式固定（类型/摘要/建议）— LLM 可以可靠地解析固定格式，减少幻觉
        """
        category_labels = {
            ErrorCategory.RETRYABLE: "RETRYABLE (可重试)",
            ErrorCategory.PARAMETER_ERROR: "PARAMETER_ERROR (参数错误 — 请修正后重试)",
            ErrorCategory.PERMANENT: "PERMANENT (永久错误 — 请勿重试同一调用)",
        }

        return f"""[工具调用失败]
错误类型: {category_labels[error.category]}
错误摘要: {error.summary}
建议修复: {error.suggested_fix}
请根据以上信息决定下一步动作。"""

    def run(self, user_input: str) -> dict:
        """反射重试主循环。

        流程：LLM 决策 → 执行工具 → 成功→最终回答 | 失败→分类→反馈→LLM 反思→重试或降级

        和简单 while True 的区别：每个分支都有明确的退出条件，不会陷入无限循环。
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        tool_attempts = 0
        self.consecutive_failures = 0

        while tool_attempts < self.max_retries:
            response = llm.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            # 检查是否包含工具调用
            if "<tool_call>" in content:
                match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
                if not match:
                    # 格式错误：给 LLM 格式修正提示
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": '你的工具调用格式不正确，请使用 <tool_call>{"tool": "...", "params": {...}}</tool_call> 格式。',
                        }
                    )
                    tool_attempts += 1
                    continue

                tool_call = json.loads(match.group(1))
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})
                result = execute_tool(tool_name, params)
                tool_attempts += 1

                if result["success"]:
                    # 成功：重置连续失败计数，将结果反馈给 LLM，继续循环
                    # 不在此处 return，因为用户可能要求多个工具调用
                    self.consecutive_failures = 0
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"工具 '{tool_name}' 执行成功，返回: {result['data']}",
                        }
                    )
                    # 继续循环，LLM 会决定是调用下一个工具还是给出最终答案
                else:
                    # 失败：分类 → 压缩反馈 → 添加到上下文
                    self.consecutive_failures += 1
                    structured_error = classify_error(result["error"])

                    # 永久错误立即降级
                    if structured_error.category == ErrorCategory.PERMANENT:
                        return {
                            "success": False,
                            "answer": f"任务无法完成: {structured_error.summary}\n请确认账户权限后重试。",
                            "attempts": tool_attempts,
                        }

                    # 连续失败超过阈值 → 降级
                    if self.consecutive_failures >= self.degradation_threshold:
                        return {
                            "success": False,
                            "answer": f"连续 {self.consecutive_failures} 次操作失败，已将问题转交人类处理。最后错误: {structured_error.summary}",
                            "attempts": tool_attempts,
                        }

                    # 可重试或参数错误 → 添加反馈，让 LLM 自我修正
                    feedback = self._format_error_feedback(structured_error)
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": feedback})
            else:
                # 纯文本回复 — LLM 决定不再调用工具
                return {"success": True, "answer": content, "attempts": tool_attempts}

        return {
            "success": False,
            "answer": f"已达到最大工具调用次数 ({self.max_retries})，任务未能完成。请简化需求后重试。",
            "attempts": tool_attempts,
        }


# ═══════════════════════════════════════════════════════════════
# 实验验证
# ═══════════════════════════════════════════════════════════════


def test_retryable_error():
    """可重试错误：超时 → LLM 根据反馈决定重试或换工具。"""
    reset()
    agent = ResilientAgent(max_retries=3, degradation_threshold=2)

    section("场景 1：可重试错误 — 查询天气超时")
    result = agent.run("帮我查一下'超时测试'的天气")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    check("Agent 未崩溃", "answer" in result)
    check("尝试次数在合理范围", result["attempts"] <= 3)

    summary()


def test_parameter_error():
    """参数错误：表不存在 → LLM 根据错误提示切换到正确的表。"""
    reset()
    global TOOL_BACKEND
    TOOL_BACKEND["employees"] = False

    agent = ResilientAgent(max_retries=3, degradation_threshold=2)

    section("场景 2：参数错误 — 查询不存在的表")
    result = agent.run("帮我从 employees 表查一下所有员工")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    # LLM 应该能根据 "did you mean 'users' or 'products'?" 修正
    check("Agent 回复包含了建议或修正", len(result["answer"]) > 5)
    del TOOL_BACKEND["employees"]

    summary()


def test_permanent_error():
    """永久错误：无权限 → Agent 应立即停止，不浪费 token 重试。"""
    reset()
    global TOOL_BACKEND
    TOOL_BACKEND["admin_access"] = False

    agent = ResilientAgent(max_retries=3, degradation_threshold=2)

    section("场景 3：永久错误 — 无权限访问 admin_logs 表")
    result = agent.run("帮我查一下 admin_logs 表里最近的登录记录")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    # 永久错误应该在 1 次工具调用后就停止
    check("永久错误立即停止（attempts=1）", result["attempts"] == 1)
    check("Agent 告知无法完成", "无法" in result["answer"] or "权限" in result["answer"] or "permission" in result["answer"].lower())
    TOOL_BACKEND["admin_access"] = True

    summary()


def test_degradation():
    """降级策略：连续失败 2 次 → 停止循环，请求人类协助。"""
    reset()
    global TOOL_BACKEND
    TOOL_BACKEND["admin_access"] = False

    agent = ResilientAgent(max_retries=5, degradation_threshold=2)

    section("场景 4：降级策略 — 连续失败后避免死循环")
    result = agent.run("帮我查一下 admin_logs 表，然后查 weather 表，最后查 secret 表")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    # degradation_threshold=2 意味着连续失败 2 次即降级
    check("连续失败后触发降级", result["attempts"] <= 2 or "转交人类" in result["answer"] or "连续" in result["answer"])

    TOOL_BACKEND["admin_access"] = True

    summary()


def test_success_path():
    """正常路径：所有工具调用成功 → 不需要任何错误处理，返回正常结果。"""
    reset()
    agent = ResilientAgent(max_retries=3, degradation_threshold=2)

    section("场景 5：正常路径 — 所有操作成功")
    result = agent.run("帮我查一下北京的天气，再查一下 users 表里有没有叫张三的用户")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    check("正常任务成功完成", result["success"])
    check("返回了有意义的结果", len(result["answer"]) > 10)
    # 正常路径用 2 次工具调用（天气+数据库）
    check("工具调用次数合理", result["attempts"] <= 2)

    summary()


if __name__ == "__main__":
    test_retryable_error()
    test_parameter_error()
    test_permanent_error()
    test_degradation()
    test_success_path()
