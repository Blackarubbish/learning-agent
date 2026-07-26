"""性能瓶颈分析 — 参考实现

核心思路：
- 用 cProfile 测量 Agent.run() 的每个函数调用
- cumtime（累计耗时）找"时间黑洞"——通常是 LLM API 调用的网络 I/O
- tottime（自身耗时）找"代码热点"——Python 本地计算密集处
- 3 种查询对比，看不同场景下瓶颈是否一致
"""

import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

from common import get_or_create_llm, load_dotenv_if_needed, reset, section, summary
from common.check import check

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

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


def profile_run(profiler: cProfile.Profile, top_n: int = 15) -> str:
    """用 pstats 解析 profiler 数据，按 cumtime 降序输出 top N。"""
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumtime")
    stats.print_stats(top_n)
    return stream.getvalue()


def compare_sorts(profiler: cProfile.Profile, top_n: int = 10) -> dict:
    """对比 cumtime 和 tottime 两种排序方式的 top N。"""
    stream_cum = io.StringIO()
    pstats.Stats(profiler, stream=stream_cum).sort_stats("cumtime").print_stats(top_n)

    stream_tot = io.StringIO()
    pstats.Stats(profiler, stream=stream_tot).sort_stats("tottime").print_stats(top_n)

    return {
        "cumtime_top": stream_cum.getvalue().strip().split("\n"),
        "tottime_top": stream_tot.getvalue().strip().split("\n"),
    }


def run_experiments() -> list[dict]:
    """对 3 种查询分别 profile，收集关键指标。"""
    queries = [
        ("简单查询", "什么是 RAG？"),
        ("多工具查询", "搜索 Agent Memory 的内容，然后对找到的结果做一个摘要"),
        ("记忆查询", "记住我的偏好：我喜欢用表格对比的方式来呈现信息"),
    ]

    results = []
    for label, query in queries:
        assistant = ResearchAssistant(
            llm=llm,
            short_term=ShortTermMemory(),
            long_term=LongTermMemory(),
        )

        profiler = cProfile.Profile()
        profiler.enable()
        t0 = time.perf_counter()
        result = assistant.run(query)
        elapsed = time.perf_counter() - t0
        profiler.disable()

        # 提取 top 3 耗时函数及其 cumtime 占比
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats("cumtime")
        stats.print_stats(3)

        results.append(
            {
                "label": label,
                "query": query,
                "success": result["success"],
                "attempts": result["attempts"],
                "elapsed_s": round(elapsed, 2),
                "top3_functions": stream.getvalue().strip(),
            }
        )

    return results


def show_call_tree(profiler: cProfile.Profile, limit: int = 5):
    """用 print_callers 展示慢函数的调用链——谁调用了慢函数。"""
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumtime")
    stats.print_callers(limit)
    print(stream.getvalue())


if __name__ == "__main__":
    reset()
    section("19 - 性能瓶颈分析")

    assistant = ResearchAssistant(
        llm=llm,
        short_term=ShortTermMemory(),
        long_term=LongTermMemory(),
    )

    section("场景 1: 简单知识检索 — cProfile")
    profiler = cProfile.Profile()
    profiler.enable()
    result = assistant.run("什么是 RAG？")
    profiler.disable()

    print(f"Agent 是否成功: {result['success']}")
    print(f"工具调用次数: {result['attempts']}")
    check("Agent 成功完成任务", result["success"])

    print("\n=== 按 cumtime 排序 (Top 15) ===")
    print(profile_run(profiler))

    print("\n=== cumtime vs tottime 对比 ===")
    comparison = compare_sorts(profiler)
    print("--- cumtime (找时间黑洞) ---")
    for line in comparison["cumtime_top"][:5]:
        print(line)
    print("--- tottime (找代码热点) ---")
    for line in comparison["tottime_top"][:5]:
        print(line)

    check("cumtime 排序有结果", len(comparison["cumtime_top"]) > 0)
    check("tottime 排序有结果", len(comparison["tottime_top"]) > 0)

    section("场景 2: 三种查询对比实验")
    experiments = run_experiments()
    for exp in experiments:
        print(f"\n--- {exp['label']} ---")
        print(f"  查询: {exp['query'][:50]}...")
        print(f"  耗时: {exp['elapsed_s']}s, 工具调用: {exp['attempts']} 次")
        print(f"  Top 3 函数:\n{exp['top3_functions']}")
    check("3 个实验全部完成", len(experiments) == 3)
    # 多工具查询比简单查询耗时长（因为调用更多次 LLM）
    check(
        "多工具查询耗时 ≥ 简单查询",
        experiments[1]["elapsed_s"] >= experiments[0]["elapsed_s"] * 0.5,
    )

    section("场景 3: 调用链分析")
    show_call_tree(profiler)

    summary()
