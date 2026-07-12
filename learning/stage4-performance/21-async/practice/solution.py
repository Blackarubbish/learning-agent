"""异步处理 — 参考实现

将 Agent 系统的 I/O 操作改造为异步，对比同步/异步在并发场景下的性能差异。

核心变化：
  - llm.invoke() → await llm.ainvoke()
  - httpx.post() → await httpx.AsyncClient().post()
  - vectorstore.similarity_search() → await vectorstore.asimilarity_search()
  - for query in queries: run(query) → await asyncio.gather(*tasks)
"""

import asyncio
import json
import time

import httpx
from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

from common import get_or_create_embeddings, get_or_create_llm, load_dotenv_if_needed, reset
from common.check import check, section, summary
from common.env import require_env

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)
embeddings = get_or_create_embeddings()

# ═══════════════════════════════════════════════════════════════
# 知识库
# ═══════════════════════════════════════════════════════════════

DOCUMENTS = [
    "RAG（检索增强生成）结合信息检索和文本生成。先检索相关文档，再作为上下文提供给 LLM 生成答案，有效减少幻觉。",
    "ReAct 是 Reasoning + Acting 的 Agent 架构。LLM 交替推理和行动，形成思考-行动-观察循环，能调用外部工具完成任务。",
    "Function Calling 用 JSON Schema 定义工具，LLM 输出结构化调用请求。相比 ReAct 文本解析，可靠性从约80%提升到约99%。",
    "Redis 是开源内存数据结构存储，常用作缓存。Agent 系统中可缓存 LLM 响应和 Embedding，消除重复 API 调用。",
    "cProfile 是 Python 内置性能分析器，统计函数调用次数、总耗时和自身耗时。cumtime 定位时间黑洞，tottime 定位 CPU 热点。",
    "异步编程使用协程和事件循环，I/O 等待时切换任务。Python 的 asyncio 提供完整异步支持，适合 I/O 密集型并发场景。",
    "FAISS 是 Facebook 开源的向量相似度搜索库，支持 Flat/IVF/HNSW 索引。适合中小规模数据集的内存检索。",
    "语义缓存用 Embedding 相似度匹配相似查询，精确缓存用哈希匹配相同查询。前者命中率高，后者准确但覆盖窄。",
]

text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=30)
chunks = text_splitter.create_documents(DOCUMENTS)
vectorstore = FAISS.from_documents(chunks, embeddings)

TEST_QUERIES = [
    "什么是 RAG？",
    "ReAct 和 Function Calling 有什么区别？",
    "Redis 在 Agent 系统中有什么用？",
    "如何分析 Python 程序的性能瓶颈？",
    "语义缓存和精确缓存有什么不同？",
]

# ═══════════════════════════════════════════════════════════════
# TODO 1: 异步 LLM 调用
# ═══════════════════════════════════════════════════════════════
# 关键变化：llm.invoke() → await llm.ainvoke()
# ainvoke 返回的是协程，await 将其挂起，让事件循环在等待 API 响应期间处理其他协程。


async def async_summarize(text: str, max_words: int = 80) -> dict:
    if not text.strip():
        return {"success": False, "error": "text 不能为空"}

    response = await llm.ainvoke(
        [
            SystemMessage(content="你是一个中文文本摘要助手。"),
            HumanMessage(content=f"请对以下文本进行摘要，控制在 {max_words} 个字以内：{text}"),
        ]
    )
    return {"success": True, "summary": response.content}


# ═══════════════════════════════════════════════════════════════
# TODO 2: 异步 Embedding
# ═══════════════════════════════════════════════════════════════
# 关键变化：httpx.post() → async with httpx.AsyncClient() + await client.post()
# AsyncClient 用 async with 管理生命周期，自动关闭连接。


async def async_embed(texts: list[str]) -> list[list[float]]:
    api_key = require_env("ZHIPU_API_KEY")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.bigmodel.cn/api/paas/v4/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "embedding-3", "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["data"]]


# ═══════════════════════════════════════════════════════════════
# TODO 3: 异步向量检索
# ═══════════════════════════════════════════════════════════════
# 关键变化：vectorstore.similarity_search() → await vectorstore.asimilarity_search()
# FAISS 向量检索本身是 CPU 操作（不涉及网络 I/O），LangChain 的 asimilarity_search
# 实际上是在线程池中执行同步操作，避免阻塞事件循环。


