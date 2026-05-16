"""ResilientAgent — 带错误处理和反思机制的 Agent。

TODO 清单:
  1. ErrorCategory — 定义错误分类枚举（RETRYABLE / PARAMETER_ERROR / PERMANENT）
  2. StructuredError — 创建结构化错误 dataclass（category + summary + suggested_fix）
  3. classify_error() — 基于关键词的错误分类器
  4. ResilientAgent._format_error_feedback() — 压缩错误信息到上下文窗口
  5. ResilientAgent.run() — 实现反射重试主循环
"""

import enum
from dataclasses import dataclass

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


# ═══════════════════════════════════════════════════════════════
# TODO 1: ErrorCategory — 错误分类枚举
# ═══════════════════════════════════════════════════════════════


# TODO 1a: 定义 ErrorCategory 枚举，包含三类错误
#   - RETRYABLE: 可重试（超时、限流、网络抖动）
#   - PARAMETER_ERROR: 参数错误（表名不对、格式错误）
#   - PERMANENT: 永久错误（无权限、资源不存在且不可恢复）
class ErrorCategory(enum.Enum):
    RETRYABLE = "retryable"
    PARAMETER_ERROR = "parameter_error"
    PERMANENT = "permanent"


# ═══════════════════════════════════════════════════════════════
# TODO 2: StructuredError — 结构化错误信息
# ═══════════════════════════════════════════════════════════════


# TODO 2a: 用 dataclass 定义 StructuredError
#   三个字段：category (ErrorCategory), summary (一句话描述), suggested_fix (给 LLM 的修复建议)
#   提示：错误信息需要同时适合人类阅读和 LLM 理解，所以 suggested_fix 要用自然语言
@dataclass
class StructuredError:
    category: ErrorCategory
    summary: str
    suggested_fix: str


# ═══════════════════════════════════════════════════════════════
# TODO 3: classify_error() — 错误分类器
# ═══════════════════════════════════════════════════════════════

# 提示：实际生产环境中可以用 LLM 做分类，这里用关键词匹配演示思路

