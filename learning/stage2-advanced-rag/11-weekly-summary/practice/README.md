# 11 - 周度总结：构建完整 Advanced RAG 系统

## 目标

把 Week 2 学的所有技术整合到一个AdvancedRAG管线中，并对比优化前后的效果。

## 整合的技术

| 技术 | 来源章节 | 作用 |
|------|---------|------|
| Multi-Query 查询变换 | 06 | 多角度改写查询，提升召回率 |
| BM25 关键词检索 | 07 | 精确关键词匹配 |
| 向量语义检索 | 04/07 | 语义相似度检索 |
| RRF 融合 | 07 | 不依赖绝对分数的排名融合 |
| Rerank 精排 | 07 | 对候选文档精细排序 |
| LLM 生成 | 05 | 基于上下文生成答案 |

## 前置知识

- 完成 06-10 章的所有练习
- 理解 BM25、向量检索、RRF、Rerank 的基本原理

## 运行方式

```bash
uv run python learning/stage2-advanced-rag/11-weekly-summary/practice/starter.py
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `starter.py` | 骨架代码 + TODO，引导你逐模块构建 |
| `solution.py` | 完整参考实现 + 对比分析 |
