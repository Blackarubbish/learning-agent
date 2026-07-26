# 08-RAG 评估 - 学习总结

## 笔记文件

- `faithfulness-explained.md` — 忠诚度：答案 → 拆 Claims → 验证能否从上下文推导
- `answer-relevance-explained.md` — 答案相关性：反向生成问题 → 计算语义相似度
- `context-precision-explained.md` — 上下文精确度：相关文档是否排在前面（Average Precision）
- `context-recall-explained.md` — 上下文召回率：标准答案的 Claims 是否被上下文覆盖
- `answer-correctness-explained.md` — 答案正确性：0.5×语义相似度 + 0.5×事实重叠度
- `qa.md` — 实操中遇到的 4 个关键问题及解答

## 实践脚本

- `01_ragas_basics.py` — RAGAs 5 个指标跑通，手工数据集验证指标行为
- `02_deepeval_basics.py` — DeepEval 4 个指标跑通，每个输出 pass/fail + reason
- `03_eval_pipeline.py` — 端到端流水线：Naive RAG vs Advanced RAG 对比

## 关键收获

### 1. 5 个指标各有侧重

| 指标 | 管"什么" | 低分意味着 |
|------|---------|-----------|
| Faithfulness | 不瞎编 | 模型编造了上下文没有的信息 |
| Answer Relevance | 不跑题 | 答案和问题无关或冗余 |
| Context Precision | 排序好 | 相关文档排在不相关文档后面 |
| Context Recall | 覆盖全 | 检索漏掉了关键信息 |
| Answer Correctness | 答案对 | 综合了语义相似度 + 事实准确性 |

### 2. DeepSeek + RAGAs 兼容性坑

- DeepSeek 不支持 `n>1`，AnswerRelevancy 默认 `generate_n=3` 会报错，需手动设为 1
- 智谱 OpenAI 兼容接口的 embedding 模型名是 `embedding-3`，不是 `text-embedding-v3`
- `LLM returned 1 generations instead of requested 3` 是无害警告

### 3. Rerank 的价值需要足够大的候选集

在小文档集（12 篇）上，Naive RAG 和 Advanced RAG 评估分数几乎相同。Rerank 的优势在候选文档多、噪声大时才能体现。

### 4. "无法回答"被 Faithfulness 打 0 分是框架局限

LLM 回答"根据现有信息无法回答"是正确行为，但 RAGAs 的 Faithfulness 会给出 0 分（因为没有可验证的 Claims）。需要单独统计"拒绝回答"比例作为补充指标。

## 指标与优化方向速查

| 指标低 | 诊断 | 优化方向 |
|--------|------|----------|
| Context Recall 低 | 检索覆盖不足 | 增大 top-k、换 Embedding、混合检索 |
| Context Precision 低 | 检索排序差 | Rerank、调优检索参数 |
| Faithfulness 低 | 模型幻觉严重 | 换更强模型、加 system prompt 约束、减少 top-k |
| Answer Relevance 低 | 答案跑题 | 优化 prompt、查询变换 |
| Answer Correctness 低 | 答案整体质量差 | 综合优化检索 + 生成 |
