"""
DeepEval 框架基础 - 用手工数据集跑通核心指标

学习目标：
1. 理解 DeepEval 的测试用例格式（LLMTestCase）
2. 跑通 Faithfulness / Answer Relevancy / ContextualPrecision / ContextualRecall
3. 对比 RAGAs 和 DeepEval 的使用差异

运行：
  uv run python 02_deepeval_basics.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)
from deepeval.test_case import LLMTestCase

# === 配置 LLM ===
# DeepEval 通过 OpenAI 兼容接口调用
os.environ["OPENAI_API_KEY"] = os.getenv("DEEPSEEK_API_KEY")
os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com/v1"

# DeepEval 的 model 参数需要指定模型名
MODEL = "deepseek-chat"


# === 构造测试用例 ===
# DeepEval 用 LLMTestCase 对象，字段含义：
#   - input: 用户问题
#   - actual_output: RAG 系统生成的答案
#   - expected_output: 标准答案
#   - retrieval_context: 检索到的上下文列表

test_cases = [
    # 案例 1：高质量回答
    LLMTestCase(
        input="什么是深度学习？",
        actual_output="深度学习是机器学习的一个分支，使用多层神经网络自动学习数据的表示。",
        expected_output="深度学习是机器学习的一个子领域，使用多层神经网络自动学习数据的表征。",
        retrieval_context=[
            "深度学习（Deep Learning）是机器学习的一个子领域，使用多层神经网络自动学习数据的表示。",
            "神经网络是受生物神经系统启发的一种计算模型，是深度学习的基础。",
        ],
    ),
    # 案例 2：幻觉回答
    LLMTestCase(
        input="Python 是什么？",
        actual_output="Python 是一种编译型编程语言，由 James Gosling 在 1995 年创建。",
        expected_output="Python 是一种解释型的高级编程语言，由 Guido van Rossum 于 1991 年创建。",
        retrieval_context=[
            "Python 是一种解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年首次发布。",
        ],
    ),
    # 案例 3：答非所问
    LLMTestCase(
        input="什么是深度学习？",
        actual_output="猫是一种可爱的动物，喜欢抓老鼠。",
        expected_output="深度学习是机器学习的一个分支。",
        retrieval_context=[
            "猫是一种可爱的动物，喜欢抓老鼠。狗是人类的好朋友。",
        ],
    ),
    # 案例 4：检索覆盖不足
    LLMTestCase(
        input="FAISS 有什么特点？",
        actual_output="FAISS 是 Facebook 开发的向量检索库。",
        expected_output="FAISS 是 Facebook 开发的向量相似度搜索库，支持 GPU 加速和大规模向量检索。",
        retrieval_context=[
            "FAISS 是 Facebook AI Research 开发的库。",
        ],
    ),
    # 案例 5：检索排序差
    LLMTestCase(
        input="什么是 Transformer？",
        actual_output="Transformer 是一种深度学习架构。",
        expected_output="Transformer 是一种基于自注意力机制的深度学习架构，是现代大语言模型的基础。",
        retrieval_context=[
            "Python 是一种广泛使用的高级编程语言。",
            "Docker 是一种容器化技术。",
            "Transformer 架构是现代大语言模型的基础，采用自注意力机制。",
        ],
    ),
]


# === 配置指标 ===
# DeepEval 的每个指标都有 threshold 参数：低于此阈值判定为 fail
# include_reason=True 会让指标输出判断理由

metrics = [
    FaithfulnessMetric(
        model=MODEL,
        threshold=0.5,
        include_reason=True,
    ),
    AnswerRelevancyMetric(
        model=MODEL,
        threshold=0.5,
        include_reason=True,
    ),
    ContextualPrecisionMetric(
        model=MODEL,
        threshold=0.5,
        include_reason=True,
    ),
    ContextualRecallMetric(
        model=MODEL,
        threshold=0.5,
        include_reason=True,
    ),
]


# === 运行评估 ===
print("DeepEval 框架基础 - 核心指标跑通\n")
print("数据集: 5 条手工样本（与 RAGAs 脚本相同）")
print("指标: Faithfulness / Answer Relevancy / ContextualPrecision / ContextualRecall\n")

result = evaluate(test_cases=test_cases, metrics=metrics)

print(f"\n{'=' * 60}")
print("评估完成")
print(f"{'=' * 60}")