# TODO 3a: 定义关键词到分类的映射
ERROR_PATTERNS: dict[ErrorCategory, list[str]] = {
    # TODO: 为每个 ErrorCategory 填写匹配关键词
    # ErrorCategory.RETRYABLE: ["timeout", ...]
    # ErrorCategory.PARAMETER_ERROR: ["not found", "invalid", ...]
    # ErrorCategory.PERMANENT: ["permission", "unauthorized", ...]
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

# TODO 3b: 定义每种分类的修复建议模板
FIX_TEMPLATES: dict[ErrorCategory, str] = {
    ErrorCategory.RETRYABLE: "暂时性故障，可以重试 1 次。如果仍然失败，换一种方式获取信息。",
    ErrorCategory.PARAMETER_ERROR: "参数可能不正确，请检查参数名称和值的格式。参考错误信息中的提示修正。",
    ErrorCategory.PERMANENT: "这是永久性错误，不要重试同一调用。告诉用户你无法完成该操作，建议替代方案。",
}


def classify_error(error_message: str) -> StructuredError:
    """根据错误信息文本，返回结构化的错误分类。

    Args:
        error_message: 工具返回的原始错误信息

    Returns:
        StructuredError: 包含分类、摘要和修复建议
    """
    error_lower = error_message.lower()

    # TODO 3c: 遍历 ERROR_PATTERNS，匹配关键词，确定 category
    category = ErrorCategory.PERMANENT  # 默认为永久错误

    for cat, patterns in ERROR_PATTERNS.items():
        for pat in patterns:
            # print(f"__Checking if pattern '{pat}' is in error message: {error_message}.")
            if pat in error_lower:
                category = cat
                break
        if category != ErrorCategory.PERMANENT:
            break

    # print(f"__Classifying error message: '{error_message}' as category: {category}")

    # TODO 3d: 从 FIX_TEMPLATES 获取对应的修复建议
    suggested_fix = FIX_TEMPLATES.get(category, "请检查错误信息并尝试修正。")

    return StructuredError(
        category=category,
        summary=error_message[:100],  # 截取前 100 字符作为摘要
        suggested_fix=suggested_fix,
    )


# ═══════════════════════════════════════════════════════════════
# 模拟工具 — 展示不同失败模式
# ═══════════════════════════════════════════════════════════════

# 模拟的工具执行环境，你可以通过 key 控制工具的执行结果
TOOL_BACKEND = {
    "users": True,
    "products": True,
    "admin_access": True,
}


def get_weather(city: str) -> dict:
    """模拟天气查询工具 — 三种失败模式。

    - city 为空时返回参数错误
    - city 为 "超时测试" 时模拟超时
    - city 为 "无权限城市" 时模拟权限错误
    """
    if not city or not city.strip():
        return {
            "success": False,
            "error": f"invalid parameter: city '{city}' not found in weather database",
        }
    if city == "超时测试":
        return {"success": False, "error": "connection timed out after 30s — weather API unreachable"}
    if city == "无权限城市":
        return {"success": False, "error": "permission denied: you don't have access to weather data for this region"}
    return {"success": True, "data": f"城市 {city}: 晴天 25°C, 湿度 60%, 风力 3 级"}


def database_lookup(query: str, table: str) -> dict:
    """模拟数据库查询工具 — 表不存在 / 权限错误。

    - table 在 TOOL_BACKEND 中标记为 False 时返回"表不存在"
    - table 为 "admin_logs" 且 admin_access=False 时返回权限错误
    """
    if table == "admin_logs" and not TOOL_BACKEND["admin_access"]:
        return {"success": False, "error": "permission denied: insufficient privileges to access table 'admin_logs'"}
    if table not in TOOL_BACKEND or not TOOL_BACKEND.get(table):
        return {
            "success": False,
            "error": f"table '{table}' not found in database — did you mean 'users' or 'products'?",
        }
    return {"success": True, "data": f"[{table}] 查询 '{query}' 返回 3 条结果"}


# 工具注册表
TOOLS = {
    "get_weather": get_weather,
    "database_lookup": database_lookup,
}


def execute_tool(tool_name: str, params: dict) -> dict:
    """执行工具调用，统一返回 {"success": bool, "data": str | None, "error": str | None}"""
    func = TOOLS.get(tool_name)
    if func is None:
        return {"success": False, "error": f"unknown tool: '{tool_name}' — available tools: {list(TOOLS.keys())}"}
    try:
        return func(**params)
    except TypeError as e:
        return {"success": False, "error": f"parameter error calling '{tool_name}': {e}"}


# ═══════════════════════════════════════════════════════════════
# TODO 4: ResilientAgent — 带反射机制的 Agent
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
    """带错误分类和反射重试的 Agent。

    核心流程：
    LLM 决策 → 执行工具 → 成功则返回 → 失败则分类 → 压缩反馈 → LLM 反思 → 重试或降级
    """

    def __init__(self, max_retries: int = 3, degradation_threshold: int = 2):
        self.max_retries = max_retries
        self.degradation_threshold = degradation_threshold
        self.consecutive_failures = 0

    # TODO 4a: _format_error_feedback — 将错误压缩为 LLM 可用的紧凑反馈
    def _format_error_feedback(self, error: StructuredError) -> str:
        """将结构化错误压缩为一段 LLM 可直接理解的反馈文本。

        12-Factor Agent 原则 9：错误信息应该结构化并适合上下文窗口。
        既要给够信息让 LLM 修正，又不能浪费 token。

        返回格式示例：
          [工具调用失败]
          错误类型: RETRYABLE
          摘要: connection timed out after 30s
          建议修复: 等待 5 秒后重试。如果重试 2 次仍然超时，尝试换个相关的工具。

        提示：根据 error.category 调整 tone：
        - RETRYABLE: 建议先重试，但给上限
        - PARAMETER_ERROR: 指明哪些参数可能有问题，给出正确的参数格式
        - PERMANENT: 直接告诉 LLM 不要重试，换个方案
        """
        # TODO: 根据 error.category 构造不同风格的错误反馈
        hints = {
            ErrorCategory.RETRYABLE: "这可能是暂时性问题",
            ErrorCategory.PARAMETER_ERROR: "检查调用参数是否正确",
            ErrorCategory.PERMANENT: "这是永久性错误，不要重试同一调用",
        }
        promt_template = f"""[工具调用失败]
错误类型: {error.category.value}
摘要: {error.summary}
建议修复: {error.suggested_fix} ({hints.get(error.category, "")})
"""
        # print(f"__Generated error feedback for LLM:\n{promt_template}")
        return promt_template

    # TODO 4b: run() — 反射重试主循环
    def run(self, user_input: str) -> dict:
        """运行 Agent 主循环，返回 {"success": bool, "answer": str, "attempts": int}。

        流程：
        1. 构建初始消息（system + user）
        2. 循环调用 LLM
        3. 解析 LLM 输出：如果有 <tool_call>，执行工具
        4. 工具成功 → 将结果反馈给 LLM 生成最终答案
        5. 工具失败 → classify_error → _format_error_feedback → 追加到消息 → 继续循环
        6. 连续失败达到阈值 → 降级，返回"请人类协助"
        7. 超过 max_retries → 降级

        提示：LLM 的回复可能有两种格式：
        - 包含 <tool_call>...</tool_call> 的 JSON 工具调用
        - 纯文本最终答案（当 LLM 不需要再调用工具时）
        """
        import json

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        tool_attempts = 0
        self.consecutive_failures = 0

        while tool_attempts < self.max_retries:
            # TODO 4b-i: 调用 LLM
            response = llm.invoke(messages)

            content = response.content if hasattr(response, "content") else str(response)

            # TODO 4b-ii: 检查是否包含工具调用
            if "<tool_call>" in content:
                # 提取 JSON
                import re

                match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
                if not match:
                    # LLM 格式错误，给一个错误反馈让它修正
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": '工具调用格式不正确，请使用 <tool_call>{"tool": "..."}</tool_call> 格式',
                        }
                    )
                    tool_attempts += 1
                    continue

                tool_call = json.loads(match.group(1))
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})

                # 执行工具
                result = execute_tool(tool_name, params)
                # print(f"__Executed tool '{tool_name}' with params {params}, got result: {result}")
                tool_attempts += 1

                if result["success"]:
                    # 工具成功：反馈数据，继续循环
                    # 不 return，因为用户可能要求多个工具调用
                    self.consecutive_failures = 0
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"工具 '{tool_name}' 成功: {result['data']}",
                        }
                    )
                    # 继续循环，LLM 决定调用下一个工具还是给出最终答案
                else:
                    # 工具失败：分类 + 压缩反馈
                    self.consecutive_failures += 1
                    structured_error = classify_error(result["error"])

                    # print(f"__Classified error: {structured_error}")

                    # TODO 4b-iii: 检查是否需要立即降级（永久错误或连续失败超阈值）
                    if structured_error.category == ErrorCategory.PERMANENT:
                        messages.append({"role": "assistant", "content": content})
                        premanent_hint = (
                            f"工具调用失败: {structured_error.summary}, 建议:{structured_error.suggested_fix}"
                        )
                        messages.append({"role": "assistant", "content": premanent_hint})
                    if structured_error.category == ErrorCategory.RETRYABLE:
                        # 可重试错误，给出提示但继续重试
                        messages.append({"role": "assistant", "content": content})
                        retry_content = (
                            f"工具调用失败: {structured_error.summary} 建议:{structured_error.suggested_fix}"
                        )
                        messages.append({"role": "assistant", "content": retry_content})
                        # 继续循环重试同一调用})
                        continue
                    elif structured_error.category == ErrorCategory.PARAMETER_ERROR:
                        # 参数错误，提示 LLM 检查参数
                        messages.append({"role": "assistant", "content": content})
                        param_fix_content = (
                            f"工具调用失败: {structured_error.summary} 建议:{structured_error.suggested_fix}"
                        )
                        messages.append({"role": "assistant", "content": param_fix_content})
                        # 继续循环让 LLM 修正参数后重试
                        continue

                    if self.consecutive_failures >= self.degradation_threshold:
                        # 连续失败达到降级阈值，提示用户需要人工协助
                        return {
                            "success": False,
                            "answer": f"连续失败 {self.consecutive_failures} 次，建议请求人类协助: {structured_error.suggested_fix}",
                            "attempts": tool_attempts,
                        }

                    # if structured_error.category == ErrorCategory.PERMANENT:
                    #     ...
                    # if self.consecutive_failures >= self.degradation_threshold:
                    #     ...

                    # 添加错误反馈到上下文
                    feedback = self._format_error_feedback(structured_error)
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": feedback})
            else:
                # 纯文本回复（最终答案或不需要工具）
                return {"success": True, "answer": content, "attempts": tool_attempts}

        # 超过最大重试次数
        return {
            "success": False,
            "answer": f"已达到最大重试次数 ({self.max_retries})，任务未能完成。",
            "attempts": tool_attempts,
        }


