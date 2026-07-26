"""性能瓶颈分析 — 用 cProfile 定位 Agent 系统的性能热点

运行：
  make run-study f=learning/stage4-performance/19-profiling/practice/starter.py
"""

import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

from common import get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

# 导入第 18 章的 ResearchAssistant，直接作为被测对象
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent.parent
        / "stage3-agent-development"
        / "18-weekly-summary"
        / "practice"
    ),
)
from agent import ResearchAssistant  # noqa: E402
from memory import LongTermMemory, ShortTermMemory  # noqa: E402

# ═══════════════════════════════════════════════════════════════
# TODO 1: 实现性能测量工具
# ═══════════════════════════════════════════════════════════════
#
# 实现一个 profile_run() 函数：
# 1. 用 cProfile.Profile() 创建一个 profiler
# 2. profiler.enable() → 执行被测代码 → profiler.disable()
# 3. 用 io.StringIO 和 pstats.Stats 解析结果
# 4. 按不同维度排序输出 top N 函数
#
# pstats.Stats 排序维度:
#   - 'cumtime' (累计时间，含子调用) → 找到"谁用了最多时间"
#   - 'tottime' (自身时间，不含子调用) → 找到"谁的代码最慢"
#   - 'ncalls' (调用次数) → 找到"谁被调用最多"


def profile_run(profiler: cProfile.Profile, top_n: int = 15) -> str:
    """从 profiler 中提取统计信息，按 cumtime 排序输出 top N。"""
    # TODO 1a: 用 io.StringIO 创建一个 stream
    stream = io.StringIO()
    # TODO 1b: 用 pstats.Stats(profiler, stream=stream) 解析 profiler 数据
    stats = pstats.Stats(profiler, stream=stream)
    # TODO 1c: 按 cumtime 降序排序，输出 top_n 条
    stats.sort_stats("cumtime")
    stats.print_stats(top_n)
    return stream.getvalue()


# ═══════════════════════════════════════════════════════════════
# TODO 2: 对比不同排序维度
# ═══════════════════════════════════════════════════════════════
#
# 同一个 profiler 数据，分别按 cumtime 和 tottime 排序：
# - cumtime: 累计耗时（含该函数调用的所有子函数），找"时间黑洞"
# - tottime: 自身耗时（不含子调用），找"代码热点"
#
# 实现 compare_sorts(profiler, top_n=10)，返回两个排序结果的对比。


def compare_sorts(profiler: cProfile.Profile, top_n: int = 10) -> dict:
    """返回按 cumtime 和 tottime 分别排序的 top N，方便对比。"""
    # TODO 2a: 分别按 cumtime 和 tottime 排序
    cumtime_stream = io.StringIO()
    tottime_stream = io.StringIO()
    # TODO 2b: 返回 {"cumtime_top": [...], "tottime_top": [...]}
    cum_stats = pstats.Stats(profiler, stream=cumtime_stream).sort_stats("cumtime")
    cum_stats.print_stats(top_n)
    tottime_stats = pstats.Stats(profiler, stream=tottime_stream).sort_stats("tottime")
    tottime_stats.print_stats(top_n)
    return {
        "cumtime_top": cumtime_stream.getvalue().splitlines(),
        "tottime_top": tottime_stream.getvalue().splitlines(),
    }


# ═══════════════════════════════════════════════════════════════
# TODO 3: 实验——对比不同查询的 profiling 结果
# ═══════════════════════════════════════════════════════════════
#
# 对 3 种不同复杂度的查询分别 profile：
#   1. 简单查询："什么是 RAG？"
#   2. 多工具查询："搜索 Agent Memory，然后做摘要"
#   3. 记忆查询："记住我的偏好：我喜欢简洁的回答"
#
# 记录每个查询的：
#   - 总耗时
#   - 工具调用次数
#   - top 3 耗时函数及其占比（cumtime / 总耗时）


def run_experiments() -> list[dict]:
    """对 3 种查询分别 profile，返回实验结果列表。"""
    # TODO 3: 实现实验循环，收集每次 profile 的数据
    queries = [
        ("easy_query", "什么是 RAG？"),
        ("multi_tool", "搜索 Agent Memory，然后做摘要"),
        ("memory_query", "记住我的偏好：我喜欢简洁的回答"),
    ]

    profile_results = []

    for name, query in queries:
        assistant = ResearchAssistant(
            llm=llm,
            short_term=ShortTermMemory(),
            long_term=LongTermMemory(),
        )
        profiler = cProfile.Profile()
        profiler.enable()
        t0 = time.perf_counter()
        result = assistant.run(query)
        elapsed_time = time.perf_counter()
        total_time = elapsed_time - t0
        profiler.disable()
        tool_calls = result.get("attempts", 0)

        ctime_stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=ctime_stream)
        stats.sort_stats("cumtime")
        stats.print_stats(3)
        top3_text = ctime_stream.getvalue()

        profile_results.append(
            {
                "query_name": name,
                "total_time": total_time,
                "tool_calls": tool_calls,
                "top3_cumtime": top3_text,
            }
        )
    return profile_results


# ═══════════════════════════════════════════════════════════════
# TODO 4: 可视化——文本版调用树
# ═══════════════════════════════════════════════════════════════
#
# 用 pstats.Stats.print_callers() 或 print_callees() 输出调用关系
# 帮助理解"谁调用了慢函数"


def show_call_tree(profiler: cProfile.Profile, limit: int = 5):
    """打印慢函数的调用者（谁调用了它）。"""
    # TODO 4: 用 pstats 的 print_callers 方法输出调用关系
    stream = io.StringIO()
    profiler_stats = pstats.Stats(profiler, stream=stream)
    profiler_stats.sort_stats("cumtime")
    profiler_stats.print_callers(limit)

    print(stream.getvalue())


# ═══════════════════════════════════════════════════════════════
# 测试入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    reset()
    section("19 - 性能瓶颈分析")

    # 准备被测 Agent
    assistant = ResearchAssistant(
        llm=llm,
        short_term=ShortTermMemory(),
        long_term=LongTermMemory(),
    )

    # 场景 1: 简单查询 profile
    section("场景 1: 简单知识检索 — cProfile")
    profiler = cProfile.Profile()
    profiler.enable()
    result = assistant.run("什么是 RAG？")
    profiler.disable()

    print(f"Agent 是否成功: {result['success']}")
    print(f"工具调用次数: {result['attempts']}")

    # TODO 1: 调用 profile_run 输出统计
    stats_output = profile_run(profiler)
    print(stats_output)

    # TODO 2: 对比排序
    comparison = compare_sorts(profiler)
    print("\n=== cumtime 排序 (找时间黑洞) ===")
    for entry in comparison.get("cumtime_top", []):
        print(entry)
    print("\n=== tottime 排序 (找代码热点) ===")
    for entry in comparison.get("tottime_top", []):
        print(entry)

    # TODO 3: 实验对比
    print("\n=== 三种查询对比 ===")
    experiments = run_experiments()
    for exp in experiments:
        print(exp)

    # TODO 4: 调用树
    print("\n=== 慢函数调用链 ===")
    show_call_tree(profiler)

    summary()
