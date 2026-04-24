# Answer Correctness (答案正确性) 详解

## 一句话概括

Answer Correctness 衡量生成答案与标准答案的整体匹配程度——综合了语义相似度和事实准确性。

## 核心问题

> 答案到底对不对？

Faithfulness 告诉你"有没有瞎编"，Answer Relevance 告诉你"有没有跑题"，但两者都不能直接回答"答案对不对"。

```
问题: "Python 的创始人是谁？"
标准答案: "Guido van Rossum"

答案 A: "Python 由 Guido van Rossum 创建，他是荷兰程序员"
  → Faithfulness 高, Answer Relevance 高, Answer Correctness 高

答案 B: "Python 由 Guido van Rossum 创建，他出生于 1956 年"
  → Faithfulness 可能高（如果上下文提到了年份）, Answer Relevance 高
  → Answer Correctness 取决于"1956 年"是否正确（如果标准答案没提年份，多余但不算错）

答案 C: "Python 由 Dennis Ritchie 创建"
  → Faithfulness 可能低，Answer Correctness 低（人名错误）
```

---

## 计算过程

RAGAs 的 Answer Correctness 是一个**加权组合指标**：

```
Answer Correctness = α × 语义相似度 + (1 - α) × 事实重叠度
```

默认 α = 0.5（各占一半权重）。

### 组成部分 1：语义相似度

用 Embedding 计算生成答案与标准答案的余弦相似度。

```
标准答案: "Python 由 Guido van Rossum 于 1991 年创建"
生成答案: "Guido van Rossum 是 Python 的创始人，这门语言诞生于 1991 年"

语义相似度 = cosine_similarity(embed(标准答案), embed(生成答案))
           ≈ 0.95  (意思几乎一样，只是表达不同)
```

**特点**：语义相似度容许换词、换语序，只要意思对就行。

### 组成部分 2：事实重叠度

类似 Faithfulness 的 claim 匹配，但比较的对象是标准答案而非检索上下文。

```
标准答案 Claims:
  Claim 1: "Python 由 Guido van Rossum 创建"
  Claim 2: "于 1991 年创建"

生成答案 Claims:
  Claim 1: "Guido van Rossum 是 Python 的创始人" → 匹配标准答案 Claim 1 ✓
  Claim 2: "诞生于 1991 年" → 匹配标准答案 Claim 2 ✓

事实重叠度 = TP / (TP + FP + FN)
           = 2 / (2 + 0 + 0) = 1.0
```

**TP**：生成答案中与标准答案匹配的 Claims
**FP**：生成答案中有但标准答案中没有的 Claims
**FN**：标准答案中有但生成答案中缺失的 Claims

### 最终计算

```
Answer Correctness = 0.5 × 0.95 + 0.5 × 1.0 = 0.975
```

---

## 完整示例

### 案例 1：高 Answer Correctness

```
标准答案: "FAISS 是 Facebook 开发的向量检索库"
生成答案: "FAISS 由 Facebook AI Research 开发，是用于向量相似性搜索的库"

语义相似度 ≈ 0.92
事实重叠度:
  标准 Claims: ["FAISS 由 Facebook 开发", "FAISS 是向量检索库"]
  生成 Claims: ["FAISS 由 Facebook AI Research 开发", "用于向量相似性搜索"]
  TP = 2, FP = 0, FN = 0 → 1.0

Answer Correctness = 0.5 × 0.92 + 0.5 × 1.0 = 0.96
```

### 案例 2：部分正确

```
标准答案: "Python 由 Guido van Rossum 于 1991 年创建，是一种解释型语言"
生成答案: "Python 由 Guido van Rossum 创建，广泛应用于数据科学"

语义相似度 ≈ 0.65 (意思有偏)
事实重叠度:
  标准 Claims: ["Guido van Rossum 创建", "1991 年创建", "解释型语言"]
  生成 Claims: ["Guido van Rossum 创建", "广泛应用于数据科学"]
  TP = 1, FP = 1, FN = 2 → 1/(1+1+2) = 0.25

Answer Correctness = 0.5 × 0.65 + 0.5 × 0.25 = 0.45
```

### 案例 3：语义相似但事实错误

```
标准答案: "Python 由 Guido van Rossum 于 1991 年创建"
生成答案: "Python 由 Dennis Ritchie 于 1972 年创建"

语义相似度 ≈ 0.85 (句子结构几乎一样，只是名字和年份不同)
事实重叠度:
  标准 Claims: ["Guido van Rossum 创建", "1991 年创建"]
  生成 Claims: ["Dennis Ritchie 创建", "1972 年创建"]
  TP = 0, FP = 2, FN = 2 → 0/(0+2+2) = 0.0

Answer Correctness = 0.5 × 0.85 + 0.5 × 0.0 = 0.425
```

**启示**：语义相似但事实错误时，Answer Correctness 会被事实重叠度拉低。这正是为什么需要两个组成部分——单纯看语义相似度会被"看起来像"的答案欺骗。

---

## Answer Correctness vs 其他指标

| 对比 | 区别 |
|------|------|
| vs Faithfulness | Faithfulness 对比的是上下文，Correctness 对比的是标准答案 |
| vs Answer Relevance | Relevance 评估是否切题，Correctness 评估是否正确 |
| vs Context Recall | Recall 评估检索覆盖度，Correctness 评估最终答案质量 |

**依赖关系**：
```
Context Recall 高 → 模型有足够信息
Faithfulness 高  → 模型没瞎编
Answer Relevance 高 → 模型没跑题
→ Answer Correctness 自然也会高

但反过来不一定：Correctness 高不代表其他指标高（可能碰巧答案对了但过程有问题）
```

---

## Answer Correctness 的局限性

| 局限 | 说明 |
|------|------|
| 需要标准答案 | 没有人工标注就无法计算 |
| 标准答案可能有误 | 如果标注本身有错，评估结果也失真 |
| 开放性问题难评估 | "你对 AI 的看法？" 这类问题没有唯一正确答案 |
| α 权重需调整 | 不同场景下语义相似度和事实重叠度的相对重要性不同 |

**实践建议**：Answer Correctness 是 RAG 评估的"终极指标"，但不应该只看它。Faithfulness、Answer Relevance、Context Recall 等过程指标能帮你定位问题所在，而 Correctness 只告诉你结果好不好。
