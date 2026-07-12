"""批处理优化 — 用更少的 API 调用完成更多工作

核心学习点：
  - embeddings.embed_documents(texts) 本身就是批处理，你从 ch04 就在用
  - 性能差距来自网络往返（RTT），不是服务端计算速度
  - llm.batch() ≠ Embedding 批处理：前者是并发 N 次调用，后者是合并为 1 次调用
  - batch_size 收益递减：1→10 省 9 次 RTT，10→50 的边际收益大幅下降

运行：
  unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
  PYTHONPATH=. python learning/stage4-performance/22-batch/practice/starter.py
"""

import math
import time

from langchain_core.messages import HumanMessage, SystemMessage

from common import get_or_create_embeddings, get_or_create_llm, load_dotenv_if_needed, reset
from common.check import check, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)
embeddings = get_or_create_embeddings()

TEXTS = [
    "RAG（检索增强生成）结合信息检索和文本生成，先检索相关文档再作为上下文提供给LLM生成答案。",
    "ReAct是Reasoning+Acting的Agent架构，LLM交替进行推理和行动。",
    "Function Calling用JSON Schema定义工具，LLM输出结构化调用请求。",
    "Redis是开源内存数据结构存储，常用作缓存和消息队列。",
    "cProfile是Python内置性能分析器，统计函数调用次数和耗时。",
    "异步编程使用协程和事件循环，在I/O等待时切换到其他任务。",
    "FAISS是Facebook开源的向量相似度搜索库。",
    "语义缓存用Embedding相似度匹配，精确缓存用哈希匹配。",
    "BM25是一种基于词频的排序算法，属于TF-IDF的改进版本。",
    "RRF（倒数排名融合）把多种检索结果按排名取倒数求和。",
    "LangChain是用于构建LLM应用的开源框架。",
    "Milvus是分布式向量数据库，支持增删改查和属性过滤。",
    "Docker是一个容器化平台，用于打包和部署应用。",
    "Kubernetes是容器编排平台，管理容器集群的部署和扩展。",
    "Python的GIL限制了同一进程内多线程的并行执行。",
    "微服务架构将应用拆分为独立的小服务，每个服务专注于单一功能。",
    "GraphQL是一种API查询语言，客户端可以精确指定需要的数据。",
    "WebSocket是一种全双工通信协议，适合实时应用。",
    "OAuth2.0是一种授权框架，允许第三方应用获取有限的资源访问权限。",
    "JWT（JSON Web Token）是一种紧凑的令牌格式，用于在各方之间安全传输信息。",
    "事件驱动架构通过事件的发布和订阅实现服务间的松耦合。",
    "CI/CD是持续集成和持续部署的实践，自动化软件的构建测试和发布流程。",
    "负载均衡将流量分配到多个服务器，提升系统的可用性和扩展性。",
    "数据库索引是一种数据结构，用于加速数据的查询操作。",
    "缓存穿透是指查询一个不存在的数据，由于缓存不命中而直接访问数据库。",
    "消息队列用于在服务之间异步传递消息，实现解耦和削峰填谷。",
    "分布式事务涉及多个独立的数据源，需要保证跨节点的数据一致性。",
    "CAP定理指出分布式系统无法同时满足一致性可用性和分区容错性。",
    "幂等性是指同一个操作执行多次产生的结果和执行一次相同。",
    "乐观锁假设数据冲突的概率较低，在提交时检查版本号决定是否成功。",
]

