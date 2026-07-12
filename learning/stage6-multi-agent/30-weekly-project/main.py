"""
第 30 章 — 智能客服工单处理系统（考核模式 · 真实框架版）

使用真实的 CrewAI 和 LangGraph 框架实现。

运行测试:
    .venv/bin/python tests/test_crewai.py       # CrewAI 流水线测试
    .venv/bin/python tests/test_langgraph.py    # LangGraph 流水线测试
    .venv/bin/python tests/test_comparison.py   # 框架对比测试
"""

import json
import os
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

# ---- LangChain LLM（FR-1 ~ FR-4 使用）----
from common import load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()

# ---- 真实 CrewAI（TODO-FR-5a 使用）----
from crewai import Agent as CrewAIAgent  # noqa: E402
from crewai import Crew, Process
from crewai import Task as CrewAITask
from crewai.llm import LLM  # noqa: E402
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from common import get_or_create_llm

# ---- 真实 LangGraph（TODO-FR-5b 使用）----

# ============================================================
# 知识库数据
# ============================================================

KNOWLEDGE_BASE: dict[str, list[dict[str, str]]] = {
    "technical": [
        {
            "title": "登录问题排查",
            "content": "如果无法登录，请先检查网络连接，然后尝试清除浏览器缓存和 Cookie。"
            "如果使用 SSO 登录，确认企业账号未过期。仍无法解决请联系 IT 管理员重置密码。",
        },
        {
            "title": "API 报错 401",
            "content": "HTTP 401 表示认证失败。请检查 API Key 是否有效、是否已过期。"
            "在请求头中确认 Authorization: Bearer <your-api-key> 格式正确。",
        },
        {
            "title": "数据同步延迟",
            "content": "数据同步通常在 5 分钟内完成。如果超过 30 分钟仍未同步，"
            "请检查数据源连接状态，或在管理后台点击「手动触发同步」。",
        },
    ],
    "billing": [
        {
            "title": "退款流程",
            "content": "在购买后 7 天内可申请全额退款。请前往「设置 → 账单 → 申请退款」提交申请，"
            "财务团队将在 3 个工作日内处理。退款原路返回，具体到账时间取决于支付渠道。",
        },
        {
            "title": "发票申请",
            "content": "在「设置 → 账单 → 发票管理」中填写开票信息，支持增值税普通发票和专用发票。"
            "电子发票在申请后 1 小时内发送到注册邮箱，纸质发票 3-5 个工作日寄出。",
        },
        {
            "title": "套餐变更",
            "content": "升级套餐立即生效，差价按剩余天数折算。降级套餐在下个计费周期生效。"
            "企业版支持自定义功能组合，请联系销售获取报价。",
        },
    ],
    "general": [
        {
            "title": "支持的语言",
            "content": "平台支持中文、英文、日文三种语言的界面和文档。API 返回内容默认与账户语言设置一致。"
            "如需切换语言，请在「设置 → 偏好设置」中修改。",
        },
        {
            "title": "数据隐私政策",
            "content": "所有用户数据使用 AES-256 加密存储，传输使用 TLS 1.3。"
            "我们通过了 SOC 2 Type II 审计和 ISO 27001 认证。数据不用于模型训练。",
        },
        {
            "title": "SLA 服务等级承诺",
            "content": "标准版 SLA 为 99.5% 月度可用性，企业版为 99.9%。"
            "如未达标，按不可用时间的 100 倍补偿服务时长。技术支持响应时间：标准版 4 小时，企业版 1 小时。",
        },
    ],
}


# ============================================================
# 辅助: 创建 CrewAI 专用的 DeepSeek LLM
# ============================================================
# CrewAI 通过 litellm 调用 LLM，支持 deepseek/deepseek-chat 格式。
# 需要将 DEEPSEEK_API_KEY 传给 LLM。base_url 通过 litellm 环境变量或参数传递。
# 提示：如果遇到 litellm 的 DeepSeek base_url 问题，可以改用 OpenAI 兼容模式：
#   LLM(model="openai/deepseek-chat", base_url="https://api.deepseek.com/v1", api_key="...")


