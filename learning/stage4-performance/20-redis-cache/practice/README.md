# 20 - 缓存优化

## 目标

用 Redis 缓存 LLM 响应，减少重复 API 调用，降低延迟和成本。

## 前置知识

- 19 章：cProfile 性能分析（知道 LLM API 调用是瓶颈）
- Python dict 基本操作

## 核心概念

| 概念 | 说明 |
|------|------|
| 精确缓存 (Exact Cache) | 完全相同的 prompt → 直接返回缓存，SHA256 做 key |
| 语义缓存 (Semantic Cache) | 意思相近的 prompt → 共享缓存，用 embedding 相似度匹配 |
| TTL (Time To Live) | 缓存过期时间，平衡命中率和数据新鲜度 |
| 命中率 (Hit Rate) | 命中次数 / 总查询次数，衡量缓存效果 |

## 运行

```bash
PYTHONPATH=. uv run python learning/stage4-performance/20-redis-cache/practice/starter.py
```

## TODO 列表

| 序号 | 内容 | 难度 |
|------|------|:--:|
| 1 | 集成 ExactMatchCache — 缓存 LLM 调用 | ⭐⭐ |
| 2 | 实现 Benchmark — 对比有/无缓存的耗时 | ⭐⭐ |
| 3 | 集成 SemanticCache — 语义相似查询共享缓存 | ⭐⭐⭐ |
| 4 | 思考缓存边界 — 什么场景不适合缓存？ | ⭐ |

## 提示

- `fakeredis.FakeRedis()` 用法和真实 Redis 完全一致
- 缓存模式：先 `cache.get(prompt)` → 命中则直接返回 → 未命中则调 LLM → `cache.set(prompt, result)`
- 语义缓存的 threshold 设太高（如 0.98）几乎退化为精确匹配，太低（如 0.7）会返回不相关结果
