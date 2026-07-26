"""
RAGAs 框架基础 - 用手工数据集跑通 5 个核心指标

学习目标：
1. 理解 RAGAs 的数据格式要求
2. 跑通 Faithfulness / Answer Relevancy / Context Precision / Context Recall / Answer Correctness
3. 观察每个指标的输出，建立直觉

运行：
  uv run python 01_ragas_basics.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

# suppress deprecation warnings - these imports work fine in ragas 0.4.x
import warnings

from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import (
    AnswerCorrectness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

warnings.filterwarnings("ignore", category=DeprecationWarning, module="ragas")
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# === 配置 LLM ===
# RAGAs 内部用 LLM 做评估（拆分 Claims、判断可推导性等）
# 这里用 DeepSeek API，通过 OpenAI 兼容接口调用
evaluator_llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0,
)

# RAGAs 的 AnswerRelevancy 需要 Embeddings 来计算语义相似度
# 智谱 OpenAI 兼容接口的 embedding 模型名是 embedding-3
evaluator_embeddings = OpenAIEmbeddings(
    model="embedding-3",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key=os.getenv("ZHIPU_API_KEY"),
)


# === 构造评估数据集 ===
# RAGAs 的数据格式：每条样本包含 user_input / response / retrieved_contexts / reference
# 不同指标需要的字段不同：
#   - Faithfulness: user_input, response, retrieved_contexts
#   - AnswerRelevancy: user_input, response
#   - ContextPrecision: user_input, reference, retrieved_contexts
#   - ContextRecall: user_input, response, reference, retrieved_contexts
#   - AnswerCorrectness: user_input, response, reference

samples = [
    # 案例 1：高质量回答 - 所有指标应该都很高
    SingleTurnSample(
        user_input="什么是深度学习？",
        response="深度学习是机器学习的一个分支，使用多层神经网络自动学习数据的表示。",
        retrieved_contexts=[
            "深度学习（Deep Learning）是机器学习的一个子领域，使用多层神经网络自动学习数据的表示。",
            "神经网络是受生物神经系统启发的一种计算模型，是深度学习的基础。",
        ],
        reference="深度学习是机器学习的一个子领域，使用多层神经网络自动学习数据的表征。",
    ),
    # 案例 2：幻觉回答 - Faithfulness 应该低
    SingleTurnSample(
        user_input="Python 是什么？",
        response="Python 是一种编译型编程语言，由 James Gosling 在 1995 年创建。",
        retrieved_contexts=[
            "Python 是一种解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年首次发布。",
        ],
        reference="Python 是一种解释型的高级编程语言，由 Guido van Rossum 于 1991 年创建。",
    ),
    # 案例 3：答非所问 - Answer Relevancy 应该低
    SingleTurnSample(
        user_input="什么是深度学习？",
        response="猫是一种可爱的动物，喜欢抓老鼠。",
        retrieved_contexts=[
            "猫是一种可爱的动物，喜欢抓老鼠。狗是人类的好朋友。",
        ],
        reference="深度学习是机器学习的一个分支。",
    ),
    # 案例 4：检索覆盖不足 - Context Recall 应该低
    SingleTurnSample(
        user_input="FAISS 有什么特点？",
        response="FAISS 是 Facebook 开发的向量检索库。",
        retrieved_contexts=[
            "FAISS 是 Facebook AI Research 开发的库。",
        ],
        reference="FAISS 是 Facebook 开发的向量相似度搜索库，支持 GPU 加速和大规模向量检索。",
    ),
    # 案例 5：检索排序差 - Context Precision 应该低
    SingleTurnSample(
        user_input="什么是 Transformer？",
        response="Transformer 是一种深度学习架构。",
        retrieved_contexts=[
            "Python 是一种广泛使用的高级编程语言。",
            "Docker 是一种容器化技术。",
            "Transformer 架构是现代大语言模型的基础，采用自注意力机制。",
        ],
        reference="Transformer 是一种基于自注意力机制的深度学习架构，是现代大语言模型的基础。",
    ),
]

dataset = EvaluationDataset(samples=samples)


# === 逐个指标运行评估 ===
# 先逐个跑，观察每个指标的输出；最后一起跑看汇总


def run_single_metric(metric, name):
    print(f"\n{'=' * 60}")
    print(f"指标: {name}")
    print(f"{'=' * 60}")
    result = evaluate(
        dataset,
        metrics=[metric],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )
    print(f"结果: {result}")
    return result


print("RAGAs 框架基础 - 5 个核心指标逐个跑通\n")
print("数据集: 5 条手工样本，覆盖不同质量场景")
print("  案例1: 高质量 → 所有指标应偏高")
print("  案例2: 幻觉 → Faithfulness 应低")
print("  案例3: 答非所问 → Answer Relevancy 应低")
print("  案例4: 检索不足 → Context Recall 应低")
print("  案例5: 排序差 → Context Precision 应低")

# 1. Faithfulness
r1 = run_single_metric(Faithfulness(), "Faithfulness (忠诚度)")

# 2. Answer Relevancy
# DeepSeek 不支持 n>1（批量生成），需要设 generate_n=1
ar_metric = AnswerRelevancy()
ar_metric.generate_n = 1  # 只生成 1 个反向问题（默认是 3 个）
r2 = run_single_metric(ar_metric, "Answer Relevancy (答案相关性)")

# 3. Context Precision
r3 = run_single_metric(ContextPrecision(), "Context Precision (上下文精确度)")

# 4. Context Recall
r4 = run_single_metric(ContextRecall(), "Context Recall (上下文召回率)")

# 5. Answer Correctness
r5 = run_single_metric(AnswerCorrectness(), "Answer Correctness (答案正确性)")


# === 汇总所有指标 ===
print(f"\n{'=' * 60}")
print("汇总: 所有指标一起跑")
print(f"{'=' * 60}")

ar_metric_full = AnswerRelevancy()
ar_metric_full.generate_n = 1
all_metrics = [
    Faithfulness(),
    ar_metric_full,
    ContextPrecision(),
    ContextRecall(),
    AnswerCorrectness(),
]

full_result = evaluate(
    dataset,
    metrics=all_metrics,
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)

print("\n最终结果:")
print(full_result)

# 转为 pandas 方便查看
try:
    df = full_result.to_pandas()
    print("\n逐样本详情:")
    print(df.to_string())
except Exception:
    pass
