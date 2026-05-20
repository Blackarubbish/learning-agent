# 20 - 缓存优化 (Redis)

## 目标

为 Agent 系统引入 Redis 缓存，减少重复的 LLM API 调用和 Embedding 计算。

## 核心概念

- **缓存策略** — 读时缓存 (Cache-Aside)，先查缓存再调 API
- **缓存键设计** — 对 LLM 响应用 `hash(model + messages)`，对 Embedding 用 `hash(text)`
- **TTL** — 设置过期时间避免缓存无限增长
- **缓存命中率** — 衡量缓存效果的核心指标

## 实验设计

1. 写一个不带缓存的 baseline：对同一批问题调用 LLM/Embedding
2. 引入 Redis 缓存后重新跑同一批问题
3. 对比：缓存命中率、平均响应时间、API 调用次数

## 预期效果

- 相同/相似查询的 LLM 调用减少 60-80%
- Embedding 重复计算归零（精确匹配命中）
- P50 延迟显著下降

## 前置准备

```bash
# 用 Docker 快速启动 Redis
docker run -d --name redis-dev -p 6379:6379 redis:7-alpine
```

## 参考来源

- [FastAPI with Redis](https://testdriven.io/blog/fastapi-redis/)
- [LiteLLM Caching](https://docs.litellm.ai/docs/caching)
- [redis-py 文档](https://redis-py.readthedocs.io/)
