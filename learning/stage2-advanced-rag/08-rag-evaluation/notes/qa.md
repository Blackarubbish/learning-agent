# 08-RAG 评估 Q&A

## Q1: 为什么 Naive RAG 和 Advanced RAG 的评估结果几乎一样？

**现象**：在 `03_eval_pipeline.py` 中，Naive RAG (纯向量检索) 和 Advanced RAG (混合检索+Rerank) 的评估分数几乎相同：
- Faithfulness: 0.40 vs 0.40
- Answer Relevancy: 0.24 vs 0.24
- Context Precision: 0.90 vs 0.80
- Context Recall: 1.00 vs 1.00

**原因**：

1. **文档库太小（12篇）**：在小文档集上，纯向量检索已经能找到相关文档，混合检索和 Rerank 的优势体现不出来。Rerank 在候选文档多、噪声大时才能发挥重排价值。

2. **LLM 过于"诚实"**：DeepSeek 遇到检索不足的情况时，倾向于回答"根据现有信息无法回答"，而不是编造信息。这导致 3 个问题都返回了拒绝回答，Faithfulness 被评 0（因为 RAGAs 认为没有 Claims 可验证），但这其实是好的行为。

3. **测试集设计**：5 个问题中有 3 个检索效果差的问题（FAISS、Transformer、Python），导致两个系统在这些问题上表现都不好，拉低了整体分数。

**教训**：
- 评估需要足够大的文档库（50+）和足够多的测试问题（20+）才能看出差异
- "无法回答"这种拒绝回答的行为，Faithfulness 指标会给出 0 分，但这是正确的模型行为——需要区分"因拒绝回答导致的低分"和"因幻觉导致的低分"
- Rerank 的价值在候选集大、噪声多时才能体现

---

## Q2: DeepSeek API 调用 RAGAs 时有哪些坑？

1. **不支持 `n>1`**：DeepSeek 的 `n` 参数只支持 1，但 RAGAs 的 AnswerRelevancy 默认 `generate_n=3`（一次生成 3 个反向问题）。解决：手动设置 `metric.generate_n = 1`。

2. **智谱 Embedding 模型名**：OpenAI 兼容接口的模型名是 `embedding-3`，不是 `text-embedding-v3`。

3. **`LLM returned 1 generations instead of requested 3` 警告**：RAGAs 内部某些指标会请求生成多个回复，DeepSeek 只返回 1 个。不影响运行但会产生警告。

---

## Q3: RAGAs vs DeepEval 实际使用体验对比？

| 维度 | RAGAs | DeepEval |
|------|-------|----------|
| 数据构造 | `SingleTurnSample` 字典式，灵活 | `LLMTestCase` 对象式，更结构化 |
| 指标配置 | 全局配置 LLM + Embeddings | 每个指标单独配 model |
| 错误处理 | 遇到 API 错误会跳过（返回 NaN） | 遇到错误会标记 fail 并给出原因 |
| 输出可读性 | 数字为主，需要转 pandas 才好读 | 每个测试用例输出 pass/fail + reason |
| 速度 | 略慢（并发请求多） | 较快（5 个测试用例 5 秒） |
| 适合场景 | 批量评估、CI/CD 集成 | 开发调试、单测试用例排查 |

---

## Q4: Faithfulness 为 0 不一定代表系统差？

是的。在 `03_eval_pipeline.py` 中，3 个问题 LLM 回答了"根据现有信息无法回答"，Faithfulness 被评为 0。

**RAGAs 的 Faithfulness 计算逻辑**：答案 → 拆 Claims → 逐条验证。如果答案是"无法回答"，可能被拆成 0 条 Claim 或 1 条无法验证的 Claim，导致分数为 0。

**但实际上"无法回答"是正确行为**——比编造信息好得多。这是当前 LLM-based 评估框架的局限：它们无法完美区分"拒绝回答"和"答错了"。

**实践建议**：在评估脚本中单独统计"拒绝回答"的比例，作为补充指标。
