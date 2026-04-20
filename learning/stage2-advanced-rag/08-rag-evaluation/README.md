# RAG 评估体系 (Day 10-11)

## 概述

RAG 评估用于衡量检索增强生成系统的质量，包括检索质量和生成质量两个维度。

## 核心评估指标

| 指标 | 说明 | 维度 | 理想值 |
|------|------|------|--------|
| **Faithfulness** | 答案是否忠实于检索上下文 | 生成质量 | 越高越好 |
| **Answer Relevance** | 答案与问题的相关性 | 生成质量 | 越高越好 |
| **Context Precision** | 相关文档的排名位置 | 检索质量 | 越高越好 |
| **Context Recall** | 检索到的相关内容比例 | 检索质量 | 越高越好 |
| **Answer Correctness** | 答案与标准答案的匹配度 | 生成质量 | 越高越好 |

### 1. Faithfulness (忠诚度)

衡量生成的答案是否忠实于检索到的上下文。

```
答案: "深度学习是机器学习的一个分支..."
上下文: "深度学习（Deep Learning）是机器学习的一个子领域..."

Faithfulness = 答案中的陈述是否都能从上下文推断 → 0~1
```

### 2. Answer Relevance (答案相关性)

评估答案与问题的匹配程度，不完整或冗余的答案得分较低。

```
问题: "什么是深度学习？"
答案1: "深度学习是机器学习的一个分支，使用神经网络..."
       → 高相关性 (1.0)

答案2: "深度学习很重要，机器学习也很重要，AI是未来..."
       → 低相关性 (0.3)
```

### 3. Context Precision (上下文精确度)

评估所有相关文档是否排名靠前。

```
理想情况: 所有相关文档都出现在 top-k 位置
Context Precision = 相关文档在 top-k 中的平均排名得分
```

### 4. Context Recall (上下文召回率)

衡量检索到的内容是否覆盖了正确答案所需的信息。

```
正确答案: "深度学习由 Hinton 等人在 2006 年提出..."
检索到的上下文: "深度学习是机器学习的一个分支..."

Context Recall = 0.5（只覆盖了部分信息）
```

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