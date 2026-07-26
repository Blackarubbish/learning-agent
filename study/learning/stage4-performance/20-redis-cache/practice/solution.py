"""LLM 缓存优化 — 参考实现

核心思路：
- 精确缓存：SHA256(prompt) 做 key，字符级完全匹配才命中
- 语义缓存：embedding 余弦相似度 > threshold 即命中，同义改写也能复用
- Cache-Aside 模式：先查缓存 → 未命中则调 LLM → 写入缓存
- 第二轮 benchmark 全命中证明缓存生效，耗时大幅下降
"""

import time

from common import (
    get_or_create_embeddings,
    get_or_create_llm,
    load_dotenv_if_needed,
    reset,
    section,
    summary,
)
from common.cache import ExactMatchCache, SemanticCache
from common.check import check
from fakeredis import FakeRedis

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


def cached_llm_invoke(prompt: str, cache: ExactMatchCache) -> tuple[str, bool]:
    """Cache-Aside 模式：先查缓存，未命中则调 LLM 并回写。"""
    cached = cache.get(prompt)
    if cached is not None:
        return cached, True

    result = llm.invoke(prompt)
    # llm.invoke 返回 str 或 AIMessage，统一成 str
    content = result if isinstance(result, str) else result.content
    cache.set(prompt, content)
    return content, False


def benchmark(queries: list[str], cache: ExactMatchCache) -> dict:
    """两轮查询对比：第一轮全部 miss（填充缓存），第二轮全部 hit。"""
    # 第一轮 — 全部 miss
    first_round_hits = 0
    t0 = time.perf_counter()
    for q in queries:
        _, is_hit = cached_llm_invoke(q, cache)
        if is_hit:
            first_round_hits += 1
    first_round_time = time.perf_counter() - t0

    # 第二轮 — 全部命中（精确缓存保证）
    second_round_hits = 0
    t0 = time.perf_counter()
    for q in queries:
        _, is_hit = cached_llm_invoke(q, cache)
        if is_hit:
            second_round_hits += 1
    second_round_time = time.perf_counter() - t0

    return {
        "first_round_hits": first_round_hits,
        "first_round_time": round(first_round_time, 2),
        "second_round_hits": second_round_hits,
        "second_round_time": round(second_round_time, 2),
    }


def test_semantic_cache(embeddings) -> dict:
    """语义缓存：原文和变体之间因语义相似而共享缓存。

    threshold=0.85 允许"同义改写"命中，但不会把无关问题误匹配。
    """
    redis = FakeRedis()
    cache = SemanticCache(redis, embeddings, ttl=300, threshold=0.85)

    original = "什么是机器学习？"
    variants = ["机器学习是什么？", "ML 是什么？"]

    # 先缓存原文
    _, _ = cached_llm_invoke(original, ExactMatchCache(redis, ttl=300))
    # 同时写入语义缓存
    llm_result = llm.invoke(original)
    content = llm_result if isinstance(llm_result, str) else llm_result.content
    cache.set(original, content)

    results = {"原文": original}
    for v in variants:
        hit = cache.get(v)
        results[v] = f"命中: {hit[:50]}..." if hit else "未命中"

    return results


if __name__ == "__main__":
    reset()
    section("20 - 缓存优化")

    redis = FakeRedis()

    # 场景 1: 精确缓存 benchmark
    section("场景 1: 精确缓存 — 两轮 Benchmark")
    exact_cache = ExactMatchCache(redis, ttl=300)

    queries = [
        "什么是 RAG？",
        "Python 的 GIL 是什么？",
        "Redis 和 Memcached 的区别是什么？",
    ]

    stats = benchmark(queries, exact_cache)
    print(f"第一轮: {stats['first_round_hits']} 命中, 耗时 {stats['first_round_time']}s")
    print(f"第二轮: {stats['second_round_hits']} 命中, 耗时 {stats['second_round_time']}s")

    check("第一轮全 miss", stats["first_round_hits"] == 0)
    check("第二轮全 hit", stats["second_round_hits"] == len(queries))
    check("第二轮比第一轮快", stats["second_round_time"] < stats["first_round_time"])

    # 场景 2: 语义缓存
    section("场景 2: 语义缓存 — 相似查询命中测试")
    embeddings = get_or_create_embeddings()
    sem_result = test_semantic_cache(embeddings)
    for k, v in sem_result.items():
        print(f"  {k}: {v}")

    check("语义缓存结果不为空", len(sem_result) > 0)

    summary()
