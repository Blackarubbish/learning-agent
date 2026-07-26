# 22 - 批处理优化 (Batching)

## 目标

用批处理减少 API 调用次数，提升 Embedding 和 LLM 调用的吞吐量。

## 核心概念

- **Embedding 批处理 — 真批处理**：`embeddings.embed_documents(texts)` 一次 API 调用发送 N 条文本，N 条文本的向量化在服务端一次完成。节省的是 **N-1 次网络往返开销 (RTT)**。
- **LLM 批处理 — 并发批处理**：`llm.batch(prompts)` 内部用线程池并发调用 `invoke()`，每个 prompt 仍是一次独立 API 请求，但 N 个请求并发发送，总耗时从 Σ 降到 max。
- **Batch Size 权衡**：
  - 太小：API 调用次数多，网络往返开销大
  - 太大：单次请求数据量过大，API 可能限流（rate limit）或超时；Embedding API 通常限制单次最多 ~100 条
  - 最优值：在 API 限制内最大化吞吐，通常在 20-50 区间收益递减

## 实验设计

1. 用 50 条技术描述文本做 Embedding，对比逐条 (`embed_documents([t])`) vs 批量 (`embed_documents(texts)`)
2. 测试不同 batch_size（1/5/10/25/50），找收益递减点
3. （选做）对比串行 `llm.invoke()` vs `llm.batch()` 的 LLM 调用加速比

## 关键对比维度

| 维度 | 逐条处理 | 批处理 |
|------|---------|--------|
| API 调用次数 | N 次 | N/batch_size 次（或 1 次） |
| 网络往返 (RTT) | N × RTT | 1 × RTT（Embedding）/ ≈RTT（LLM 并发） |
| 单条均摊耗时 | ~RTT + 计算 | ~(RTT + 批量计算) / N |
| 适用场景 | 实时单条查询 | 离线批量导入、预热缓存 |

## 预期效果

- Embedding 批处理：API 调用次数从 N 降到 1，加速比可达 10-50x（取决于 N 和 RTT）
- LLM 批处理：并发加速比接近并发数（受 API rate limit 和 max_concurrency 限制）
- 注意事项：
  - `embeddings.embed_documents()` 本身就是批处理——你会发现你一直在用它
  - 批处理的核心价值是 **减少网络往返**，而非加速服务端计算
  - API 服务商通常有单次请求大小上限（如智谱 Embedding 约 100 条）

## 学习资料总结

### 核心阅读

- [LangChain Runnable.batch() API 参考](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/batch) — 官方 API 文档，`batch()` 的方法签名和参数说明
- [LangChain Runnable.batch_as_completed](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/batch_as_completed) — 流式批处理，结果逐条返回而非等全部完成
- [LangChain Batch Processing Guide (旧版)](https://python.langchain.com/docs/how_to/batch/) — 批处理概念和使用指南（已重定向到 docs.langchain.com，可搜索 "langchain batch processing" 获取最新版本）

### 关键理解

- **Embedding 批处理 ≠ LLM 批处理**：
  - `embeddings.embed_documents(texts)` = 真正的 API 级批处理，N 条文本在一次 HTTP 请求中发送，服务端一次计算
  - `llm.batch(prompts)` = LangChain 框架级并发，内部用线程池同时发 N 个独立 API 请求，服务端看到的仍是 N 次请求
  - 两者都减少了总耗时，但原理不同：前者消除往返，后者让往返重叠
- **`max_concurrency` 控制并发度**：`llm.batch(prompts, config={"max_concurrency": 5})` 限制同时发出的请求数，防止触发 API rate limit
- **batch_size 收益递减**：从 1→10 加速明显（省了 9 次往返），从 50→100 收益小（只多省了 1/50 的比例），而且接近 API 上限风险增大
- **与异步的关系**：`llm.abatch()` 是 `batch()` 的异步版本，内部用 `asyncio.gather` 而非线程池；批处理 + 异步可以叠加使用

### AgentGuide 相关引用

- 学习路线 Week 4 Day 26：批处理优化，目标"实现 Embedding 和 Reranker 的批处理，提升吞吐量"
- Continuous Batching（vLLM 相关，ch23 会涉及）：推理引擎层面的动态批处理，与本章的 API 调用批处理是不同层级的概念

### 延伸阅读

- [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits) — API 并发限制和批处理策略
- [智谱 Embedding API 文档](https://open.bigmodel.cn/dev/api/nlp-model/embedding) — 单次请求支持的最大文本条数

## 前置知识

- 已完成 ch04 向量化与存储（用过 `embed_documents`，知道它接受 list）
- 已完成 ch21 异步处理（理解 I/O 等待是瓶颈，`await` 让等待重叠）
- 批处理在本章的定位：**从另一个角度减少 I/O 开销——不是让等待重叠（异步），而是让等待只发生一次（批处理）**

## 参考来源

- [LangChain Runnable.batch() API 参考](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/batch)
- [LangChain batch_as_completed](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/batch_as_completed)
- AgentGuide 学习路线 Week 4 Day 26
