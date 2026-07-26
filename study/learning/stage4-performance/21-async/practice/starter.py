"""异步处理 — 将 Agent 系统的 I/O 操作改造为异步

核心学习点：
  - async/await 语法：定义和等待协程
  - httpx.AsyncClient：异步 HTTP 客户端，替换同步 httpx.Client
  - LangChain Async API：ainvoke / asimilarity_search
  - asyncio.gather：并发执行多个协程
  - 同步 vs 异步 benchmark 对比

运行：
  python learning/stage4-performance/21-async/practice/starter.py
"""

import asyncio
import json
import time

import httpx
from common import get_or_create_embeddings, get_or_create_llm, load_dotenv_if_needed, reset
from common.check import check, section, summary
from common.env import require_env
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)
embeddings = get_or_create_embeddings()

# ═══════════════════════════════════════════════════════════════
# 准备知识库（已提供，无需修改）
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

# 并发测试查询（覆盖不同主题，确保触发工具调用）
TEST_QUERIES = [
    "什么是 RAG？",
    "ReAct 和 Function Calling 有什么区别？",
    "Redis 在 Agent 系统中有什么用？",
    "如何分析 Python 程序的性能瓶颈？",
    "语义缓存和精确缓存有什么不同？",
]

# ═══════════════════════════════════════════════════════════════
# TODO 1: 将同步 LLM 调用改造为异步
# ═══════════════════════════════════════════════════════════════
#
# LangChain ChatOpenAI 的异步版 invoke：
#   同步: llm.invoke(messages)       → 阻塞当前线程直到 API 返回
#   异步: await llm.ainvoke(messages) → 挂起协程，事件循环去处理其他任务
#
# 任务：用 llm.ainvoke() 实现异步摘要


async def async_summarize(text: str, max_words: int = 80) -> dict:
    """异步调用 LLM 做文本摘要，返回 {"success": True, "summary": "..."}"""
    if not text.strip():
        return {"success": False, "error": "text 不能为空"}

    # TODO 1: 用 llm.ainvoke() 替代 llm.invoke()，其他逻辑不变
    response = await llm.ainvoke(
        [
            SystemMessage(content="你是一个中文文本摘要助手。"),
            HumanMessage(content=f"请对以下文本进行摘要，控制在 {max_words} 个字以内：{text}"),
        ]
    )
    return {"success": True, "summary": response.content}


# ═══════════════════════════════════════════════════════════════
# TODO 2: 将 Embedding API 调用改造为异步
# ═══════════════════════════════════════════════════════════════
#
# httpx 的同步和异步用法：
#   同步: resp = httpx.post(url, headers={...}, json={...})
#   异步: async with httpx.AsyncClient() as client:
#             resp = await client.post(url, headers={...}, json={...})
#
# 任务：用 httpx.AsyncClient 异步调用智谱 Embedding API
# 提示：API key 通过 require_env("ZHIPU_API_KEY") 获取


async def async_embed(texts: list[str]) -> list[list[float]]:
    """异步调用智谱 Embedding API，返回向量列表"""
    api_key = require_env("ZHIPU_API_KEY")

    # TODO 2: 用 httpx.AsyncClient 替代同步 httpx.post
    resp = None
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
#
# FAISS（LangChain 封装）的异步检索：
#   同步: vectorstore.similarity_search(query, k=5)
#   异步: await vectorstore.asimilarity_search(query, k=5)
#
# 任务：用 asimilarity_search 实现异步知识库搜索


