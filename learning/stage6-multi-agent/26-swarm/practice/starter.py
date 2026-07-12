"""Swarm 极简入门 — 手写 Multi-Agent Handoff 机制

核心学习点：
  - Agent = instructions + tools + handoff functions
  - Handoff 就是一个 tool，返回值是目标 Agent
  - Swarm.run() 循环：LLM调用 → tool执行 → 检测Handoff → 切换Agent
  - Routine 模式可以减少 LLM 调用（预定义流程，无需每次 LLM 判断路由）

运行：
  PYTHONPATH=. python learning/stage6-multi-agent/26-swarm/practice/starter.py
"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from common import get_or_create_llm, load_dotenv_if_needed, reset
from common.check import check, section, summary

load_dotenv_if_needed()


# ═══════════════════════════════════════════════════════════════
# TODO 1: 实现最简单的 Agent 对象
# ═══════════════════════════════════════════════════════════════
#
# Agent = name(str) + instructions(str) + tools(dict) + handoffs(list)
# 其中 handoffs 也是一类特殊的 tool：执行后返回目标 Agent 对象


class Agent:
    """Swarm 风格的 Agent：角色定义 + 工具 + Handoff。

    Swarm 的核心创新：Handoff 不是框架层面的特殊机制，
    而是普通的 tool function——返回值是目标 Agent 对象。
    """

    def __init__(self, name: str, instructions: str, tools: dict | None = None):
        # TODO 1a: 初始化 Agent 的属性
        # - self.name: Agent 名称
        # - self.instructions: 系统提示词
        # - self.tools: dict[str, callable]，工具名 → 函数
        self.name = name
        self.instructions = instructions
        if not tools:
            self.tools = {}
        else:
            self.tools = tools

    def add_handoff(self, target_agent: "Agent", description: str = ""):
        """注册一个 handoff 工具。

        Handoff 的运作方式：
        1. 框架把这个 handoff 包装成 tool 给 LLM 调用
        2. LLM 判断当前 Agent 无法处理，调用 handoff tool
        3. tool 返回目标 Agent → 框架检测到 Agent 对象 → 切换

        Args:
            target_agent: 要转到的 Agent
            description: 什么时候该用这个 handoff（写入 tool description）
        """

        # TODO 1b: 创建 handoff 函数并注册为 tool
        def _handoff():
            """把对话转给专门处理此类问题的 Agent。"""
            return target_agent

        self.tools[f"transfer_to_{target_agent.name}"] = _handoff


# ═══════════════════════════════════════════════════════════════
# TODO 2: 实现 Swarm.run() 核心循环
# ═══════════════════════════════════════════════════════════════
#
# 循环流程：
#   1. 拼接 messages: system(当前Agent的instructions) + history + latest_user_msg
#   2. 如果有 tools，调用 llm.bind_tools()；否则 llm.invoke()
#   3. 如果 LLM 返回 tool_calls:
#        a. 执行每个 tool
#        b. 如果 tool 返回 Agent 对象 → handoff! 切换 current_agent → break
#        c. 否则把 tool 结果作为 ToolMessage 追加到 messages → 继续循环
#   4. 如果 LLM 没调 tool → 返回最终回复
#   5. 循环上限 max_turns（防止死循环）


class TooManyTurns(Exception):
    """超出最大轮数"""


class Swarm:
    """极简 Multi-Agent 编排器。"""

    def __init__(self, llm: ChatOpenAI, max_turns: int = 10):
        self.llm = llm
        self.max_turns = max_turns

    def run(self, agent: Agent, messages: list, debug: bool = False) -> dict:
        """运行 Agent 循环，支持 Handoff。

        Args:
            agent: 初始 Agent
            messages: 历史消息列表（LangChain 格式）
            debug: 是否打印调试信息

        Returns:
            {"agent": 最终Agent名, "answer": 最终回复, "handoffs": [经过的Agent名]}
        """
        # TODO 2: 实现核心循环
        current_agent = agent
        history = list(messages)
        handoff_chain = [agent.name]
        for _ in range(self.max_turns):
            if debug:
                print(f"\n[Turn {_ + 1}] current_agent={current_agent.name}")
            system_msg = SystemMessage(content=current_agent.instructions)
            full_messages = [system_msg] + history
            response = None
            if current_agent.tools:
                tool_list = []
                from langchain.tools import tool

                for t_name, t_fn in current_agent.tools.items():
                    wrapped = tool(t_fn)
                    wrapped.name = t_name
                    tool_list.append(wrapped)
                llm_with_tool = self.llm.bind_tools(tool_list)
                response = llm_with_tool.invoke(full_messages)
            else:
                response = self.llm.invoke(full_messages)

            # 关键：必须先把 assistant 消息加入 history，ToolMessage 才能引用它的 tool_call_id
            history.append(response)

            if response.tool_calls:
                for tc in response.tool_calls:
                    t_name = tc["name"]
                    t_args = tc["args"]
                    if t_name in current_agent.tools:
                        result = current_agent.tools[t_name](**t_args)
                        if isinstance(result, Agent):
                            if debug:
                                print(f"  ↪ Handoff: {current_agent.name} → {result.name}")
                            current_agent = result
                            handoff_chain.append(result.name)
                            history.append(
                                ToolMessage(
                                    content=f"已将对话转交给 {result.name}，请继续处理。",
                                    tool_call_id=tc.get("id", ""),
                                )
                            )
                            break
                        history.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            else:
                return {
                    "answer": response.content,
                    "agent": current_agent.name,
                    "handoff_chain": handoff_chain,
                }
        raise TooManyTurns()


# ═══════════════════════════════════════════════════════════════
# TODO 3: 构建"客服→技术支持"两级 Handoff 系统
# ═══════════════════════════════════════════════════════════════


def search_kb(query: str) -> str:
    """搜索知识库（模拟）。"""
    kb = {
        "退货": "退货流程：登录→我的订单→申请退货→填写原因→等待审核→寄回商品→退款",
        "物流": "物流查询：登录→我的订单→点击订单→查看物流详情",
        "密码": "修改密码：设置→账号安全→修改密码→验证手机→设置新密码",
        "API": "API 调用 500 错误：检查 Content-Type header 是否设置为 application/json",
        "部署": "部署失败：确认 .env 文件中的 DEEPSEEK_API_KEY 是否配置正确",
    }
    for key, value in kb.items():
        if key in query:
            return value
    return f"知识库中未找到关于 '{query}' 的信息"


def build_customer_service_agents():
    """构建两个 Agent 并设置 Handoff。

    客服 Agent：
      - 处理一般问题（退货、物流、密码）
      - 遇到技术问题 → handoff 到技术支持

    技术支持 Agent：
      - 处理技术问题（API 报错、部署问题）
      - 没有 handoff（终端 Agent）
    """
    # TODO 3a: 创建两个 Agent
    #
    # 客服 Agent（customer_service）:
    #   instructions = "你是电商客服..." + 明确何时转给技术支持
    #   tools = {search_kb, transfer_to_tech_support}
    #
    # 技术支持 Agent（tech_support）:
    #   instructions = "你是技术支持工程师..."
    #   tools = {search_kb}

    llm = get_or_create_llm(temperature=0)
    swarm = Swarm(llm)

    # TODO 3b: 创建客服 Agent，tools 包含 search_kb 和 transfer_to_tech_support
    # customer_service_agent = Agent(...)
    customer_service_agent = Agent(
        name="customer_service",
        tools={"search_kb": search_kb},
        instructions=(
            "你是电商客服，当用户向你询问物流和售后问题时，"
            "主动使用 search_kb 工具搜索对应的应对手册。"
            "其他问题如技术问题使用 transfer_to_tech_support 移交给 tech_support"
        ),
    )

    # TODO 3c: 创建技术支持 Agent，tools 只有 search_kb
    tech_support_agent = Agent(
        name="tech_support",
        tools={"search_kb": search_kb},
        instructions=(
            "你是技术支持工程师，负责解决用户的 API 调用、系统部署等技术问题。"
            "使用 search_kb 工具查找解决方案。"
            "如果知识库中没有相关信息，诚实地告诉用户需要进一步排查。"
        ),
    )

    customer_service_agent.add_handoff(tech_support_agent, "当用户问题涉及技术细节时")

    return swarm, customer_service_agent, tech_support_agent


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    reset()
    llm = get_or_create_llm(temperature=0)

    # --- TODO 1 基础验证：Agent 对象 ---
    section("TODO 1: Agent 对象 + Handoff 注册")

    agent_a = Agent("A", "你是Agent A")
    agent_b = Agent("B", "你是Agent B", {"dummy": lambda: "dummy"})

    check("Agent 有 name", agent_a.name == "A")
    check("Agent 有 instructions", "你是Agent A" in agent_a.instructions)
    check("Agent tools 初始为空", agent_a.tools == {})
    check("Agent B tools 不为空", len(agent_b.tools) == 1)

    agent_a.add_handoff(agent_b)
    check("注册 handoff 后 tools 增加一项", len(agent_a.tools) == 1)
    check("handoff tool 名称包含 transfer_to", "transfer_to_B" in agent_a.tools)

    # 验证 handoff 返回的是目标 Agent
    handoff_result = agent_a.tools["transfer_to_B"]()
    check("handoff 返回目标 Agent", handoff_result is agent_b)

    # --- TODO 2+3: Swarm 循环 + 客服系统 ---
    section("场景1: 业务问题 → 客服直接回答（无 Handoff）")
    swarm = Swarm(llm)
    _, cs_agent, tech_agent = build_customer_service_agents()

    result1 = swarm.run(
        cs_agent,
        [HumanMessage(content="我想退货，应该怎么操作？")],
    )
    print(f"  Agent: {result1['agent']}")
    print(f"  回复: {result1['answer'][:120]}...")
    print(f"  Handoff 链: {' → '.join(result1['handoff_chain'])}")

    check("退货问题由客服处理", result1["agent"] == "customer_service")
    check("没有发生 Handoff", len(result1["handoff_chain"]) == 1)
    check("回复包含退货", "退货" in result1["answer"])

    # --- 技术问题：触发 Handoff ---
    section("场景2: 技术问题 → 客服 Handoff 到技术支持")
    result2 = swarm.run(
        cs_agent,
        [HumanMessage(content="我的 API 调用一直返回 500 错误，怎么回事？")],
    )
    print(f"  Agent: {result2['agent']}")
    print(f"  回复: {result2['answer'][:120]}...")
    print(f"  Handoff 链: {' → '.join(result2['handoff_chain'])}")

    check("技术问题最终由技术支持处理", result2["agent"] == "tech_support")
    check("发生了 Handoff", len(result2["handoff_chain"]) >= 2)
    check("Handoff 链正确", result2["handoff_chain"] == ["customer_service", "tech_support"])
    check(
        "回复涉及技术细节",
        "API" in result2["answer"]
        or "500" in result2["answer"]
        or "Content-Type" in result2["answer"],
    )

    # --- 边界场景：已到技术支持，再问技术问题 ---
    section("场景3: 直接在技术支持 Agent 上提问（无需 Handoff）")
    result3 = swarm.run(
        tech_agent,
        [HumanMessage(content="我的 Docker 部署失败了，怎么办？")],
    )
    print(f"  Agent: {result3['agent']}")
    print(f"  回复: {result3['answer'][:120]}...")
    print(f"  Handoff 链: {' → '.join(result3['handoff_chain'])}")

    check("技术问题由技术支持直接处理", result3["agent"] == "tech_support")
    check("未发生 Handoff（终端直接回答）", len(result3["handoff_chain"]) == 1)
    check(
        "回复包含部署排查",
        "部署" in result3["answer"]
        or "DEEPSEEK" in result3["answer"]
        or "env" in result3["answer"],
    )

    # --- 带 debug 输出：让你看到 Handoff 切换过程 ---
    section("场景4: Debug 模式 — 观察 Handoff 切换过程")
    result4 = swarm.run(
        cs_agent,
        [HumanMessage(content="API 返回 401 错误怎么办？")],
        debug=True,
    )
    print(f"\n  最终 Agent: {result4['agent']}")
    print(f"  最终回复: {result4['answer'][:120]}...")
    print(f"  Handoff 链: {' → '.join(result4['handoff_chain'])}")

    check("401 问题也正确 Handoff", result4["agent"] == "tech_support")
    check("Handoff 链至少两步", len(result4["handoff_chain"]) >= 2)

    summary()
