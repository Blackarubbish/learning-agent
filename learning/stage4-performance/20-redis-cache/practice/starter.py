"""LLM 缓存优化 — 用 Redis 缓存减少重复 API 调用

运行：
  PYTHONPATH=. uv run python learning/stage4-performance/20-redis-cache/practice/starter.py
"""

import time

from fakeredis import FakeRedis

from common import get_or_create_llm, load_dotenv_if_needed, reset, section, summary
from common.check import check
from common.cache import ExactMatchCache, SemanticCache

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


# ═══════════════════════════════════════════════════════════════
# TODO 1: 集成 ExactMatchCache — 用缓存包裹 LLM 调用
# ═══════════════════════════════════════════════════════════════
#
# 实现 cached_llm_invoke(prompt, cache) 函数：
# 1. 先查缓存 cache.get(prompt)
# 2. 命中 → 直接返回 (is_hit=True)
# 3. 未命中 → 调 llm.invoke(prompt) → 写入 cache.set(prompt, content) → 返回 (is_hit=False)
#
# 缓存模式（Cache-Aside Pattern）：
#   ┌──────────┐
#   │ 查询缓存  │
#   └─────┬────┘
#     hit? │
#    ┌─────┴─────┐
#   YES          NO
#    │            │
#    ▼            ▼
#  返回缓存    调用 LLM
#               │
#               ▼
#            写入缓存
#               │
#               ▼
#            返回结果


def cached_llm_invoke(prompt: str, cache: ExactMatchCache) -> tuple[str, bool]:
    """返回 (回复内容, 是否缓存命中)。"""
    # TODO 1: 实现缓存包裹逻辑
    cached = cache.get(prompt)  # 先查缓存

    if cached:
        print(f"__Log__:缓存命中: {prompt}")
        return cached, True  # 命中，直接返回
    else:
        print(f"__Log__:缓存未命中: {prompt}")
        response = llm.invoke(prompt)  # 未命中，调用 LLM
        # 提取文本内容（如果返回的是 AIMessage）
        content = response if isinstance(response, str) else response.content
        cache.set(prompt, content)  # 写入缓存
        return content, False  # 返回结果，标记未命中


# ═══════════════════════════════════════════════════════════════
# TODO 2: 实现 Benchmark — 对比有/无缓存的性能差异
# ═══════════════════════════════════════════════════════════════
#
# 实现 benchmark(queries, cache) 函数：
# 1. 对一组查询跑两轮：第一轮填充缓存，第二轮全部命中
# 2. 统计每轮的命中次数和总耗时
# 3. 返回 stats dict，包含：
#    - first_round_hits / first_round_time
#    - second_round_hits / second_round_time
#
# 预期：第一轮命中率 = 0%，第二轮命中率 = 100%（精确缓存）


def benchmark(queries: list[str], cache: ExactMatchCache) -> dict:
    """运行两轮查询，统计缓存效果。"""
    # TODO 2a: 第一轮 — 全部 miss，填充缓存
    first_round_hits = 0
    first_round_start = time.perf_counter()
    for q in queries:
        _, is_hit = cached_llm_invoke(q, cache)
        if is_hit:
            first_round_hits += 1
    first_round_time = time.perf_counter() - first_round_start

    # TODO 2b: 第二轮 — 全部命中（精确缓存）
    second_round_hits = 0
    second_round_start = time.perf_counter()
    for q in queries:
        _, is_hit = cached_llm_invoke(q, cache)
        if is_hit:
            second_round_hits += 1
    second_round_time = time.perf_counter() - second_round_start

    return {
        "first_round_hits": first_round_hits,
        "first_round_time": round(first_round_time, 2),
        "second_round_hits": second_round_hits,
        "second_round_time": round(second_round_time, 2),
    }


# ═══════════════════════════════════════════════════════════════
# TODO 3: 语义缓存 — 让意思相近的查询共享缓存
# ═══════════════════════════════════════════════════════════════
#
# SemanticCache 用 embedding 相似度匹配，不是字符精确匹配。
#
# 实现 test_semantic_cache() 函数：
# 1. 用 SemanticCache 缓存一个查询的 LLM 响应
# 2. 用语义相近但字符不同的查询去查缓存，验证能否命中
# 3. 返回命中结果
#
# 实验查询对（语义相近但措辞不同）：
#   原文：  "什么是机器学习？"
#   变体1： "机器学习是什么？"
#   变体2： "ML 是什么？"


def test_semantic_cache(embeddings, redis) -> dict:
    """测试语义缓存：缓存原文，用变体查询验证能否命中。"""
    # TODO 3: 初始化 SemanticCache，缓存原文，测试变体命中情况
    semantic_cache = SemanticCache(redis, embeddings, ttl=300)

    original_query = "什么是机器学习？"
    variant_query_1 = "机器学习是什么？"
    variant_query_2 = "ML 是什么？"

    # 缓存原文的响应
    original_response = llm.invoke(original_query)
    # 提取文本内容（如果返回的是 AIMessage）
    original_response_text = (
        original_response if isinstance(original_response, str) else original_response.content
    )
    semantic_cache.set(original_query, original_response_text)

    # 测试变体查询的命中情况
    hit_variant_1 = semantic_cache.get(variant_query_1) is not None
    hit_variant_2 = semantic_cache.get(variant_query_2) is not None

    return {"hit_variant_1": hit_variant_1, "hit_variant_2": hit_variant_2}


# ═══════════════════════════════════════════════════════════════
# 测试入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    reset()
    section("20 - 缓存优化")

    redis = FakeRedis()
    exact_cache = ExactMatchCache(redis, ttl=300)

    # 场景 1: 精确缓存
    section("场景 1: 精确缓存 — 两轮 Benchmark")
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

    # 场景 2: 语义缓存（需要 embeddings）
    section("场景 2: 语义缓存 — 相似查询命中测试")
    from common import get_or_create_embeddings

    embeddings = get_or_create_embeddings()
    sem_result = test_semantic_cache(embeddings, redis)
    if sem_result:
        for k, v in sem_result.items():
            print(f"  {k}: {v}")
    check("语义缓存结果不为空", sem_result is not None)
    check("同义改写命中", sem_result.get("hit_variant_1", False))

    summary()