async def async_search(query: str, top_k: int = 5) -> dict:
    if not query.strip():
        return {"success": False, "error": "query 不能为空"}

    docs = await vectorstore.asimilarity_search(query, k=top_k)

    results = []
    for i, d in enumerate(docs):
        results.append(
            {
                "rank": i + 1,
                "content": d.page_content[:150] + "..."
                if len(d.page_content) > 150
                else d.page_content,
            }
        )
    return {"success": True, "results": results, "count": len(results)}


# ═══════════════════════════════════════════════════════════════
# TODO 4: 异步 Agent
# ═══════════════════════════════════════════════════════════════
# 将 FC 循环中所有 I/O 操作改为 await：
#   - LLM 推理：await llm.ainvoke()
#   - 工具执行：await self._execute_tool()
# bind_tools() 只是修改请求参数（不涉及网络），不需要 await。

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "在知识库中搜索相关文档",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "top_k": {"type": "integer", "description": "返回文档数量，默认5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": "对文本做中文摘要",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "需要摘要的文本"},
                    "max_words": {"type": "integer", "description": "摘要最大字数，默认80"},
                },
                "required": ["text"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "你是一个 AI 研究助手。用中文回复。优先搜索知识库回答问题。如果搜索结果不够，可以对文档做摘要。"
)


class AsyncAgent:
    """异步 FC Agent — 核心：将所有网络 I/O 改为 await"""

    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns

    async def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """执行单个工具，返回 JSON 字符串。"""
        if tool_name == "search_knowledge":
            result = await async_search(tool_args.get("query", ""), tool_args.get("top_k", 5))
        elif tool_name == "summarize_text":
            result = await async_summarize(
                tool_args.get("text", ""), tool_args.get("max_words", 80)
            )
        else:
            result = {"success": False, "error": f"未知工具: {tool_name}"}
        return json.dumps(result, ensure_ascii=False)

    async def run(self, user_input: str) -> dict:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_input),
        ]

        tool_calls_count = 0
        for _ in range(self.max_turns):
            response = await llm.bind_tools(TOOLS_SCHEMA).ainvoke(messages)
            tool_calls = getattr(response, "tool_calls", [])

            if not tool_calls:
                answer = response.content if hasattr(response, "content") else str(response)
                return {"success": True, "answer": answer, "tool_calls": tool_calls_count}

            messages.append(response)
            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {})
                tool_result = await self._execute_tool(tool_name, tool_args)
                messages.append(ToolMessage(content=tool_result, tool_call_id=call["id"]))
                tool_calls_count += 1

        return {
            "success": False,
            "answer": f"已进行 {tool_calls_count} 次工具调用仍未完成",
            "tool_calls": tool_calls_count,
        }

    def run_sync(self, user_input: str) -> dict:
        """同步版本 — 与 run() 逻辑完全相同，但用同步 API。

        用于 benchmark 对比：同样的逻辑，同步 I/O 会串行等待，异步 I/O 可以并发。
        """
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_input),
        ]

        tool_calls_count = 0
        for _ in range(self.max_turns):
            response = llm.bind_tools(TOOLS_SCHEMA).invoke(messages)
            tool_calls = getattr(response, "tool_calls", [])

            if not tool_calls:
                answer = response.content if hasattr(response, "content") else str(response)
                return {"success": True, "answer": answer, "tool_calls": tool_calls_count}

            messages.append(response)
            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {})

                if tool_name == "search_knowledge":
                    docs = vectorstore.similarity_search(
                        tool_args.get("query", ""), k=tool_args.get("top_k", 5)
                    )
                    result = {
                        "success": True,
                        "results": [
                            {"rank": i + 1, "content": d.page_content[:150]}
                            for i, d in enumerate(docs)
                        ],
                        "count": len(docs),
                    }
                elif tool_name == "summarize_text":
                    result = {
                        "success": True,
                        "summary": llm.invoke(
                            [
                                SystemMessage(content="你是一个中文文本摘要助手。"),
                                HumanMessage(
                                    content=f"摘要（{tool_args.get('max_words', 80)}字内）：{tool_args.get('text', '')}"
                                ),
                            ]
                        ).content,
                    }
                else:
                    result = {"success": False, "error": f"未知工具: {tool_name}"}

                messages.append(
                    ToolMessage(
                        content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"]
                    )
                )
                tool_calls_count += 1

        return {
            "success": False,
            "answer": f"已进行 {tool_calls_count} 次工具调用仍未完成",
            "tool_calls": tool_calls_count,
        }