def get_crewai_llm() -> LLM:
    """创建 CrewAI 使用的 DeepSeek LLM 实例。

    提示：因为 CrewAI 底层用 litellm，调用 DeepSeek 时可能需要配置 base_url。
    如果默认的 deepseek/deepseek-chat 不可用，尝试 openai/ 前缀 + base_url 参数。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    # TODO: 选择合适的 model 格式和参数，使 CrewAI 能正常调用 DeepSeek
    # 你可能需要尝试以下几种配置之一：
    #   1. LLM(model="deepseek/deepseek-chat", api_key=api_key, temperature=0)
    #   2. LLM(model="openai/deepseek-chat", base_url="https://api.deepseek.com/v1", api_key=api_key, temperature=0)
    return LLM(
        model="deepseek-v4-flash",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0,
    )
    # raise NotImplementedError("TODO-CREWAI-LLM: 配置 CrewAI 的 DeepSeek LLM")


# ============================================================
# TODO-FR-1: 工单分类
# ============================================================


def classify_ticket(user_question: str, llm: ChatOpenAI) -> dict[str, str]:
    """TODO-FR-1: 实现工单分类功能。

    用 LLM 将用户问题分类为 technical / billing / general。
    验收标准：
    - "无法登录" → category="technical"
    - "怎么退款" → category="billing"
    - "你们支持哪些语言" → category="general"
    """
    system_prompt = """
  你是一个智能客服工单分类助手。你的任务是将用户问题分类到以下三类之一：

  1. technical —— 技术相关问题，例如：无法登录、API 
  报错、数据同步延迟、网络连接问题、系统报错信息等
  2. billing —— 
  账单和账户相关问题，例如：退款申请、发票开具、套餐变更、扣费疑问、付款失败等
  3. general —— 通用咨询，例如：产品功能说明、支持哪些语言、数据隐私政策、SLA 
  承诺、公司信息等

  判断标准：
  - 优先根据问题的实际内容判断，不要仅凭关键词
  - 如果一个技术问题同时涉及账单（如"API 扣费异常"），以核心意图为准
  - 不确定时归入 general

  以 JSON 格式返回，不要返回其他无关内容，格式如下：
  {"category": "<类型>", "reason": "<简短的分类理由>"}
"""
    response = llm.invoke(input=[SystemMessage(system_prompt), HumanMessage(user_question)])
    result = response.content

    parsed = json.loads(result)
    return {"category": parsed["category"], "reason": parsed["reason"]}


# ============================================================
# TODO-FR-2: 知识库检索
# ============================================================


def search_knowledge_base(
    category: str, user_question: str, llm: ChatOpenAI = None
) -> list[dict[str, str]]:
    """TODO-FR-2: 实现知识库检索功能。

    验收标准：
    - 检索结果与 category 匹配
    - 检索结果与 user_question 语义相关
    - 没有匹配时返回空列表
    """
    entries = KNOWLEDGE_BASE.get(category, [])
    if not entries:
        return []

    entries_text = "\n".join(f"[{i}] {e['title']}: {e['content']}" for i, e in enumerate(entries))

    system_prompt = f"""
你是一个知识库检索助手。从以下知识条目中选出与用户问题最相关的条目。

判断原则：
- 基于语义匹配，而非仅关键词
- 最多选 2 条
- 无匹配时返回空列表

知识条目：
{entries_text}

