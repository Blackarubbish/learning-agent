"""错误分类系统（来自 ch17）。

三类而非二分：如果只分"可重试/不可重试"，LLM 面对参数拼写错误也会盲目重试。
显式区分 PARAMETER_ERROR 让 LLM 的行为从"再试一次"变成"检查参数再试"。
"""

import enum
from dataclasses import dataclass


class ErrorCategory(enum.Enum):
    RETRYABLE = "retryable"  # 暂时性：超时、限流、网络抖动 → 可以重试
    PARAMETER_ERROR = "parameter_error"  # 参数问题：拼写错误、格式不对 → 修正后重试
    PERMANENT = "permanent"  # 永久性：无权限、资源已删除 → 不要重试


@dataclass
class StructuredError:
    """结构化错误信息 — 压缩到上下文窗口（12-Factor Agent 原则 9）。

    和裸 Exception 的区别：
    - summary 是给 LLM 看的自然语言摘要
    - suggested_fix 是给 LLM 的行动建议
    - category 决定了 LLM 的处理策略（重试/修正/放弃）
    """

    category: ErrorCategory
    summary: str
    suggested_fix: str


# 关键词映射表 — 优先匹配长关键词
ERROR_PATTERNS: dict[ErrorCategory, list[str]] = {
    ErrorCategory.RETRYABLE: [
        "timeout",
        "timed out",
        "connection",
        "rate limit",
        "temporarily unavailable",
        "network",
        "try again",
        "running error",
        "failed to fetch",
        "service unavailable",
    ],
    ErrorCategory.PARAMETER_ERROR: [
        "not found",
        "invalid",
        "unknown",
        "empty",
        "missing",
        "parameter",
    ],
    ErrorCategory.PERMANENT: [
        "permission denied",
        "unauthorized",
        "forbidden",
        "quota exceeded",
    ],
}

FIX_TEMPLATES: dict[ErrorCategory, str] = {
    ErrorCategory.RETRYABLE: "暂时性故障，可以重试 1 次。如果仍然失败，换一种方式获取信息。",
    ErrorCategory.PARAMETER_ERROR: "参数可能不正确，请检查参数名称和值的格式。参考错误信息中的提示修正。",
    ErrorCategory.PERMANENT: "永久错误，不要重试同一调用。告诉用户你无法完成该操作，建议替代方案。",
}


def classify_error(error_message: str) -> StructuredError:
    """基于关键词模式的错误分类。

    遍历顺序：PERMANENT → RETRYABLE → PARAMETER_ERROR（兜底）。
    PERMANENT 优先级最高，因为权限错误中的 "access denied" 不应被 PARAMETER_ERROR 的 "not found" 误匹配。
    无法分类时默认 PERMANENT（安全侧：宁可放弃也不死循环）。
    """
    error_lower = error_message.lower()
    for category in [ErrorCategory.PERMANENT, ErrorCategory.RETRYABLE, ErrorCategory.PARAMETER_ERROR]:
        for pattern in ERROR_PATTERNS[category]:
            if pattern in error_lower:
                return StructuredError(
                    category=category,
                    summary=error_message[:120],
                    suggested_fix=FIX_TEMPLATES[category],
                )
    return StructuredError(
        category=ErrorCategory.PERMANENT,
        summary=error_message[:120],
        suggested_fix="未知错误类型，出于安全考虑不再重试。",
    )