# ═══════════════════════════════════════════════════════════════
# TODO 1: 量化批处理的真实收益
# ═══════════════════════════════════════════════════════════════
#
# 从 ch04 开始你就在用 embeddings.embed_documents(texts)，传的就是 list。
# 如果传 [text]（list 里只有 1 条）和传 [text1, ..., text30]，耗时差多少？
#
# 两者调用的是同一个函数，区别仅在于 list 的长度。
# 所以性能差距不是"算法差异"，纯粹是"发了几次 HTTP 请求"。
#
# 任务 A: 实现 measure_embedding() — 按 batch_size 分批调用 embed_documents
# 任务 B: 实现 run_embedding_benchmark() — 跑 3 种 batch_size 的对比表
# 任务 C: 运行后想一下 —— 单条均摊耗时为什么随 batch_size 增大而下降？
#         省的是服务端计算时间，还是网络往返时间？


def measure_embedding(texts: list[str], batch_size: int) -> tuple[float, int]:
    """按 batch_size 分批调用 embed_documents，返回 (耗时秒数, API调用次数)。

    batch_size=1  → 每个 [text] 一次 API 请求，共 len(texts) 次
    batch_size=10 → 每 10 条一次 API 请求，共 ceil(len/10) 次
    batch_size=len(texts) → 一次 API 请求处理全部
    """
    # TODO 1a: 将 texts 按 batch_size 切片，每批调用 embeddings.embed_documents(batch)
    # 记录总耗时和 API 调用次数，返回 (elapsed, api_calls)

    len_size = len(texts)

    api_calls = math.ceil(len_size / batch_size)

    start_time = time.time()
    for i in range(api_calls):
        start = i * batch_size
        end = min(start + batch_size, len(texts))
        chunk_texts = texts[start:end]
        embeddings.embed_documents(chunk_texts)

    end_time = time.time()

    elapsed = end_time - start_time
    return elapsed, api_calls


def run_embedding_benchmark():
    """对比 batch_size=1, 10, 30 三种策略的表现。"""
    texts = TEXTS[:30]

    bs_args = [1, 10, 30]

    # 打印表头
    print(f"{'batch_size':>10} | {'耗时':>10} | {'API调用':>8} | {'单条均摊(ms)':>12}")
    print("-" * 50)  # 分隔线

    results = {}
    for bs in bs_args:
        elapsed, api_calls = measure_embedding(texts, bs)
        avg_time_per_text = (elapsed / len(texts)) * 1000  # 转换为毫秒
        results[bs] = (elapsed, api_calls)
        print(f"{bs:>10} | {elapsed:>10.3f} | {api_calls:>8} | {avg_time_per_text:>12.2f}")

    elapsed_1, calls_1 = results[1]
    elapsed_30, calls_30 = results[30]
    check("bs=1 调用 30 次 API", calls_1 == 30)
    check("bs=30 只调用 1 次 API", calls_30 == 1)
    check("bs=30 比 bs=1 快", elapsed_30 < elapsed_1)


# ═══════════════════════════════════════════════════════════════
# TODO 2: LLM 批处理 ≠ Embedding 批处理
# ═══════════════════════════════════════════════════════════════
#
# llm.batch(prompts) 看起来也是"批处理"，但和 embed_documents 是两种机制：
#
#   Embedding 批处理：30 条文本 → 1 次 HTTP → 服务端一次算完 → 30 个向量
#   LLM "批处理"：   5 个问题 → 5 次 HTTP → 线程池并发发出（各自独立）
#
# 前者是"合并请求"（API 级别），后者是"并发请求"（框架级别）。
#
# 推论：LLM batch 耗时 ≈ max(单次耗时)，不是 sum 也不是 1/n。
# 运行后验证：batch 耗时是否接近单次耗时，而非 5 次之和？
#
# 任务：对比 for llm.invoke() vs llm.batch()


