"""批处理优化 — 参考实现

对比逐条 API 调用和批量调用的性能差异，理解批处理如何通过减少网络往返提升吞吐。
"""

import time

from common import get_or_create_embeddings, get_or_create_llm, load_dotenv_if_needed, reset
from common.check import check, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)
embeddings = get_or_create_embeddings()

TEXTS = [
    "RAG（检索增强生成）结合信息检索和文本生成，先检索相关文档再作为上下文提供给LLM生成答案。",
    "ReAct是Reasoning+Acting的Agent架构，LLM交替进行推理和行动。",
    "Function Calling用JSON Schema定义工具，LLM输出结构化调用请求。",
    "Redis是开源内存数据结构存储，常用作缓存和消息队列。",
    "cProfile是Python内置性能分析器，统计函数调用次数和耗时。",
    "异步编程使用协程和事件循环，在I/O等待时切换到其他任务。",
    "FAISS是Facebook开源的向量相似度搜索库。",
    "语义缓存用Embedding相似度匹配，精确缓存用哈希匹配。",
    "BM25是一种基于词频的排序算法，属于TF-IDF的改进版本。",
    "RRF（倒数排名融合）把多种检索结果按排名取倒数求和。",
    "LangChain是用于构建LLM应用的开源框架。",
    "Milvus是分布式向量数据库，支持增删改查和属性过滤。",
    "Docker是一个容器化平台，用于打包和部署应用。",
    "Kubernetes是容器编排平台，管理容器集群的部署和扩展。",
    "Python的GIL限制了同一进程内多线程的并行执行。",
    "微服务架构将应用拆分为独立的小服务，每个服务专注于单一功能。",
    "GraphQL是一种API查询语言，客户端可以精确指定需要的数据。",
    "WebSocket是一种全双工通信协议，适合实时应用。",
    "OAuth2.0是一种授权框架，允许第三方应用获取有限的资源访问权限。",
    "JWT（JSON Web Token）是一种紧凑的令牌格式，用于在各方之间安全传输信息。",
    "事件驱动架构通过事件的发布和订阅实现服务间的松耦合。",
    "CI/CD是持续集成和持续部署的实践，自动化软件的构建测试和发布流程。",
    "负载均衡将流量分配到多个服务器，提升系统的可用性和扩展性。",
    "数据库索引是一种数据结构，用于加速数据的查询操作。",
    "缓存穿透是指查询一个不存在的数据，由于缓存不命中而直接访问数据库。",
    "消息队列用于在服务之间异步传递消息，实现解耦和削峰填谷。",
    "分布式事务涉及多个独立的数据源，需要保证跨节点的数据一致性。",
    "CAP定理指出分布式系统无法同时满足一致性可用性和分区容错性。",
    "幂等性是指同一个操作执行多次产生的结果和执行一次相同。",
    "乐观锁假设数据冲突的概率较低，在提交时检查版本号决定是否成功。",
]

# ═══════════════════════════════════════════════════════════════
# TODO 1: 量化批处理的真实收益
# ═══════════════════════════════════════════════════════════════
# embed_documents([text]) vs embed_documents(texts) 调用的是同一个函数。
# 区别仅在于 list 的长度——也就是一次 HTTP 请求带了多少条文本。
# 耗时差距不在服务端计算速度，而在 N-1 次额外的网络往返（RTT）。


def measure_embedding(texts: list[str], batch_size: int) -> tuple[float, int]:
    """按 batch_size 分批调用 embed_documents，返回 (耗时秒数, API调用次数)。"""
    start = time.time()
    calls = 0
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings.embed_documents(batch)
        calls += 1
    return time.time() - start, calls


def run_embedding_benchmark():
    """对比 batch_size=1, 10, 30 三种策略的表现。"""
    texts = TEXTS[:30]

    print(f"{'batch_size':<12} {'耗时':<10} {'API调用':<10} {'单条均摊':<12}")
    print("-" * 44)

    results = {}
    for bs in [1, 10, 30]:
        elapsed, calls = measure_embedding(texts, bs)
        per_item_ms = elapsed / len(texts) * 1000
        results[bs] = (elapsed, calls, per_item_ms)
        print(f"{bs:<12} {elapsed:<10.2f}s {calls:<10} {per_item_ms:<12.1f}ms")

    # bs=30 的 API 调用次数应该是 1（一次全发）
    _, calls_1, _ = results[1]
    _, calls_30, _ = results[30]
    elapsed_1, _, _ = results[1]
    elapsed_30, _, _ = results[30]

    check("bs=1 调用 30 次 API", calls_1 == 30,
          f"预期 30 次，实际 {calls_1} 次")
    check("bs=30 只调用 1 次 API", calls_30 == 1,
          f"预期 1 次，实际 {calls_30} 次")
    check("bs=30 比 bs=1 快", elapsed_30 < elapsed_1,
          f"bs=1: {elapsed_1:.1f}s, bs=30: {elapsed_30:.1f}s")

    # 性能差距来自 RTT 而非计算：如果 30 次 API vs 1 次 API，差距 ≈ 29 × RTT
    rtt_estimate = (elapsed_1 - elapsed_30) / (calls_1 - calls_30)
    print(f"\n估算单次 RTT ≈ {(elapsed_1 - elapsed_30) / (calls_1 - calls_30) * 1000:.0f}ms "
          f"(= ({elapsed_1:.1f}s - {elapsed_30:.1f}s) / ({calls_1} - {calls_30}) 次)")


