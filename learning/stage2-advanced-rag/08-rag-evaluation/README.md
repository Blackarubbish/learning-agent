# RAG 评估体系 (Day 10-11)

## 概述

RAG 评估用于衡量检索增强生成系统的质量，包括检索质量和生成质量两个维度。

## 为什么需要 RAG 评估？

前面学了查询变换（06章）和混合检索+Rerank（07章），我们有了更复杂的 RAG 系统。但问题来了：

**你怎么知道这些优化真的有效？**

没有评估，优化就是盲人摸象。你加了 Rerank，Faithfulness 提高了还是降低了？你换了 Embedding 模型，Context Recall 变好了还是变差了？没有量化指标，你只能凭感觉说"好像好了一点"。

RAG 评估的本质是：**用可量化的指标，告诉你系统哪里好、哪里差、该往哪个方向优化。**

## 评估的两个维度

RAG = Retrieval + Generation，评估自然也分两个维度：

```
用户问题 → [检索] → 检索到的上下文 → [生成] → 最终答案
              ↑                          ↑
          检索质量评估                 生成质量评估
```

- **检索质量**：检索到的东西对不对？（垃圾进 → 垃圾出）
- **生成质量**：生成的答案好不好？（好材料也可能做坏菜）

---

## 核心评估指标

| 指标 | 说明 | 维度 | 直觉理解 |
|------|------|------|----------|
| **Context Precision** | 相关文档的排名位置 | 检索质量 | 检索结果的"排序质量" |
| **Context Recall** | 检索到的相关内容比例 | 检索质量 | 检索结果的"覆盖度" |
| **Faithfulness** | 答案是否忠实于检索上下文 | 生成质量 | 答案有没有"瞎编" |
| **Answer Relevance** | 答案与问题的相关性 | 生成质量 | 答案有没有"答非所问" |
| **Answer Correctness** | 答案与标准答案的匹配度 | 生成质量 | 答案的"正确程度" |

### 容易混淆的指标对比

**Faithfulness vs Answer Relevance**：
- Faithfulness：答案**可以**从上下文中推导出来 → 不瞎编
- Answer Relevance：答案**回应了**用户的问题 → 不跑题

```
问题："什么是深度学习？"
上下文："猫是一种可爱的动物"
答案："猫很可爱"

Faithfulness = 1.0（答案确实可以从上下文推导，没瞎编）
Answer Relevance = 0.0（答案和问题毫无关系）
```

**Context Precision vs Context Recall**：
- Precision：排在前面的文档中，有多少是相关的？（重排序质量）
- Recall：所有需要的信息，检索到了多少？（覆盖度）

这是经典的 Precision/Recall 权衡：检索 100 篇文档，Recall 很高但 Precision 很低；只检索 1 篇最相关的，Precision 很高但 Recall 很低。

---

### 1. Faithfulness (忠诚度)

衡量生成的答案是否忠实于检索到的上下文。

```
答案: "深度学习是机器学习的一个分支..."
上下文: "深度学习（Deep Learning）是机器学习的一个子领域..."

Faithfulness = 答案中的陈述是否都能从上下文推断 → 0~1
```

**计算方式**（RAGAs 的做法）：
1. 将答案拆分为若干独立陈述（claims）
2. 对每个陈述，判断它是否能从上下文中推导出来
3. Faithfulness = 可推导的陈述数 / 总陈述数

```
答案: "深度学习是机器学习的分支，由 Hinton 在 2006 年提出"
→ 拆分为两个陈述：
  Claim 1: "深度学习是机器学习的分支" → 上下文中可推导 ✓
  Claim 2: "由 Hinton 在 2006 年提出" → 上下文中找不到 ✗

Faithfulness = 1/2 = 0.5
```

**Faithfulness 低意味着什么？** 答案中有幻觉（hallucination），模型编造了上下文中没有的信息。

### 2. Answer Relevance (答案相关性)

评估答案与问题的匹配程度，不完整或冗余的答案得分较低。

```
问题: "什么是深度学习？"
答案1: "深度学习是机器学习的一个分支，使用神经网络..."
       → 高相关性 (1.0)

答案2: "深度学习很重要，机器学习也很重要，AI是未来..."
       → 低相关性 (0.3)
```

**计算方式**（RAGAs 的做法）：
1. 从答案中反向生成可能的问题
2. 计算生成的问题与原始问题的语义相似度
3. 取平均值作为 Answer Relevance

**直觉**：如果答案是切题的，从答案反推应该能得到相似的问题；如果答案跑题了，反推出来的问题也会和原问题不同。

### 3. Context Precision (上下文精确度)

评估所有相关文档是否排名靠前。

```
理想情况: 所有相关文档都出现在 top-k 位置
Context Precision = 相关文档在 top-k 中的平均排名得分
```