# ═══════════════════════════════════════════════════════════════
# 实验验证
# ═══════════════════════════════════════════════════════════════


def test_retryable_error():
    """测试可重试错误：超时后应该重试并尝试成功。"""
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
    """测试参数错误：LLM 应该根据错误提示修正参数。"""
    reset()
    # 模拟表 "employees" 不存在，但 "users" 存在
    global TOOL_BACKEND
    TOOL_BACKEND["employees"] = False

    agent = ResilientAgent(max_retries=3, degradation_threshold=2)

    section("场景 2：参数错误 — 查询不存在的表")
    result = agent.run("帮我从 employees 表查一下所有员工")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    check("Agent 回复包含了建议或修正", len(result["answer"]) > 5)
    # 清理
    del TOOL_BACKEND["employees"]

    summary()


def test_permanent_error():
    """测试永久错误：LLM 不应该重试，直接告知用户。"""
    reset()
    global TOOL_BACKEND
    TOOL_BACKEND["admin_access"] = False

    agent = ResilientAgent(max_retries=3, degradation_threshold=2)

    section("场景 3：永久错误 — 无权限访问")
    result = agent.run("帮我查一下 admin_logs 表里最近的登录记录")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    is_stopped_early = result["attempts"] <= 1
    has_permission_msg = "权限" in result["answer"] or "无法" in result["answer"]
    check("Agent 不会反复尝试永久错误", is_stopped_early or has_permission_msg)
    TOOL_BACKEND["admin_access"] = True

    summary()


