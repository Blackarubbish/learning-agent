"""
RAGAs 框架基础 — 动手实现版

学习目标：
1. 构造 RAGAs 评估数据集
2. 配置评估 LLM 和 Embeddings
3. 逐个运行 5 个核心指标并观察结果

运行：
    cd learning/stage2-advanced-rag/08-rag-evaluation/practice
    uv run python starter.py

完成后对照 solution.py 查看参考实现。
"""
from common import load_dotenv_if_needed, get_or_create_llm, section, check, summary, reset

load_dotenv_if_needed()

# ============================================================
# TODO 1: 创建评估用的 LLM（温度设为 0）
# 提示：使用 get_or_create_llm()
# ============================================================
# evaluator_llm = ???

# ============================================================
# TODO 2: 创建评估用的 Embeddings
# 提示：RAGAs 的 AnswerRelevancy 需要 OpenAIEmbeddings 来计算语义相似度
# 智谱接口兼容 OpenAI，使用：
#   from langchain_openai import OpenAIEmbeddings
#   model="embedding-3", base_url="https://open.bigmodel.cn/api/paas/v4"
#   api_key 用 os.getenv("ZHIPU_API_KEY")
# ============================================================
# evaluator_embeddings = ???

# ============================================================
# TODO 3: 构造评估数据集
# 提示：使用 ragas.SingleTurnSample，每条样本包含：
#   - user_input: 用户问题
#   - response: 模型回答
#   - retrieved_contexts: 检索到的上下文列表
#   - reference: 参考答案（ground truth）
#
# 设计 3-4 条样本覆盖不同场景：
#   1. 高质量回答（所有指标应高）
#   2. 幻觉回答（Faithfulness 应低）
#   3. 答非所问（Answer Relevancy 应低）
#   4. 检索不足（Context Recall 应低）
# ============================================================
# from ragas import EvaluationDataset, SingleTurnSample
# samples = [
#     SingleTurnSample(
#         user_input="...",
#         response="...",
#         retrieved_contexts=["..."],
#         reference="...",
#     ),
#     # 补充更多样本...
# ]
# dataset = EvaluationDataset(samples=samples)


# ============================================================
# TODO 4: 逐个运行指标
# 提示：使用 ragas.evaluate()
#   5 个核心指标：Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall, AnswerCorrectness
#   from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall, AnswerCorrectness
# ============================================================
# from ragas import evaluate
# result = evaluate(dataset, metrics=[Faithfulness()], llm=evaluator_llm, embeddings=evaluator_embeddings)


# ============================================================
# TODO 5: 汇总运行所有指标
# 提示：将所有指标传入 metrics=[] 列表
# ============================================================


# ============================================================
# 自检区
# ============================================================
if __name__ == "__main__":
    reset()

    # TODO: 补充自检条件
    # check("数据集包含至少 3 条样本", ...)
    # check("Faithfulness 对幻觉案例得分低", ...)

    summary()
    print("提示：完成后对照 solution.py 查看参考实现")