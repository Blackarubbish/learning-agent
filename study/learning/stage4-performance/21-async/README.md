# 21 - 异步处理 (Async)

## 目标

将 Agent 系统中的 I/O 密集型操作（LLM 调用、Embedding、工具调用）改造为异步，提升并发能力。

## 核心概念

- **asyncio** — Python 原生异步框架，单线程事件循环，通过协程在 I/O 等待时切换任务
- **async/await** — Python 异步语法糖，`async def` 定义协程，`await` 挂起等待
- **aiohttp** — 异步 HTTP 客户端，替代同步的 `requests`/`httpx`（同步版）
- **I/O 密集 vs CPU 密集** — I/O 等待（网络请求、文件读写）用 async；CPU 计算用线程池 `run_in_executor`
- **LangChain Async API** — `llm.ainvoke()`, `vectorstore.asimilarity_search()`, `embeddings.aembed_documents()`
- **asyncio.gather** — 并发执行多个协程，等待全部完成

## 实验设计

1. 将 ResearchAssistant.run() 改造为 `async def run()`
2. 并发运行 5/10/20 个查询，对比同步和异步的完成时间
3. 计算加速比：`同步总时间 / 异步总时间`

## 关键对比维度

| 维度 | 同步 | 异步 |
|------|------|------|
| 执行模型 | 一个任务完成再开始下一个 | I/O 等待时切换到其他任务 |
| 并发 10 个查询耗时 | ~10 × 单次耗时 | ~1 × 单次耗时（理想情况） |
| 单次查询耗时 | N | N（无差异） |
| 代码复杂度 | 简单直接 | 需要 async/await，注意事件循环 |

## 预期效果

- 并发场景下加速比接近并发数（理想情况）
- 单次查询无显著差异（异步不加速单任务，只提升并发吞吐）

## 学习资料总结

### 核心阅读

- [Python asyncio 官方文档](https://docs.python.org/3/library/asyncio.html) — 事件循环、协程、Task 概念
- [FastAPI Concurrency and async/await](https://fastapi.tiangolo.com/async/) — FastAPI 作者对 async 的深入解释
- [LangChain Async Guide](https://python.langchain.com/docs/how_to/async/) — LangChain 各组件的异步 API 用法

### 关键理解

- **协程不是线程**：async 是单线程内的协作式多任务，线程是操作系统抢占式调度
- **async 不加速计算**：它解决的是 I/O 等待期间 CPU 空闲的问题
- **事件循环是核心**：`asyncio.get_event_loop()` 管理所有协程的调度
- **阻塞操作会卡住整个事件循环**：在 async 函数中调用同步 I/O（如 `time.sleep`、同步 `httpx.post`）会阻塞所有协程

### AgentGuide 相关引用

- 12-Factor Agent 原则中关于并发和异步设计的内容
- Context Engineering 中异步管道设计模式

## 前置知识

- 已完成 ch19 性能分析（知道 LLM API 是最大瓶颈）
- 已完成 ch20 缓存优化（知道缓存消除重复调用）
- 异步在本章的定位：**并发场景下消除 I/O 等待的串行瓶颈**

## 参考来源

- [FastAPI Async](https://fastapi.tiangolo.com/async/)
- [LangChain Async](https://python.langchain.com/docs/how_to/async/)
- [Python asyncio 文档](https://docs.python.org/3/library/asyncio.html)
- [Real Python: Async IO in Python](https://realpython.com/async-io-python/)
