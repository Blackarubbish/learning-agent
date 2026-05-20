# 22 - 批处理优化 (Batching)

## 目标

用批处理减少 API 调用次数，提升 Embedding 和 Reranker 的吞吐量。

## 核心概念

- **批处理 vs 逐个处理** — 一次发送 N 条数据 vs 发送 N 次单条
- **批大小 (Batch Size) 的影响** — 越大吞吐越高，但有上限（API rate limit / 内存）
- **LangChain batch API** — `llm.batch()`, `embeddings.embed_documents()`

## 实验设计

1. 用已有的知识库文档做 Embedding 批量导入
2. 对比逐个 embed vs 批次 embed（batch_size=10/50/100）
3. 记录：总耗时、API 调用次数、每条均摊耗时

## 预期效果

- API 调用次数从 N 次降到 N/batch_size 次
- 网络往返开销减少，吞吐量提升 5-20x
- 需要注意 API 的 rate limit 上限

## 参考来源

- [LangChain Batch Processing](https://python.langchain.com/docs/how_to/batch/)
- [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)
