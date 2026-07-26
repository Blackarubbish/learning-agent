# Context Recall (上下文召回率) 详解

## 一句话概括

Context Recall 衡量检索到的上下文是否覆盖了回答问题所需的全部信息——本质是评估**检索覆盖度**。

## 核心问题

> 需要的信息，检索到了多少？

如果标准答案需要 A、B、C 三个信息点，但检索只覆盖了 A 和 B，Context Recall 就只有 0.67。检索漏了 C，模型要么编造（Faithfulness 降低），要么答不全（Answer Relevance 降低）。

---

## 计算过程

RAGAs 的 Context Recall 计算方式与 Faithfulness 对称：

### Faithfulness 的逻辑

```
答案 → 拆成 Claims → 每个 Claim 能否从上下文推导？
```

### Context Recall 的逻辑

```
标准答案 → 拆成 Claims → 每个 Claim 能否从检索到的上下文推导？
```

### Step 1：将标准答案拆分为关键陈述

```
标准答案: "Python 由 Guido van Rossum 于 1991 年创建，是一种解释型编程语言"

→ 拆分为 3 条 Claim：
  Claim 1: "Python 由 Guido van Rossum 创建"
  Claim 2: "Python 于 1991 年创建"
  Claim 3: "Python 是解释型编程语言"
```

### Step 2：逐条验证 Claim 是否可从检索上下文推导

```
检索上下文:
  Doc1: "Python 由 Guido van Rossum 创建"
  Doc2: "Python 是一种面向对象的编程语言"

Claim 1: "Python 由 Guido van Rossum 创建" → Doc1 可推导 ✓
Claim 2: "Python 于 1991 年创建"          → 无法推导 ✗ (没有文档提到年份)
Claim 3: "Python 是解释型编程语言"         → 无法推导 ✗ (Doc2 说面向对象，没提解释型)
```

### Step 3：计算分数

```
Context Recall = 可推导的 Claim 数 / 总 Claim 数
              = 1 / 3
              = 0.33
```

---

## 完整示例

### 案例 1：高 Context Recall

```
标准答案: "Python 是解释型语言，由 Guido van Rossum 创建"
检索上下文:
  Doc1: "Python 是一种解释型、面向对象的高级编程语言"
  Doc2: "Python 由 Guido van Rossum 于 1991 年首次发布"

→ Claim 1: "Python 是解释型语言" → 可推导 ✓
→ Claim 2: "Python 由 Guido van Rossum 创建" → 可推导 ✓
→ Context Recall = 2/2 = 1.0
```

### 案例 2：低 Context Recall — 检索缺失

```
标准答案: "Python 由 Guido van Rossum 于 1991 年创建，支持面向对象和函数式编程"
检索上下文:
  Doc1: "Python 是一种流行的编程语言"  ← 信息量太少

→ Claim 1: "由 Guido van Rossum 创建" → 无法推导 ✗
→ Claim 2: "于 1991 年创建" → 无法推导 ✗
→ Claim 3: "支持面向对象编程" → 无法推导 ✗
→ Claim 4: "支持函数式编程" → 无法推导 ✗
→ Context Recall = 0/4 = 0.0
```

### 案例 3：部分 Context Recall

```
标准答案: "FAISS 由 Facebook 开发，用于高效向量相似性搜索，支持 GPU 加速"
检索上下文:
  Doc1: "FAISS 是 Facebook AI Research 开发的向量检索库"
  Doc2: "向量检索是信息检索的重要技术"

→ Claim 1: "FAISS 由 Facebook 开发" → 可推导 ✓
→ Claim 2: "用于向量相似性搜索" → 可推导 ✓
→ Claim 3: "支持 GPU 加速" → 无法推导 ✗
→ Context Recall = 2/3 = 0.67
```

---

## Context Recall 低的连锁反应

Context Recall 低不只是检索的问题，它会波及整个 RAG 系统：

```
Context Recall 低
  ├── → 模型缺少关键信息 → 被"逼"编造 → Faithfulness 降低
  ├── → 答案不完整 → Answer Relevance 降低
  └── → 答案与标准答案差距大 → Answer Correctness 降低
```

**所以 Context Recall 往往是 RAG 系统的瓶颈指标**。检索是 RAG 的基础，地基不稳，上层建筑再好也没用。

---

## Context Recall 低的原因与对策

| 原因 | 说明 | 对策 |
|------|------|------|
| top-k 太小 | 相关文档排第 11 位，但只取了前 10 | 增大 top-k |
| Embedding 模型太弱 | 语义相近但用词不同的文档检索不到 | 换更好的 Embedding 模型 |
| 纯向量检索 | 对关键词不敏感，漏掉了精确匹配的文档 | 混合检索（BM25 + 向量） |
| 文档切分不当 | 关键信息被切到不同的 chunk，单个 chunk 信息不完整 | 优化切分策略（ParentDocument、上下文窗口） |
| 查询表达不精确 | 用户问题与文档表述差异大 | 查询变换（Multi-Query、HyDE、Sub-Query） |

---

## Context Recall 需要"标准答案"

Context Recall 的计算依赖标准答案（reference/ground truth）来拆分 Claims。

| 有标准答案 | 没有 | 有标准答案 |
|---|---|---|
| 能计算 | ✗ | ✓ |
| 常见场景 | 手工标注的数据集 | 手工标注的数据集 |
| 替代方案 | 只看 Faithfulness + Answer Relevance | — |

**实践建议**：对于生产系统，可以用 RAGAs 的测试集生成器自动生成"伪标准答案"，虽然不如人工标注精确，但可以快速建立评估基线。