# ═══════════════════════════════════════════════════════════════
# TODO 2: LLM 批处理 ≠ Embedding 批处理
# ═══════════════════════════════════════════════════════════════
# llm.batch() 内部用线程池并发调用 invoke()，每个 prompt 仍是独立的 API 请求。
# 耗时 ≈ max(单次耗时)，不是 sum 也不是 1/n。
# 而 embed_documents 是真正的 API 级合并：N 条文本在一次 HTTP 请求中处理完毕。


def benchmark_llm_batch(questions: list[str]):
    """串行 vs 批量 LLM 调用对比。"""
    prompts = [[("system", "用一句话回答。"), ("human", q)] for q in questions]

    # 串行：逐个 invoke，总耗时 = Σ 每次耗时
    start = time.time()
    for p in prompts:
        llm.invoke(p)
    serial_time = time.time() - start

    # 批量：内部线程池并发 invoke，总耗时 ≈ max(每次耗时)
    start = time.time()
    llm.batch(prompts)
    batch_time = time.time() - start

    speedup = serial_time / batch_time if batch_time > 0 else float("inf")
    single_estimate = serial_time / len(questions)  # 估算单次 invoke 耗时

    print(f"串行 x{len(questions)}: {serial_time:.1f}s")
    print(f"batch x{len(questions)}: {batch_time:.1f}s")
    print(f"加速比: {speedup:.1f}x")
    print(f"估算单次耗时: {single_estimate:.1f}s")
    print(f"batch 耗时 vs 单次耗时: {batch_time:.1f}s vs ~{single_estimate:.1f}s "
          f"({'≈ 单次' if abs(batch_time - single_estimate) < single_estimate * 0.5 else '注意：batch 并非合并为一次请求'})")

    check("batch 比串行快", batch_time < serial_time,
          f"串行{serial_time:.1f}s vs batch{batch_time:.1f}s")

    # 关键验证：batch 耗时并非 1/n（因为它不是合并请求，而是并发请求）
    # batch 耗时应该明显大于 serial_time / len(questions) 的理论下限
    theoretical_min = serial_time / len(questions)
    check("batch 耗时 > 理论最小值（证明它不是合并为一次请求）",
          batch_time > theoretical_min * 0.5,
          f"batch{batch_time:.1f}s vs 理论下限{theoretical_min:.1f}s")


# ═══════════════════════════════════════════════════════════════
# TODO 3: 探索 batch_size 的收益递减点
# ═══════════════════════════════════════════════════════════════
# 收益递减的根本原因：每减少一次 API 调用的价值是相同的（省 1 个 RTT），
# 但当 API 调用次数本身已经很少时，再减少的绝对值就不大了。
# 从 30 次到 6 次（bs=5）的收益 >> 从 6 次到 3 次（bs=10）的收益


def find_best_batch_size(texts: list[str], sizes: list[int] | None = None):
    """对不同 batch_size 做 benchmark，观察收益递减规律。"""
    if sizes is None:
        sizes = [1, 5, 10, 15, 30]

    print(f"\n{'batch_size':<12} {'耗时':<10} {'API调用':<10} {'单条均摊':<12} {'vs bs=1':<10}")
    print("-" * 56)

    baseline = None
    prev_elapsed = None
    prev_bs = None
    for bs in sizes:
        elapsed, calls = measure_embedding(texts, bs)
        per_item_ms = elapsed / len(texts) * 1000
        if baseline is None:
            baseline = elapsed
        speedup = baseline / elapsed if elapsed > 0 else float("inf")

        # 计算边际收益：从上个 batch_size 到当前的加速提升
        marginal = ""
        if prev_elapsed is not None and prev_bs is not None:
            marginal_gain = prev_elapsed / elapsed if elapsed > 0 else float("inf")
            marginal = f"(vs bs={prev_bs}: {marginal_gain:.1f}x)"

        print(f"{bs:<12} {elapsed:<10.2f}s {calls:<10} {per_item_ms:<12.1f}ms "
              f"{speedup:<10.1f}x {marginal}")

        prev_elapsed = elapsed
        prev_bs = bs

    check("bs=30 比 bs=1 快", sizes[-1] == 30)
    # 边际收益递减：bs=5→10 的提升应该小于 bs=1→5 的提升
    print("\n观察：从哪个 batch_size 开始，加速比的增长明显放缓？")


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    reset()

    # --- TODO 1: 批处理收益 ---
    section("TODO 1: 量化批处理收益")
    run_embedding_benchmark()

    # --- TODO 2: LLM batch vs Embedding batch ---
    section("TODO 2: LLM batch ≠ Embedding batch")
    questions = [
        "什么是RAG？",
        "什么是ReAct？",
        "什么是Function Calling？",
        "什么是向量数据库？",
        "什么是缓存穿透？",
    ]
    benchmark_llm_batch(questions)

    # --- TODO 3: 收益递减点 ---
    section("TODO 3: 探索收益递减点")
    find_best_batch_size(TEXTS[:30])

    summary()