async def async_search(query: str, top_k: int = 5) -> dict:
    """异步搜索知识库，返回 {"success": True, "results": [...], "count": N}"""
    if not query.strip():
        return {"success": False, "error": "query 不能为空"}

    # TODO 3: 用 vectorstore.asimilarity_search() 替代 vectorstore.similarity_search()
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
# TODO 4: 实现异步 Agent（FC 循环 + 异步工具）
# ═══════════════════════════════════════════════════════════════
#
# 将同步 FC Agent 循环改造为异步版本。关键变化：
#   llm.invoke()           → await llm.ainvoke()
#   vectorstore 同步检索     → await async_search()
#   llm 同步摘要             → await async_summarize()
#   bind_tools() 不涉及 I/O → 保持不变
#
# 工具定义和 System Prompt 已提供。

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
    """异步 FC Agent — 将同步 I/O 改造为 async/await"""

    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns

    # TODO 4a: 异步工具执行
    async def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """执行单个工具调用，返回 JSON 字符串。
        根据 tool_name 分发到 async_search 或 async_summarize。"""
        # 你的代码：
        # if tool_name == "search_knowledge": result = await async_search(...)
        # elif tool_name == "summarize_text": result = await async_summarize(...)
        # else: result = {"success": False, "error": f"未知工具: {tool_name}"}
        result = {"success": False, "error": f"未知工具: {tool_name}"}
        if tool_name == "search_knowledge":
            result = await async_search(**tool_args)
        elif tool_name == "summarize_text":
            result = await async_summarize(**tool_args)
        return json.dumps(result, ensure_ascii=False)

    # TODO 4b: 异步 FC Agent 循环
    async def run(self, user_input: str) -> dict:
        """异步 FC Agent 主循环。

        流程：
        1. 构建 messages = [SystemMessage, HumanMessage(user_input)]
        2. 循环 while turns < max_turns:
           a. await llm.bind_tools(TOOLS_SCHEMA).ainvoke(messages)
           b. 无 tool_calls → 返回最终答案，附带 tool_calls 次数
           c. 有 tool_calls → messages.append(response)
           d. 遍历 tool_calls，await self._execute_tool() 执行
           e. messages.append(ToolMessage(...))
        3. 超出 max_turns → 返回降级信息
        """

        llm_with_tools = llm.bind_tools(TOOLS_SCHEMA)
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_input)]
        tool_calls_count = 0

        for _ in range(self.max_turns):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)
            if not response.tool_calls:
                return {"answer": response.content, "success": True, "tool_calls": tool_calls_count}

            tool_calls = response.tool_calls
            for tc in tool_calls:
                tool_calls_count = tool_calls_count + 1
                tc_name = tc["name"]
                tc_args = tc["args"]
                tc_result = await self._execute_tool(tool_name=tc_name, tool_args=tc_args)
                messages.append(ToolMessage(content=tc_result, tool_call_id=tc.get("id", "")))

        return {
            "answer": "Agent reached maximum steps",
            "success": False,
            "tool_calls": tool_calls_count,
        }

    # TODO 4c: 同步版本（用于 benchmark 对比）
    def run_sync(self, user_input: str) -> dict:
        """同步 FC Agent 循环 — 与 run() 逻辑相同但全用同步 API。

        关键区别：
          llm.invoke() 代替 await llm.ainvoke()
          vectorstore.similarity_search() 代替 await async_search()
          llm.invoke() 代替 await async_summarize()
        """
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_input)]
        tool_calls_count = 0

        for _ in range(self.max_turns):
            response = llm.bind_tools(TOOLS_SCHEMA).invoke(messages)
            messages.append(response)
            if not response.tool_calls:
                return {"answer": response.content, "success": True, "tool_calls": tool_calls_count}

            for tc in response.tool_calls:
                tool_calls_count += 1
                if tc["name"] == "search_knowledge":
                    docs = vectorstore.similarity_search(
                        tc["args"].get("query", ""), k=tc["args"].get("top_k", 5)
                    )
                    result = json.dumps(
                        {
                            "success": True,
                            "results": [
                                {"rank": i + 1, "content": d.page_content[:150]}
                                for i, d in enumerate(docs)
                            ],
                            "count": len(docs),
                        },
                        ensure_ascii=False,
                    )
                elif tc["name"] == "summarize_text":
                    text = tc["args"].get("text", "")
                    if len(text) > 2000:
                        text = text[:2000]
                    summary_resp = llm.invoke(
                        [
                            SystemMessage(content="你是一个中文文本摘要助手。"),
                            HumanMessage(
                                content=f"摘要（{tc['args'].get('max_words', 80)}字内）：{text}"
                            ),
                        ]
                    )
                    result = json.dumps(
                        {"success": True, "summary": summary_resp.content}, ensure_ascii=False
                    )
                else:
                    result = json.dumps(
                        {"success": False, "error": f"未知工具: {tc['name']}"}, ensure_ascii=False
                    )
                messages.append(ToolMessage(content=result, tool_call_id=tc.get("id", "")))
                tool_calls_count += 1

        return {
            "answer": "Agent reached maximum steps",
            "success": False,
            "tool_calls": tool_calls_count,
        }


# ═══════════════════════════════════════════════════════════════
# TODO 5: Benchmark — 同步 vs 异步
# ═══════════════════════════════════════════════════════════════
#
# 核心对比：
#   同步：for q in queries: agent.run_sync(q)       → 总耗时 = Σ 单次耗时
#   异步：await asyncio.gather(*[agent.run(q) ...])  → 总耗时 ≈ max(单次耗时)


def benchmark_sync(queries: list[str]) -> float:
    """同步顺序执行所有查询，返回总耗时（秒）"""
    agent = AsyncAgent(max_turns=5)
    # 用一次空跑预热 LLM 连接，减少首次调用的网络波动影响
    agent.run_sync("ping")
    start = time.time()
    for q in queries:
        agent.run_sync(q)
    return time.time() - start


async def benchmark_async_impl(queries: list[str]) -> float:
    """异步并发执行所有查询，返回总耗时（秒）"""
    agent = AsyncAgent(max_turns=5)
    # asyncio.gather 并发执行所有协程，I/O 等待时间重叠
    await agent.run("ping")
    start = time.time()
    await asyncio.gather(*[agent.run(q) for q in queries])
    return time.time() - start


def run_benchmarks():
    """运行同步 vs 异步对比实验，打印加速比"""
    queries = TEST_QUERIES
    print(f"测试 {len(queries)} 个并发查询...")

    sync_time = benchmark_sync(queries)
    print(f"同步耗时: {sync_time:.2f}s")

    async_time = asyncio.run(benchmark_async_impl(queries))
    print(f"异步耗时: {async_time:.2f}s")

    speedup = sync_time / async_time if async_time > 0 else float("inf")
    print(f"加速比: {speedup:.1f}x")
    check("加速比 > 1.5x（异步明显更快）", speedup > 1.5, f"当前: {speedup:.1f}x")
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
