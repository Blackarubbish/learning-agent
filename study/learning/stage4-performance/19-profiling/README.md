# 19 - 性能瓶颈分析

## 目标

用 profiling 工具定位 Agent/RAG 系统中的性能热点，建立"先测量再优化"的习惯。

## 核心概念

- **cProfile** — Python 内置的确定性 profiler，统计每个函数的调用次数和耗时
- **py-spy** — 采样 profiler，无需修改代码，可 attach 到运行中的进程
- **火焰图 (Flame Graph)** — 可视化调用栈的耗时分布

## 实验设计

用你的 ResearchAssistant（第 18 章产物）作为被测试对象：
1. 用 cProfile 跑一个完整 run() 调用，查看各函数耗时占比
2. 画出热点列表：哪些函数占用了 80% 的时间？
3. （可选）用 py-spy 采样，生成火焰图

## 预期发现

- LLM API 调用通常是最大瓶颈（网络 I/O）
- Embedding 计算其次
- 向量检索（FAISS similarity_search）通常不是瓶颈

## 参考来源

- [Python cProfile 官方文档](https://docs.python.org/3/library/profile.html)
- [py-spy GitHub](https://github.com/benfred/py-spy)
- [Scalene — 高性能 Python profiler](https://github.com/plasma-umass/scalene)