def test_degradation():
    """测试降级策略：连续失败后应该请求人类协助而非死循环。"""
    reset()
    global TOOL_BACKEND
    TOOL_BACKEND["admin_access"] = False

    agent = ResilientAgent(max_retries=5, degradation_threshold=2)

    section("场景 4：降级策略 — 连续失败后请求人类")
    # 多次查询不存在的表触发连续失败
    result = agent.run("帮我查一下 admin_logs 表，然后查 weather 表，最后查 secret 表")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    # 降级后应该请求人类或承认失败
    check("Agent 在连续失败后有降级行为", len(result["answer"]) > 10)

    TOOL_BACKEND["admin_access"] = True

    summary()


def test_success_path():
    """测试正常路径：不触犯任何错误。"""
    reset()
    agent = ResilientAgent(max_retries=3, degradation_threshold=2)

    section("场景 5：正常路径 — 查询存在的表和天气")
    result = agent.run("帮我查一下北京的天气，再查一下 users 表里有没有叫张三的用户")
    print(f"Agent 回答: {result['answer']}")
    print(f"尝试次数: {result['attempts']}")
    check("正常任务成功完成", result["success"])

    summary()


if __name__ == "__main__":
    test_retryable_error()
    test_parameter_error()
    test_permanent_error()
    test_degradation()
    test_success_path()
