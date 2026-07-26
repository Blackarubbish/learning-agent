"""研究助手 Agent — 阶段 3 综合实战（模块化版本）

模块结构：
  knowledge_base.py  — 知识库文档 + FAISS vectorstore
  error_handler.py   — 错误分类系统
  memory.py          — 双层记忆（ShortTermMemory / LongTermMemory）
  tools.py           — 工具函数 + FC JSON Schema
  agent.py           — ResearchAssistant FC Agent
  solution.py        — 本文件：入口 + 测试场景

运行：
  make run f=learning/stage3-agent-development/18-weekly-summary/practice/solution.py
"""

from agent import ResearchAssistant
from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary
from memory import LongTermMemory

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


def test_normal_search():
    """场景 1：正常知识检索——搜索概念并获取结果。"""
    reset()
    assistant = ResearchAssistant(llm)

    section("场景 1：正常知识检索")
    result = assistant.run("什么是 RAG？它和 ReAct 有什么区别？")
    print(f"Agent 回答: {result['answer'][:300]}...")
    print(f"工具调用次数: {result['attempts']}")
    check("任务成功", result["success"])
    check("工具调用次数合理", result["attempts"] <= 4)
    summary()


def test_empty_query():
    """场景 2：参数错误——空查询触发 PARAMETER_ERROR 反馈。"""
    reset()
    assistant = ResearchAssistant(llm)

    section("场景 2：参数错误 — 空查询")
    result = assistant.run("搜索一下（不要给我任何关键词）")
    print(f"Agent 回答: {result['answer'][:200]}...")
    print(f"工具调用次数: {result['attempts']}")
    check("未崩溃", "answer" in result)
    summary()


def test_memory_persistence():
    """场景 3：长期记忆——保存偏好后能在后续查询中回忆。"""
    reset()
    ltm = LongTermMemory()
    assistant = ResearchAssistant(llm, long_term=ltm)

    section("场景 3：长期记忆 — 保存偏好")
    result1 = assistant.run(
        "记住：我最关注的是 RAG 和 Embedding 相关的内容，我喜欢用表格对比的方式呈现信息"
    )
    print(f"第一轮: {result1['answer'][:200]}...")
    check("第一轮成功", result1["success"])

    result2 = assistant.run("推荐一些我可能感兴趣的技术话题")
    print(f"第二轮: {result2['answer'][:200]}...")
    check("第二轮成功", result2["success"])
    check("长期记忆已写入", len(ltm.store) >= 1)
    summary()


def test_summarize():
    """场景 4：文本摘要——调用 LLM 对搜索结果做摘要。"""
    reset()
    assistant = ResearchAssistant(llm)

    section("场景 4：文本摘要")
    result = assistant.run("帮我搜索 Agent Memory 的内容，然后对找到的结果做一个摘要")
    print(f"Agent 回答: {result['answer'][:300]}...")
    print(f"工具调用次数: {result['attempts']}")
    check("任务成功", result["success"])
    check("使用了多个工具", result["attempts"] >= 2)
    summary()


def test_degradation():
    """场景 5：降级策略——连续参数错误后停止循环。"""
    reset()
    assistant = ResearchAssistant(llm, max_retries=5, degradation_threshold=3)

    section("场景 5：降级策略")
    result = assistant.run(
        "帮我保存一个空的笔记，然后搜索空内容，最后再试一次空摘要——重复直到你放弃"
    )
    print(f"Agent 回答: {result['answer'][:200]}...")
    print(f"工具调用次数: {result['attempts']}")
    check("Agent 未无限循环", result["attempts"] <= 5)
    summary()


if __name__ == "__main__":
    test_normal_search()
    test_empty_query()
    test_memory_persistence()
    test_summarize()
    test_degradation()
