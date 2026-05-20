# 21 - 异步处理 (Async)

## 目标

将 Agent 系统中的 I/O 密集型操作（LLM 调用、Embedding、工具调用）改造为异步，提升并发能力。

## 核心概念

- **asyncio** — Python 原生异步框架，单线程事件循环
- **aiohttp** — 异步 HTTP 客户端，替代 requests
- **异步 vs 同步的适用场景** — I/O 密集型用 async，CPU 密集型用线程池
- **LangChain Async** — `llm.ainvoke()`, `vectorstore.asimilarity_search()`

## 实验设计

1. 将 ResearchAssistant.run() 改造为 async run()
2. 并发运行 5/10/20 个查询，对比同步和异步的完成时间
3. 计算加速比：`同步总时间 / 异步总时间`

## 预期效果

- 并发场景下加速比接近并发数（理想情况）
- 单次查询无显著差异（异步不加速单任务，只提升并发吞吐）

## 参考来源

- [FastAPI Async](https://fastapi.tiangolo.com/async/)
- [LangChain Async](https://python.langchain.com/docs/how_to/async/)
- [Python asyncio 文档](https://docs.python.org/3/library/asyncio.html)