**计算方式**：

给定检索结果列表，对每个位置计算 precision@k，然后只对相关文档位置的 precision 取平均：

```
检索结果: [相关, 不相关, 相关, 不相关, 相关]
位置:        1       2       3       4       5

precision@1 = 1/1 = 1.0  (相关)
precision@3 = 2/3 = 0.67 (前3个中2个相关)
precision@5 = 3/5 = 0.6  (前5个中3个相关)

Context Precision = (1.0 + 0.67 + 0.6) / 3 = 0.76
                 = 只对相关文档位置的 precision 取平均
```

**Context Precision 低意味着什么？** 相关文档被排在了不相关文档后面，Rerank 或排序策略需要改进。

### 4. Context Recall (上下文召回率)

衡量检索到的内容是否覆盖了正确答案所需的信息。

```
正确答案: "深度学习由 Hinton 等人在 2006 年提出..."
检索到的上下文: "深度学习是机器学习的一个分支..."

Context Recall = 0.5（只覆盖了部分信息）
```

**计算方式**（RAGAs 的做法）：
1. 将标准答案拆分为若干关键陈述
2. 对每个陈述，判断它是否能从检索到的上下文中推导出来
3. Context Recall = 可推导的陈述数 / 总陈述数

**Context Recall 低意味着什么？** 检索漏掉了关键信息，需要改进检索策略（增加 top-k、换 Embedding 模型、用混合检索等）。

### 5. Answer Correctness (答案正确性)

答案与标准答案的匹配度，综合了语义相似度和事实重叠。

```
标准答案: "深度学习是机器学习的一个分支，由 Hinton 在 2006 年提出"
生成答案: "深度学习是机器学习的子领域，Hinton 在 2006 年提出了这个概念"

Answer Correctness ≈ 0.85（语义相似 + 大部分事实正确）
```

**计算方式**：加权组合
- 语义相似度（Embedding 余弦相似度）
- 事实重叠度（类似 Faithfulness 的 claim 匹配）

**Answer Correctness 需要标准答案**，而 Faithfulness 不需要。

---

## 指标与优化方向的对应关系

| 指标低 | 诊断 | 优化方向 |
|--------|------|----------|
| Context Recall 低 | 检索覆盖不足 | 增大 top-k、换 Embedding、混合检索 |
| Context Precision 低 | 检索排序差 | Rerank、调优检索参数 |
| Faithfulness 低 | 模型幻觉严重 | 换更强模型、加 system prompt 约束、减少 top-k |
| Answer Relevance 低 | 答案跑题 | 优化 prompt、查询变换 |
| Answer Correctness 低 | 答案整体质量差 | 综合优化检索 + 生成 |

---

## RAGAs 评估框架

### 安装

```bash
pip install ragas langchain-openai
```

### 基本使用

```python
from ragas import Dataset
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas import evaluate
from langchain_openai import ChatOpenAI

# 准备评估数据
eval_data = {
    "user_input": ["什么是深度学习？", "谁提出了深度学习？"],
    "retrieved_contexts": [
        ["深度学习是机器学习的一个分支..."],
        ["Hinton 在 2006 年提出了深度学习..."]
    ],
    "response": ["深度学习是机器学习的一个分支...", "深度学习是由 Hinton 等人提出的..."],
    "reference": ["深度学习是机器学习的一个分支，由 Hinton 等人在 2006 年提出...", "Hinton 等人在 2006 年提出了深度学习概念..."]
}

dataset = Dataset.from_dict(eval_data)

# 配置评估器 LLM
evaluator_llm = ChatOpenAI(model="gpt-4o-mini")

# 运行评估
result = evaluate(
    dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ],
    llm=evaluator_llm
)

print(result)
```

### 生成评估测试集

```python
from ragas.testset import generate_testset
from langchain_openai import ChatOpenAI

# 使用文档生成测试问题
documents = loader.load()

testset_generator = generate_testset(
    llm=ChatOpenAI(model="gpt-4o-mini"),
    embedding_model=OpenAIEmbeddings()
)

# 生成 50 个测试问题
testset = testset_generator.generate(
    documents=documents,
    num_samples=50,
    raise_errors=False
)

# 保存测试集
testset.to_pandas().to_csv("evaluation_testset.csv", index=False)
```

---

## DeepEval 评估框架

### 安装

```bash
pip install deepeval
```

### 基本使用

```python
from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
from deepeval.testcase import LLMTestCase

# 创建测试用例
test_case = LLMTestCase(
    input="什么是深度学习？",
    expected_output="深度学习是机器学习的一个分支...",
    actual_output="深度学习是机器学习的一个分支，使用神经网络模型...",
    retrieval_context=["深度学习是机器学习的一个分支...", "神经网络是深度学习的基础..."]
)

# 配置指标
faithfulness_metric = FaithfulnessMetric(threshold=0.5)
relevancy_metric = AnswerRelevancyMetric(threshold=0.5)

# 运行评估
evaluate([test_case], [faithfulness_metric, relevancy_metric])
```

