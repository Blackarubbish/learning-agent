# Faithfulness (忠诚度) 详解

## 一句话概括

Faithfulness 衡量答案中的每一条陈述是否都能从检索到的上下文中推导出来——本质是检测**幻觉（hallucination）**。

## 核心问题

> 答案有没有"瞎编"？

模型生成答案时，可能会混入上下文中没有的信息。Faithfulness 就是量化这种"瞎编"的程度。

---

## 计算过程

RAGAs 的 Faithfulness 计算分三步：

### Step 1：将答案拆分为独立陈述（Claims）

用 LLM 将答案拆成若干条可以独立验证的陈述。

```
答案: "深度学习是机器学习的分支，由 Hinton 在 2006 年提出，使用神经网络进行特征学习"

→ 拆分为 3 条 Claim：
  Claim 1: "深度学习是机器学习的分支"
  Claim 2: "由 Hinton 在 2006 年提出"
  Claim 3: "使用神经网络进行特征学习"
```

### Step 2：逐条验证 Claim 是否可从上下文推导

对每条 Claim，用 LLM 判断它能否从上下文中推导出来。
<!-- 
```
上下文: "深度学习（Deep Learning）是机器学习的一个子领域，使用多层神经网络自动学习数据的表示"

Claim 1: "深度学习是机器学习的分支" → 可推导 ✓
Claim 2: "由 Hinton 在 2006 年提出" → 无法推导 ✗ (上下文没提到)
Claim 3: "使用神经网络进行特征学习" → 可推导 ✓ ("自动学习数据的表示" ≈ "特征学习")
``` -->

### Step 3：计算分数

```
Faithfulness = 可推导的 Claim 数 / 总 Claim 数
             = 2 / 3
             = 0.67
```

---

## 完整示例

### 案例 1：高 Faithfulness

```
问题: "Python 是什么？"
上下文: "Python 是一种解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年首次发布"
答案: "Python 是一种解释型的高级编程语言"

→ Claim: "Python 是一种解释型的高级编程语言" → 可推导 ✓
→ Faithfulness = 1/1 = 1.0
```

### 案例 2：低 Faithfulness（幻觉）

```
问题: "Python 是什么？"
上下文: "Python 是一种解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年首次发布"
答案: "Python 是一种编译型语言，由 James Gosling 在 1995 年创建"

→ Claim 1: "Python 是一种编译型语言" → 无法推导 ✗ (上下文说解释型)
→ Claim 2: "由 James Gosling 在 1995 年创建" → 无法推导 ✗ (上下文说 Guido, 1991)
→ Faithfulness = 0/2 = 0.0
```

### 案例 3：部分 Faithfulness

```
问题: "Python 有什么特点？"
上下文: "Python 支持多种编程范式，包括面向对象和函数式编程"
答案: "Python 支持面向对象和函数式编程，同时也支持并发编程"

→ Claim 1: "Python 支持面向对象编程" → 可推导 ✓
→ Claim 2: "Python 支持函数式编程" → 可推导 ✓
→ Claim 3: "Python 支持并发编程" → 无法推导 ✗ (上下文没提到)
→ Faithfulness = 2/3 = 0.67
```

---

## Faithfulness 低的原因与对策

| 原因 | 说明 | 对策 |
|------|------|------|
| 模型过度推理 | 模型用自己的知识"补全"了上下文没有的信息 | 换更强指令遵循的模型，加 prompt 约束 "只根据上下文回答" |
| 上下文不足 | 检索到的信息不够，模型被迫"编造" | 提高 Context Recall（增大 top-k、混合检索） |
| 上下文噪声 | 不相关文档干扰了模型判断 | 提高 Context Precision（Rerank、减少 top-k） |
| 上下文矛盾 | 多个文档信息冲突，模型选了错误的 | 改进检索质量，prompt 中要求"如果信息矛盾请指出" |

---

## Faithfulness vs Answer Relevance

这两个指标容易混淆，但评估的是完全不同的东西：

```
问题: "什么是深度学习？"
上下文: "猫是一种可爱的动物"
答案: "猫很可爱"

Faithfulness = 1.0  ← 答案确实从上下文推导，没瞎编
Answer Relevance = 0.0  ← 但答案和问题毫无关系
```

```
问题: "什么是深度学习？"
上下文: "深度学习是机器学习的一个分支"
答案: "深度学习是人工智能的核心技术，涵盖自然语言处理、计算机视觉等多个领域"

Faithfulness = 0.5  ← 答案部分内容无法从上下文推导
Answer Relevance = 0.9  ← 但答案确实切题
```

**总结**：Faithfulness 管"有没有瞎编"，Answer Relevance 管"有没有跑题"。两者都高才是好答案。
