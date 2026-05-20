# 第四阶段：系统性能优化

> Week 4 — 从"能用"到"高性能"：找到瓶颈 → 优化 → 量化对比

## 阶段目标

不再从零搭建新功能，而是在已有的 Agent/RAG 系统上：
1. **定位瓶颈** — 用 profiling 工具找到性能热点
2. **逐个优化** — 缓存、异步、批处理
3. **量化对比** — 每个优化都需要优化前 vs 优化后的数据

## 章节概览

| 章节 | 主题 | 核心技能 | 实验产出 |
|------|------|---------|---------|
| 19 | 性能瓶颈分析 | cProfile, py-spy 定位热点 | 火焰图 + 性能报告 |
| 20 | 缓存优化 (Redis) | Redis 缓存 LLM/Embedding | 缓存命中率 + 响应时间对比 |
| 21 | 异步处理 (Async) | asyncio, aiohttp | QPS 对比（同步 vs 异步） |
| 22 | 批处理优化 | Batch Embedding/Reranker | 吞吐量对比（逐个 vs 批量） |
| 23 | 高性能推理 (vLLM) | vLLM 部署 + 压测 | tokens/s 吞吐量数据 |
| 24 | 周度总结与性能压测 | locust 压测 + 综合优化 | 优化前后完整对比报告 |

## 前置条件

- 已完成阶段 1-3（RAG 管道 + Agent + 工具调用）
- 安装 Redis（`apt install redis-server` 或用 Docker）
- 可选：GPU 环境用于 vLLM（第 23 章可用 CPU 模拟）

## 实验方法

每个章节的标准流程：

```
1. 基准测试 → 记录优化前数据
2. 实现优化 → 编写代码
3. 对比测试 → 记录优化后数据
4. 分析 → 为什么提升/没有提升？
```

## 参考来源

- [AgentGuide 学习路线 - Week 4](https://github.com/adongwanai/AgentGuide)
- [py-spy](https://github.com/benfred/py-spy)
- [FastAPI with Redis](https://testdriven.io/blog/fastapi-redis/)
- [vLLM Quickstart](https://docs.vllm.ai/en/latest/getting_started/quickstart.html)