### RAGAs vs DeepEval 对比

| 维度 | RAGAs | DeepEval |
|------|-------|----------|
| 设计理念 | 数据集驱动，批量评估 | 测试用例驱动，类似单元测试 |
| 数据格式 | Dataset (dict-like) | LLMTestCase 对象 |
| 指标丰富度 | 专注 RAG 指标 | 更广泛（含 bias, toxicity 等） |
| 集成方式 | 与 LangChain 深度集成 | 独立框架，也可集成 LangChain |
| 测试集生成 | 内置生成器 | 需要外部准备 |
| 适用场景 | RAG 系统整体评估 | RAG + 更广泛的 LLM 评估 |

---

## RAG 评估最佳实践

### 1. 建立评估流水线

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness,
)

def evaluate_rag_system(rag_system, test_questions):
    """评估 RAG 系统"""
    results = []

    for question in test_questions:
        # 获取系统回答
        response = rag_system.ask(question)

        # 获取检索到的上下文
        contexts = rag_system.retrieve(question)

        # 获取标准答案（如果有）
        reference = rag_system.get_reference(question)

        results.append({
            "user_input": question,
            "response": response.answer,
            "retrieved_contexts": contexts,
            "reference": reference
        })

    # 创建数据集
    dataset = Dataset.from_dict(results)

    # 评估
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
        answer_correctness  # 如果有 reference
    ]

    eval_result = evaluate(dataset, metrics=metrics)
    return eval_result
```

### 2. 对比优化前后效果

```python
def compare_optimizations(baseline_system, optimized_system, test_set):
    """对比优化前后的系统性能"""

    print("=" * 60)
    print("Baseline System Evaluation")
    print("=" * 60)
    baseline_result = evaluate_rag_system(baseline_system, test_set)
    print(f"Faithfulness: {baseline_result['faithfulness']}")
    print(f"Answer Relevance: {baseline_result['answer_relevancy']}")

    print("\n" + "=" * 60)
    print("Optimized System Evaluation")
    print("=" * 60)
    optimized_result = evaluate_rag_system(optimized_system, test_set)
    print(f"Faithfulness: {optimized_result['faithfulness']}")
    print(f"Answer Relevance: {optimized_result['answer_relevancy']}")

    print("\n" + "=" * 60)
    print("Improvement")
    print("=" * 60)
    for metric in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
        baseline = baseline_result[metric]
        optimized = optimized_result[metric]
        improvement = (optimized - baseline) / baseline * 100
        print(f"{metric}: {improvement:+.1f}%")
```

### 3. 评估指标解读

| 指标范围 | 质量等级 | 建议 |
|----------|----------|------|
| 0.9 - 1.0 | 优秀 | 系统质量很高 |
| 0.7 - 0.9 | 良好 | 可以接受，可能有轻微问题 |
| 0.5 - 0.7 | 一般 | 需要改进 |
| 0.0 - 0.5 | 差 | 严重问题，需要重新设计 |

### 4. 评估驱动的优化循环

```
         ┌──────────────────────────────────┐
         │                                  │
         ▼                                  │
    运行评估 ──→ 分析低分指标 ──→ 针对性优化 ──┘
         │
         ▼
    指标达标？── 是 ──→ 上线
         │
         否
         │
         ▼
    继续优化循环
```

**示例优化路径**：

1. 初始评估：Context Recall = 0.4, Faithfulness = 0.8
2. 诊断：检索覆盖不足（Context Recall 低）
3. 优化：增大 top-k，引入混合检索
4. 再评估：Context Recall = 0.7, Faithfulness = 0.75
5. 诊断：Recall 提升但 Faithfulness 略降（更多上下文引入了噪声）
6. 优化：加入 Rerank 过滤不相关文档
7. 再评估：Context Recall = 0.72, Faithfulness = 0.85 ✓

---

## 实践任务

1. 安装 RAGAs
2. 使用现有文档生成评估测试集
3. 对比 Naive RAG 和 Advanced RAG 的评估结果
4. 分析各指标，识别系统瓶颈

---

## 参考资源

- [RAGAs 官方文档](https://docs.ragas.io/en/stable/)
- [RAGAs 指标解释(CSDN)](https://blog.csdn.net/qq_41913559/article/details/143055531)
- [RAG评价框架RAGAs完整使用指南](https://blog.csdn.net/gitblog_01126/article/details/157111695)
- [DeepEval 官方文档](https://github.com/confident-ai/deepeval)