返回 JSON：
{{"selected_indices": [0], "reason": "选择理由"}}
"""

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_question),
        ]
    )

    content = response.content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    parsed = json.loads(content)
    return [entries[i] for i in parsed.get("selected_indices", [])]


# ============================================================
# TODO-FR-3: 回复生成
# ============================================================


def generate_response(
    user_question: str, category: str, kb_results: list[dict[str, str]], llm
) -> str:
    """TODO-FR-3: 实现回复生成功能。

    验收标准：
    - 回复语气专业、友好
    - 回复内容基于知识库事实，不编造
    - kb_results 为空时诚实告知无法处理
    """
    if not kb_results:
        return (
            "抱歉，我目前的知识库中没有与您问题相关的信息。"
            "请尝试联系人工客服，或拨打服务热线 400-xxx-xxxx 获取进一步帮助。"
        )

    kb_text = "\n".join(f"- {e['title']}: {e['content']}" for e in kb_results)
    system_prompt = f"""
你是一个专业的客服助手。根据以下知识条目，回复用户的问题。

要求：
- 语气专业、友好
- 内容基于知识库事实，不编造
- 回复长度 50-200 字
- 先确认用户问题，再给出具体解决方案
- 直接输出回复文本，不要额外格式

分类：{category}

相关知识条目：
{kb_text}
"""

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_question),
        ]
    )
    return response.content.strip()


# ============================================================
# TODO-FR-4: 质量审核
# ============================================================


def review_response(user_question: str, response: str, llm) -> dict[str, str]:
    """TODO-FR-4: 实现质量审核功能。

    验收标准：
    - 符合标准的回复 → verdict="approved"
    - 偏离问题 / 编造内容 / 语气不当 → verdict="rejected" + 具体反馈
    """
    system_prompt = """
你是一个客服回复质量审核员。请按以下 4 条标准审核回复：

1. 解决问题：回复是否直接回应用户的问题？
2. 基于事实：回复内容是否基于知识库，没有编造信息？
3. 语气专业：语气是否专业、友好、有礼貌？
4. 长度适中：回复长度是否在 50-200 字之间？