def benchmark_llm_batch(questions: list[str]):
    """串行 vs 批量 LLM 调用对比。"""
    # TODO 2:
    #   1. 用 for llm.invoke(...) 串行处理所有问题，计时
    #   2. 用 llm.batch(prompts) 批量处理，计时
    #   3. 打印两种方式的耗时和加速比
    #   4. 用 check() 验证 batch 比串行快
    #
    # 提示：prompt 格式 [("system", "..."), ("human", q)]
    system_prompt = "根据用户的提问回答用户的问题"
    start_time = time.time()
    for idx, question in enumerate(questions, 1):
        messages = [SystemMessage(system_prompt), HumanMessage(question)]
        llm.invoke(messages)
        # print(f"串行回答--{idx}：{response.content}")
    end_time = time.time()

    serial_time = end_time - start_time
    print(f"串行回答耗时:{(serial_time):.3f}s")

    batch_msgs = []

    for q in questions:
        batch_msgs.append([SystemMessage(system_prompt), HumanMessage(q)])

    start_time = time.time()
    llm.batch(batch_msgs)
    end_time = time.time()
    batch_time = end_time - start_time

    print(f"llm.batch回答耗时:{(batch_time):.3f}s")
    print(f"加速比: {serial_time / batch_time:.2f}x")

    check("Batch 加速比 > 1", batch_time < serial_time)


# ═══════════════════════════════════════════════════════════════
# TODO 3: 探索 batch_size 的收益递减点
# ═══════════════════════════════════════════════════════════════
#
# batch_size 越大，API 调用次数越少，但收益不是线性的：
#
#   bs=1  → bs=5:  30 次 API → 6 次，省 24 次 RTT → 收益巨大
#   bs=5  → bs=10: 6 次 → 3 次，省 3 次 RTT    → 收益明显但已变小
#   bs=10 → bs=30: 3 次 → 1 次，省 2 次 RTT    → 边际递减
#
# 同时 batch_size 越接近 API 上限（智谱约 100 条），风险越大。
#
# 任务：测试 sizes = [1, 5, 10, 15, 30]，观察加速比的增长趋势
# 动手前猜一下：从哪个区间开始，加速比的增长明显放缓？


def find_best_batch_size(texts: list[str], sizes: list[int] | None = None):
    """对不同 batch_size 做 benchmark，观察收益递减规律。"""
    # TODO 3: 遍历 sizes，调用 measure_embedding，打印每条结果
    # 格式：batch_size | 耗时 | API调用 | 单条均摊(ms) | vs bs=1 加速比
    # 用 check() 验证 bs=30 比 bs=1 快

    sizes = [1, 5, 10, 15, 30]
    size_result = []

    # 先获取 bs=1 的耗时作为基准
    base_elapsed, _ = measure_embedding(texts, 1)

    # 打印表头
    print(
        f"{'batch_size':>10} | {'耗时':>10} | {'API调用':>8} | {'单条均摊(ms)':>12} | {'vs bs=1 加速比':>12}"
    )

    elapsed_30 = None
    for size in sizes:
        elapsed, api_calls = measure_embedding(texts, size)
        avg_time = elapsed / len(texts) * 1000  # 单条均摊(ms)
        speedup = base_elapsed / elapsed  # vs bs=1 加速比
        size_result.append({"bs": size, "result": (elapsed, api_calls)})
        if size == 30:
            elapsed_30 = elapsed
        print(
            f"{size:>10} | {elapsed:>10.3f} | {api_calls:>8} | {avg_time:>12.2f} | {speedup:>12.2f}"
        )

    check("bs=30 比 bs=1 快", elapsed_30 is not None and elapsed_30 < base_elapsed)


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    reset()

    # --- TODO 1: 批处理收益 ---
    section("TODO 1: 量化批处理收益")
    run_embedding_benchmark()

    # --- TODO 2: LLM batch vs Embedding batch ---
    section("TODO 2: LLM batch ≠ Embedding batch")
    questions = [
        "什么是RAG？",
        "什么是ReAct？",
        "什么是Function Calling？",
        "什么是向量数据库？",
        "什么是缓存穿透？",
    ]
    benchmark_llm_batch(questions)

    # --- TODO 3: 收益递减点 ---
    section("TODO 3: 探索收益递减点")
    find_best_batch_size(TEXTS[:30])

    summary()