# ═══════════════════════════════════════════════════════════════
# TODO 5: Benchmark
# ═══════════════════════════════════════════════════════════════
# 为什么异步更快？
#   同步：query1 → 等待 LLM API → query2 → 等待 LLM API → ...（串行等待）
#   异步：query1..5 同时发出 LLM API 请求，然后一起等待（并发 I/O）
#   总耗时 ≈ max(单次耗时) 而非 Σ(单次耗时)
#
# 为什么单次查询异步不更快？
#   异步不减少 I/O 时间，只让多个 I/O 操作的时间重叠。
#   就像一个人排队买咖啡 vs 五个人同时排队——单人的等待时间不变。


def benchmark_sync(queries: list[str]) -> float:
    agent = AsyncAgent(max_turns=5)
    start = time.time()
    for q in queries:
        agent.run_sync(q)
    return time.time() - start


async def benchmark_async_impl(queries: list[str]) -> float:
    agent = AsyncAgent(max_turns=5)
    start = time.time()
    tasks = [agent.run(q) for q in queries]
    # asyncio.gather 并发执行所有协程 — I/O 等待时间重叠
    await asyncio.gather(*tasks)
    return time.time() - start


def run_benchmarks():
    queries = TEST_QUERIES

    section("同步 Benchmark")
    sync_time = benchmark_sync(queries)
    print(f"同步耗时 ({len(queries)} 个查询): {sync_time:.2f}s")

    section("异步 Benchmark")
    async_time = asyncio.run(benchmark_async_impl(queries))
    print(f"异步耗时 ({len(queries)} 个查询): {async_time:.2f}s")

    speedup = sync_time / async_time if async_time > 0 else float("inf")
    print(f"加速比: {speedup:.1f}x")

    check("加速比 > 1.5x（异步明显更快）", speedup > 1.5, f"当前: {speedup:.1f}x")
    # 理想情况加速比应接近并发数，但受限于 API 并发限制和网络波动
    check("异步耗时 < 同步耗时", async_time < sync_time)


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    reset()

    # --- TODO 1: async_summarize ---
    section("TODO 1: 异步 LLM 调用")
    result1 = asyncio.run(
        async_summarize("异步编程使用协程和事件循环，在 I/O 等待时切换到其他任务，提升并发吞吐。")
    )
    print(f"摘要: {result1.get('summary', '')[:100]}...")
    check("async_summarize 返回成功", result1.get("success"))
    check("包含 summary 字段", "summary" in result1)

    # --- TODO 2: async_embed ---
    section("TODO 2: 异步 Embedding")
    emb_result = asyncio.run(async_embed(["测试文本", "异步编程"]))
    print(f"向量 0 前 5 维: {emb_result[0][:5]}...")
    check("返回 2 个向量", len(emb_result) == 2)
    check("向量维度 > 0", len(emb_result[0]) > 0)

    # --- TODO 3: async_search ---
    section("TODO 3: 异步向量检索")
    search_result = asyncio.run(async_search("什么是 RAG？"))
    print(f"找到 {search_result.get('count', 0)} 条结果")
    check("搜索成功", search_result.get("success"))
    check("至少 1 条结果", search_result.get("count", 0) >= 1)

    # --- TODO 4: AsyncAgent ---
    section("TODO 4: 异步 Agent")
    agent = AsyncAgent(max_turns=3)
    agent_result = asyncio.run(agent.run("什么是 RAG？"))
    print(f"回答（前200字）: {agent_result.get('answer', '')[:200]}")
    check("Agent 成功", agent_result.get("success"))
    check("使用了工具", agent_result.get("tool_calls", 0) > 0)

    # --- TODO 5: Benchmark ---
    section("TODO 5: Benchmark 同步 vs 异步")
    run_benchmarks()

    summary()
