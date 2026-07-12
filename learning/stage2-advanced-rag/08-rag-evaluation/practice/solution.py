"""
RAGAs 框架基础 — 参考实现（使用 common/ 模块消除 boilerplate）

对比 starter.py：
- infrastructure 从 ~20 行减少到 3 行
- 添加了自检断言
- 注释解释"为什么"而非"做什么"

运行：
    cd learning/stage2-advanced-rag/08-rag-evaluation/practice
    uv run python solution.py
"""

import os
import warnings

from common import load_dotenv_if_needed, get_or_create_llm, section, check, summary, reset

load_dotenv_if_needed()

# 评估 LLM：temperature=0 保证评估结果可复现（DeepSeek 作为评判模型）
evaluator_llm = get_or_create_llm(provider="deepseek", temperature=0)

# RAGAs 的 AnswerRelevancy 内部需要 Embeddings 计算语义相似度
# 用智谱 OpenAI 兼容接口（model="embedding-3"）而非 common.ZhipuEmbeddings，
# 因为 Ragas 要求传入 langchain_openai.OpenAIEmbeddings 实例
from langchain_openai import OpenAIEmbeddings

evaluator_embeddings = OpenAIEmbeddings(
    model="embedding-3",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key=os.getenv("ZHIPU_API_KEY"),
)

from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    AnswerCorrectness,
)

# 抑制 ragas 0.4.x 的弃用警告（不影响功能）
warnings.filterwarnings("ignore", category=DeprecationWarning, module="ragas")

# ============================================================
# 构造评估数据集
# 5 条样本覆盖不同质量场景，让我们看清每个指标在测什么
# ============================================================
section("构造数据集")

samples = [
    # 案例 1：高质量 —— 回答完全基于上下文，语义匹配
    SingleTurnSample(
        user_input="什么是深度学习？",
        response="深度学习是机器学习的一个分支，使用多层神经网络自动学习数据的表示。",
        retrieved_contexts=[
            "深度学习（Deep Learning）是机器学习的一个子领域，使用多层神经网络自动学习数据的表示。",
            "神经网络是受生物神经系统启发的一种计算模型，是深度学习的基础。",
        ],
        reference="深度学习是机器学习的一个子领域，使用多层神经网络自动学习数据的表征。",
    ),
    # 案例 2：幻觉 —— response 说的跟 retrieved_contexts 完全不同
    # 预期：Faithfulness 低（回答无法从上下文推导出来）
    SingleTurnSample(
        user_input="Python 是什么？",
        response="Python 是一种编译型编程语言，由 James Gosling 在 1995 年创建。",
        retrieved_contexts=[
            "Python 是一种解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年首次发布。",
        ],
        reference="Python 是一种解释型的高级编程语言，由 Guido van Rossum 于 1991 年创建。",
    ),
    # 案例 3：答非所问 —— response 跟问题完全无关
    # 预期：Answer Relevancy 低
    SingleTurnSample(
        user_input="什么是深度学习？",
        response="猫是一种可爱的动物，喜欢抓老鼠。",
        retrieved_contexts=["猫是一种可爱的动物，喜欢抓老鼠。狗是人类的好朋友。"],
        reference="深度学习是机器学习的一个分支。",
    ),
    # 案例 4：检索覆盖不足 —— 检索到的上下文缺少关键信息
    # 预期：Context Recall 低（reference 中的信息在 retrieved_contexts 里找不到）
    SingleTurnSample(
        user_input="FAISS 有什么特点？",
        response="FAISS 是 Facebook 开发的向量检索库。",
        retrieved_contexts=["FAISS 是 Facebook AI Research 开发的库。"],
        reference="FAISS 是 Facebook 开发的向量相似度搜索库，支持 GPU 加速和大规模向量检索。",
    ),
    # 案例 5：检索排序差 —— 无关文档排在相关文档前面
    # 预期：Context Precision 低（不相关的上下文在相关上下文之前）
    SingleTurnSample(
        user_input="什么是 Transformer？",
        response="Transformer 是一种深度学习架构。",
        retrieved_contexts=[
            "Python 是一种广泛使用的高级编程语言。",  # 不相关，排在前面
            "Docker 是一种容器化技术。",  # 不相关
            "Transformer 架构是现代大语言模型的基础，采用自注意力机制。",  # 相关但排在后面
        ],
        reference="Transformer 是一种基于自注意力机制的深度学习架构，是现代大语言模型的基础。",
    ),
]

dataset = EvaluationDataset(samples=samples)
check("数据集包含 5 条样本", len(samples) == 5, f"实际 {len(samples)} 条")
check(
    "案例2是幻觉场景",
    "James Gosling" in samples[1].response,
    "案例2应包含错误信息 James Gosling（幻觉）",
    fix="案例2的 response 应是故意写错的幻觉回答",
)


def run_metric(metric, name: str):
    """运行单个指标评估——逐个观察便于建立直觉"""
    section(f"指标: {name}")
    result = evaluate(dataset, metrics=[metric], llm=evaluator_llm, embeddings=evaluator_embeddings)
    print(f"  结果: {result}")
    return result


run_metric(Faithfulness(), "Faithfulness（忠实度）")

# DeepSeek 不支持 n>1 批量生成，AnswerRelevancy 需要设 generate_n=1
ar_metric = AnswerRelevancy()
ar_metric.generate_n = 1
run_metric(ar_metric, "Answer Relevancy（答案相关性）")

run_metric(ContextPrecision(), "Context Precision（上下文精确度）")
run_metric(ContextRecall(), "Context Recall（上下文召回率）")
run_metric(AnswerCorrectness(), "Answer Correctness（答案正确性）")

# ============================================================
# 汇总评估
# ============================================================
section("汇总 — 所有指标一起跑")

ar_full = AnswerRelevancy()
ar_full.generate_n = 1

full_result = evaluate(
    dataset,
    metrics=[Faithfulness(), ar_full, ContextPrecision(), ContextRecall(), AnswerCorrectness()],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)
print(full_result)

# ============================================================
# 自检区
# ============================================================
if __name__ == "__main__":
    reset()

    checkpoint_2_index = 1  # 幻觉案例是 samples[1]
    checkpoint_3_index = 2  # 答非所问案例是 samples[2]

    # 运行评估后检查分数合理性
    try:
        df = full_result.to_pandas()
        faithfulness_scores = df["faithfulness"].tolist()

        check(
            "至少评估了 5 个指标",
            len(df.columns) >= 5,
            f"实际列数: {len(df.columns)}",
            fix="检查 metrics 列表是否包含 5 个指标",
        )

        # 幻觉案例的 Faithfulness 应该最低
        check(
            "幻觉案例的 Faithfulness 不是最高的",
            faithfulness_scores[checkpoint_2_index] < 0.5
            or faithfulness_scores[checkpoint_2_index] <= min(faithfulness_scores),
            f"案例2 Faithfulness={faithfulness_scores[1]:.3f}，预期应很低",
            fix="案例2是故意写错的幻觉回答，Faithfulness 应该接近 0",
        )

    except Exception as e:
        check("结果可转为 DataFrame", False, str(e), fix="检查 ragas 版本是否支持 to_pandas()")

    summary()
