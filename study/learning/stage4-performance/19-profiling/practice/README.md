# 19 - 性能瓶颈分析

## 目标

用 profiling 工具定位 Agent/RAG 系统中的性能热点，建立"先测量再优化"的习惯。

## 运行

```bash
make run f=learning/stage4-performance/19-profiling/practice/starter.py
```

## TODO 列表

| 序号 | 内容 | 难度 |
|------|------|------|
| 1 | 实现 `profile_run()` — cProfile + pstats 按 cumtime 排序输出 | ⭐⭐ |
| 2 | 实现 `compare_sorts()` — 对比 cumtime 和 tottime 的排序差异 | ⭐⭐ |
| 3 | 实现 `run_experiments()` — 对 3 种不同复杂度查询分别 profile | ⭐⭐⭐ |
| 4 | 实现 `show_call_tree()` — 输出慢函数的调用链 | ⭐⭐ |

## 提示

- `pstats.Stats` 构造时传入 `stream=io.StringIO()` 可以捕获输出
- `sort_stats('cumtime')` 后 `.print_stats(n)` 输出 top N
- `cumtime` 和 `tottime` 的区别：`cumtime` 包含子函数调用时间，`tottime` 只有自身代码耗时
- LLM API 调用通常占据 90%+ 的 cumtime，这是预期发现
