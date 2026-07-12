"""手写 Reflection Agent — 失败→反馈→修正→重试.

Usage:
    uv run handwrite/04-reflection/starter.py
"""

# TODO 1: 引入 LLMClient，复用 02-react 的 ReAct 循环作为基础

# TODO 2: 实现错误分类（RETRYABLE / PARAMETER_ERROR / PERMANENT）

# TODO 3: 实现结构化错误反馈（分类 + 摘要 + 修复建议）

# TODO 4: 改造 ReAct 循环，Observation 失败时注入结构化反馈

# TODO 5: 实现降级策略（连续 N 次失败 → 安全终止）


if __name__ == "__main__":
    print("TODO: 实现 Reflection Agent")
