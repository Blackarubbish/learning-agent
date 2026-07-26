"""工具函数 + FC JSON Schema（ch13 工具工程 + ch15 Function Calling）。

三个工具：
- search_knowledge: 向量检索知识库（信息抽象：截断+摘要+引导）
- summarize_text:   LLM 文本摘要（结构化输出）
- save_note:        写入长期记忆（状态反馈）

设计要点：
- 每个工具返回 JSON 字符串，LLM 可以可靠解析
- 参数校验在工具层（不在 prompt 层），空参数返回结构化错误
- 错误信息包含分类关键词（empty/invalid/not found），供 error_handler 分类
"""

import json

from langchain_community.vectorstores import FAISS
from memory import LongTermMemory


def search_knowledge(query: str, vectorstore: FAISS, top_k: int = 5) -> str:
    """搜索知识库——信息抽象：截断 top_k 条 + 摘要引导，而非倾泻原始文档。

    Args:
        query: 搜索关键词或问题
        vectorstore: FAISS 向量存储实例
        top_k: 返回结果数量

    Returns:
        JSON 字符串，格式 {"success": bool, "results": [...], "summary": str, "count": int}
    """
    if not query or not query.strip():
        return json.dumps(
            {
                "success": False,
                "error": "invalid parameter: query is empty or missing — please provide a search query",
            }
        )

    docs = vectorstore.similarity_search(query, k=top_k)
    if not docs:
        return json.dumps(
            {
                "success": True,
                "results": [],
                "summary": "未找到相关结果。建议尝试更短或更通用的关键词。",
                "count": 0,
            }
        )

    results = [{"rank": i + 1, "content": d.page_content[:150]} for i, d in enumerate(docs)]
    return json.dumps(
        {
            "success": True,
            "results": results,
            "summary": f"共找到 {len(results)} 条相关结果（共检索 {top_k} 条）。如需详细信息，请指定序号获取完整内容。",
            "count": len(results),
        },
        ensure_ascii=False,
    )


def summarize_text(text: str, llm, max_words: int = 80) -> str:
    """调用 LLM 对文本做摘要——结构化输出：标题 + 要点 + 结论。

    Args:
        text: 需要摘要的文本
        llm: LLM 实例
        max_words: 摘要最大字数

    Returns:
        JSON 字符串，格式 {"success": bool, "summary": str} 或 {"success": false, "error": str}
    """
    if not text or not text.strip():
        return json.dumps(
            {
                "success": False,
                "error": "invalid parameter: text is empty or missing — please provide text to summarize",
            }
        )

    trimmed = text[:2000]  # 超长截断保护
    prompt = f"""请用中文对以下内容做摘要，输出 JSON 格式，包含 title（标题）、points（3 个要点）、conclusion（一句话结论），总字数不超过 {max_words} 字。

内容：
{trimmed}

输出 JSON："""

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        return json.dumps({"success": True, "summary": content}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": f"summarization failed: {e}"})


def save_note(content: str, ltm: LongTermMemory, tags: list[str] | None = None) -> str:
    """将关键信息写入长期记忆——状态反馈：告知写入内容和当前记忆总数。

    Args:
        content: 要保存的内容
        ltm: LongTermMemory 实例
        tags: 标签列表，便于后续分类检索

    Returns:
        JSON 字符串，格式 {"success": bool, "memory_id": str, "message": str}
    """
    if not content or not content.strip():
        return json.dumps(
            {
                "success": False,
                "error": "invalid parameter: content is empty or missing — cannot save empty note",
            }
        )

    memory_id = ltm.add(content, tags)
    return json.dumps(
        {
            "success": True,
            "memory_id": memory_id,
            "message": f"已保存到长期记忆 (id={memory_id})。当前共 {len(ltm.store)} 条记忆。",
        },
        ensure_ascii=False,
    )


# ═══════════════════════════════════════════════════════════════
# FC JSON Schema 定义（ch15）
# ═══════════════════════════════════════════════════════════════

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索 AI/ML 知识库，返回相关文档摘要。当用户问概念性问题或需要查找信息时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或问题"},
                    "top_k": {"type": "integer", "description": "返回结果数量，默认 5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": "对一段文本做摘要，返回标题、要点和结论。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "需要摘要的文本"},
                    "max_words": {"type": "integer", "description": "摘要最大字数，默认 80"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "将重要信息保存到长期记忆，供后续会话使用。当用户说'记住'、'保存'时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要保存的内容"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签列表，便于后续分类检索",
                    },
                },
                "required": ["content"],
            },
        },
    },
]
