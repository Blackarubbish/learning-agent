"""手写 ReWOO Agent — 一次性规划，无中间观察.

Usage:
    uv run handwrite/05-rewoo/starter.py
"""

# TODO 1: 引入 LLMClient，定义工具

# TODO 2: Planner — LLM 一次性生成工具调用计划（含依赖标注）

# TODO 3: 依赖图解析 — 构建 DAG，识别可并行执行的工具

# TODO 4: Worker 执行引擎 — 并行执行无依赖的工具，串行执行有依赖的

# TODO 5: Solver — 汇总所有结果，LLM 生成最终答案

if __name__ == "__main__":
    print("TODO: 实现 ReWOO Agent")