以 JSON 格式返回：
{"verdict": "approved", "feedback": "审核意见"}
其中 verdict 为 "approved" 或 "rejected"，feedback 指出具体问题（如通过可写"全部标准通过"）。
"""

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"用户问题：{user_question}\n\n回复内容：{response}"),
        ]
    )

    content = response.content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    parsed = json.loads(content)
    return {"verdict": parsed["verdict"], "feedback": parsed["feedback"]}


# ============================================================
# TODO-FR-5a: CrewAI 流水线（真实框架）
# ============================================================
# 用真实的 CrewAI Agent / Task / Crew 实现。
# 关键 API:
#   Agent(role=..., goal=..., backstory=..., llm=crewai_llm)
#   Task(description=..., expected_output=..., agent=..., context=[...])
#   Crew(agents=[...], tasks=[...], process=Process.sequential)
#   crew.kickoff() → CrewOutput (含 .raw 和 .tasks_output)
#
# 角色定义要求：
# - 分类专员: 判断工单类型
# - 技术专家: 处理 technical 问题
# - 账单专员: 处理 billing 问题
# - 通用客服: 处理 general 问题
# - 审核员: 审核回复质量


def run_crewai_pipeline(user_question: str) -> dict:
    """TODO-FR-5a: 用真实 CrewAI 实现工单处理流水线。

    流程: classify → search → draft → review → (rejected? → draft → review) → 输出

    要求：
    1. 创建 CrewAI LLM，创建 5 个 Agent
    2. 创建 Task，通过 context 参数建立依赖链
    3. 用 Crew(process=Process.sequential) 运行
    4. 如果审核 rejected，重新生成回复（最多退回 1 次）
    5. 返回 {"final_response": str, "category": str, "review_verdict": str, "pipeline": "crewai"}

    提示：
    - crew.kickoff() 返回 CrewOutput 对象
    - crew_output.tasks_output[i].raw 可获取各 Task 的输出文本
    - 退回重试时，创建新的 draft + review Task 重新 kickoff
    - 也可以用一个 Crew 完成全程，在外部用 while 循环控制退回
    """
    # TODO: 1. 创建 crewai_llm = get_crewai_llm()
    crewai_llm = get_crewai_llm()
    # TODO: 2. 创建 5 个 CrewAI Agent（role/goal/backstory + llm=crewai_llm）
    classifier = CrewAIAgent(
        role="工单分类专员",
        goal="准确判断用户问题所属类型",
        backstory="你是一名资深的客服工单分类专家，擅长快速识别问题属于技术、账单还是通用咨询。",
        llm=crewai_llm,
    )
    tech_support = CrewAIAgent(
        role="技术支持专家",
        goal="根据知识库解决用户的技术问题",
        backstory="你是一名经验丰富的技术支持工程师，熟悉登录问题、API 报错、数据同步等常见技术问题的排查。",
        llm=crewai_llm,
    )
    billing_support = CrewAIAgent(
        role="账单专员",
        goal="根据知识库处理用户的账单问题",
        backstory="你是一名专业的账单客服，熟悉退款流程、发票开具、套餐变更等财务相关业务。",
        llm=crewai_llm,
    )
    general_support = CrewAIAgent(
        role="通用客服专员",
        goal="根据知识库回答用户的通用咨询",
        backstory="你是一名友好的客服代表，熟悉公司产品信息、支持语言、隐私政策、SLA 承诺等常见问题。",
        llm=crewai_llm,
    )
    reviewer = CrewAIAgent(
        role="质量审核员",
        goal="严格审核回复是否符合质量标准",
        backstory="你是一名严谨的客服质量审核专家，按照标准检查回复是否解决问题、基于事实、语气专业、长度适中。",
        llm=crewai_llm,
    )

    task_classify = CrewAITask(
        description=(
            f"将以下用户问题分类为 technical / billing / general：\n\n{user_question}\n\n"
            '输出 JSON：{"category": "...", "reason": "..."}'
        ),
        expected_output='{"category": "technical|billing|general", "reason": "分类理由"}',
        agent=classifier,
    )
    task_search = CrewAITask(
        description=(
            "根据分类结果中的 category，从对应的知识库中检索与用户问题最相关的知识条目。输出格式为 JSON 列表。"
        ),
        expected_output='[{"title": "...", "content": "..."}]',
        agent=tech_support,
        context=[task_classify],
    )
    task_draft = CrewAITask(
        description=(
            "根据检索到的知识条目，以专业友好的语气回复用户问题。回复长度 50-200 字，基于知识库事实，不编造。"
        ),
        expected_output="一段客服回复文本",
        agent=tech_support,
        context=[task_search],
    )
    task_review = CrewAITask(
        description=(
            "按 4 条标准审核回复：①是否解决问题 ②是否基于事实 ③语气是否专业 ④长度是否适中。"
            '输出 JSON：{"verdict": "approved|rejected", "feedback": "..."}'
        ),
        expected_output='{"verdict": "approved|rejected", "feedback": "审核意见"}',
        agent=reviewer,
        context=[task_draft],
    )

    crew = Crew(
        agents=[classifier, tech_support, billing_support, general_support, reviewer],
        tasks=[task_classify, task_search, task_draft, task_review],
        process=Process.sequential,
    )
    crew_output = crew.kickoff()

    category_info = json.loads(task_classify.output.raw)
    review_info = json.loads(task_review.output.raw)
    final_response = task_draft.output.raw

    retry_count = 0
    while review_info["verdict"] == "rejected" and retry_count < 1:
        retry_count += 1
        task_draft = CrewAITask(
            description=(
                f"根据知识条目重新回复用户问题。上一次被拒原因：{review_info['feedback']}\n"
                "回复长度 50-200 字，基于知识库事实。"
            ),
            expected_output="一段客服回复文本",
            agent=tech_support,
            context=[task_search],
        )
        task_review = CrewAITask(
            description=(
                f"审核下面的回复。上一次被拒原因：{review_info['feedback']}。按 4 条标准审核，输出 JSON。"
            ),
            expected_output='{"verdict": "approved|rejected", "feedback": "审核意见"}',
            agent=reviewer,
            context=[task_draft],
        )
        crew = Crew(
            agents=[classifier, tech_support, billing_support, general_support, reviewer],
            tasks=[task_classify, task_search, task_draft, task_review],
            process=Process.sequential,
        )
        crew_output = crew.kickoff()
        review_info = json.loads(task_review.output.raw)
        final_response = task_draft.output.raw

    return {
        "final_response": final_response,
        "category": category_info["category"],
        "review_verdict": review_info["verdict"],
        "pipeline": "crewai",
    }


# ============================================================
# TODO-FR-5b: LangGraph 流水线（真实框架）
# ============================================================
# 用真实的 langgraph.graph.StateGraph 实现。
# 关键 API:
#   StateGraph(state_schema)  — 接受 TypedDict 定义 State
#   graph.add_node(name, func)  — func(state) -> dict 返回部分更新
#   graph.add_edge(from, to)  — 普通边
#   graph.add_conditional_edges(from, condition, path_map)  — 条件路由
#   graph.set_entry_point(name)
#   app = graph.compile()
#   app.invoke(initial_state) → 最终 state
#
# 图结构:
#   START → classify → research → draft → review ── approved → END
#                                            ↑  rejected   │
#                                            └──────────────┘


class TicketState(TypedDict, total=False):
    """LangGraph State 类型定义。total=False 表示所有字段可选。"""

    user_question: str
    category: str
    classification_reason: str
    kb_results: list[dict[str, str]]
    draft_response: str
    review_verdict: str
    review_feedback: str
    retry_count: int


def run_langgraph_pipeline(user_question: str) -> dict:
    """TODO-FR-5b: 用真实 LangGraph 实现工单处理状态机。

    要求：
    1. 用 TicketState TypedDict 定义 State
    2. 定义节点函数（classify / research / draft / review）
    3. 定义条件函数（decide_after_review）
    4. 构建 StateGraph，设置节点+边+条件边
    5. compile 并 invoke
    6. 返回 {"final_response": str, "category": str, "review_verdict": str,
              "pipeline": "langgraph"}

    提示：
    - 每个节点函数的签名: (state: TicketState) -> dict[str, Any]
      - 返回只包含要更新的字段，LangGraph 自动合并
    - 条件函数签名: (state: TicketState) -> str
      - 返回 path_map 中的 key，如 "draft" 或 END
    - add_conditional_edges("review", decide_after_review, {"draft": "draft", END: END})
    - 节点内通过闭包访问 llm: 在 run_langgraph_pipeline 中定义节点函数即可
    """
    llm = get_or_create_llm(temperature=0)

    def classify_node(state: TicketState) -> dict:
        result = classify_ticket(state["user_question"], llm=llm)
        return {
            "category": result["category"],
            "classification_reason": result["reason"],
        }

    def research_node(state: TicketState) -> dict:
        kb_results = search_knowledge_base(state["category"], state["user_question"], llm=llm)
        return {"kb_results": kb_results}

    def draft_node(state: TicketState) -> dict:
        response_text = generate_response(
            state["user_question"],
            state["category"],
            state["kb_results"],
            llm=llm,
        )
        return {"draft_response": response_text}

    def review_node(state: TicketState) -> dict:
        result = review_response(state["user_question"], state["draft_response"], llm=llm)
        return {
            "review_verdict": result["verdict"],
            "review_feedback": result["feedback"],
            "retry_count": state.get("retry_count", 0) + 1,
        }

    def decide_after_review(state: TicketState) -> str:
        if state.get("review_verdict") == "rejected" and state.get("retry_count", 0) < 2:
            return "draft"
        return END

    graph = StateGraph(TicketState)
    graph.add_node("classify", classify_node)
    graph.add_node("research", research_node)
    graph.add_node("draft", draft_node)
    graph.add_node("review", review_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "research")
    graph.add_edge("research", "draft")
    graph.add_edge("draft", "review")
    graph.add_conditional_edges("review", decide_after_review, {END: END, "draft": "draft"})
    app = graph.compile()

    final_state = app.invoke(TicketState(user_question=user_question, retry_count=0))

    return {
        "final_response": final_state.get("draft_response", ""),
        "category": final_state.get("category", ""),
        "review_verdict": final_state.get("review_verdict", ""),
        "pipeline": "langgraph",
    }


# ============================================================
# TODO-COMPARE: 框架对比分析
# ============================================================


def compare_frameworks() -> dict[str, str]:
    """TODO-COMPARE: 基于真实框架的使用体验，完成对比分析。

    返回包含以下维度的字典：
    - "代码结构": CrewAI vs LangGraph 的代码组织差异
    - "可观测性": 哪个框架更容易追踪中间状态和调试
    - "灵活性": 遇到流程变更时哪个框架更容易调整
    - "选型建议": 基于本次实战体验，什么场景推荐用哪种框架

    提示：不是选择题，是你作为工程师的技术判断。结合真实 API 的使用体验。
    """
    return {
        "代码结构": (
            "LangGraph 用 StateGraph 定义状态机，graph.compile().invoke() 一条链走完，理解上更容易。"
            "CrewAI 基于 Agent/Task/Crew 的组装，crew.kickoff() 一次调用，但内部黑盒感更强。"
        ),
        "可观测性": (
            "LangGraph 的体验最好，app.invoke() 返回完整的最终 State，包括 category、draft_response、review_verdict，"
            "每一步中间结果都清晰可见。CrewAI 需要从 task.output.raw 逐个取，调试不如 LangGraph 直观。"
        ),
        "灵活性": (
            "依然是 LangGraph，在这个客服工单场景中，把每个流程拆成节点，add_conditional_edges 让退回重试变得自然。"
            "CrewAI 遇到流程变更需要重建整个 Crew，调整成本更高。"
        ),
        "选型建议": (
            "推荐 LangGraph。固定顺序的简单流水线（如内容生成）用 CrewAI 够用，"
            "但像本项目的客服工单审批流，涉及条件路由和退回重试，LangGraph 的状态机模型更合适。"
        ),
    }


# ============================================================
# 主程序（演示用，测试请运行 tests/ 目录下的文件）
# ============================================================

if __name__ == "__main__":
    reset()

    test_questions = [
        "我无法登录账号，一直提示密码错误",
        "我想申请退款，已经买了 3 天",
        "你们支持哪些语言？",
    ]

    section("CrewAI 流水线（真实框架）")
    for q in test_questions:
        print(f"\n用户: {q}")
        try:
            result = run_crewai_pipeline(q)
            print(f"  分类: {result.get('category')}")
            print(f"  审核: {result.get('review_verdict')}")
            print(f"  回复: {result.get('final_response', '')[:120]}...")
        except NotImplementedError as e:
            print(f"  ⚠️ 待实现: {e}")

    section("LangGraph 流水线（真实框架）")
    for q in test_questions:
        print(f"\n用户: {q}")
        try:
            result = run_langgraph_pipeline(q)
            print(f"  分类: {result.get('category')}")
            print(f"  审核: {result.get('review_verdict')}")
            print(f"  回复: {result.get('final_response', '')[:120]}...")
        except NotImplementedError as e:
            print(f"  ⚠️ 待实现: {e}")

    section("框架对比")
    try:
        comparison = compare_frameworks()
        for key, value in comparison.items():
            print(f"\n{key}:\n  {value[:200]}...")
    except NotImplementedError as e:
        print(f"  ⚠️ 待实现: {e}")

    summary()
