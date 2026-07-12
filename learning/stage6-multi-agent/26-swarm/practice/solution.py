"""Swarm 极简入门 — 完整参考实现

运行：
  PYTHONPATH=. python learning/stage6-multi-agent/26-swarm/practice/solution.py
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from common import get_or_create_llm, load_dotenv_if_needed, reset
from common.check import check, section, summary

load_dotenv_if_needed()


# ═══════════════════════════════════════════════════════════════
# Agent 与 Swarm 框架
# ═══════════════════════════════════════════════════════════════


class Agent:
    """Swarm 风格的 Agent。

    和 Stage 3 的 SimpleAgent 的区别：
    - SimpleAgent 是"一个人包揽一切"（一个 ReAct 循环 + 多个 tools）
    - Swarm Agent 是"一个角色只做一件事"，遇到超出能力范围的事就 handoff

    这种设计让每个 Agent 的 system prompt 更短、更聚焦，
    减少上下文污染（角色 A 的指令不会干扰角色 B 的推理）。
    """

    def __init__(self, name: str, instructions: str, tools: dict | None = None):
        self.name = name
        self.instructions = instructions
        self.tools = tools or {}

    def add_handoff(self, target_agent: "Agent", description: str = ""):
        """注册 handoff 到目标 Agent。"""

        # 闭包捕获 target_agent，LLM 调用时由框架检测返回值
        # 为什么不用 @tool 装饰器？
        # 因为要动态生成函数名（每个 handoff 的目标不同），
        # 闭包 + lambda 更灵活
        def _handoff():
            """把对话转给专门处理此类问题的 Agent。"""
            return target_agent

        tool_name = f"transfer_to_{target_agent.name}"
        self.tools[tool_name] = _handoff


class TooManyTurns(Exception):
    """超出最大轮数，避免死循环。"""


class Swarm:
    """极简 Multi-Agent 编排器，核心循环 ~30 行。"""

    def __init__(self, llm, max_turns: int = 10):
        self.llm = llm
        self.max_turns = max_turns

    def run(self, agent: Agent, messages: list, debug: bool = False) -> dict:
        current_agent = agent
        # 复制一份历史消息，不修改原始
        history = list(messages)
        handoff_chain = [agent.name]

        for turn in range(self.max_turns):
            if debug:
                print(f"\n[Turn {turn + 1}] current_agent={current_agent.name}")

            # 1. 构建带 system prompt 的消息
            #    当前 Agent 的 instructions 作为 system prompt
            #    这确保了每个 Agent 的上下文中只有自己的角色定义
            system_msg = SystemMessage(content=current_agent.instructions)
            full_messages = [system_msg] + history

            # 2. 调用 LLM
            if current_agent.tools:
                # 把 dict 中的 callable 转成 @tool 装饰的函数供 bind_tools
                tool_list = list(current_agent.tools.items())
                tool_schemas = []
                for t_name, t_fn in tool_list:
                    # 用 @tool 装饰器包装，让 LangChain 自动生成 JSON Schema
                    # 为什么用 @tool 装饰器而非手动写 schema？
                    # LangChain 的 @tool 会自动从函数签名和 docstring 提取
                    # name/description/parameters，和 Swarm 原版的函数→schema
                    # 自动转换逻辑一致
                    wrapped = tool(t_fn)
                    wrapped.name = t_name
                    tool_schemas.append(wrapped)

                llm_with_tools = self.llm.bind_tools(tool_schemas)
                response = llm_with_tools.invoke(full_messages)
            else:
                response = self.llm.invoke(full_messages)

            # 把 assistant 消息加入历史
            history.append(response)

            # 3. 处理 tool_calls
            tool_calls = getattr(response, "tool_calls", None) or []
            if tool_calls:
                handoff_occurred = False
                for tc in tool_calls:
                    t_name = tc.get("name", "")
                    t_args = tc.get("args", {})

                    if t_name in current_agent.tools:
                        result = current_agent.tools[t_name](**t_args)

                        # 3a. 检测 Handoff：tool 返回 Agent 对象
                        if isinstance(result, Agent):
                            if debug:
                                print(f"  ↪ Handoff: {current_agent.name} → {result.name}")
                            current_agent = result
                            handoff_chain.append(result.name)
                            handoff_occurred = True
                            # 把 handoff 信息也加入历史（LLM 知道已经转交了）
                            history.append(
                                ToolMessage(
                                    content=f"已将对话转交给 {result.name}，请继续处理。",
                                    tool_call_id=tc.get("id", ""),
                                )
                            )
                            break  # handoff 后立即切 Agent，不继续处理当前 tool_calls

                        # 3b. 普通 tool 结果
                        history.append(
                            ToolMessage(content=str(result), tool_call_id=tc.get("id", ""))
                        )

                if handoff_occurred:
                    continue  # 切换到新 Agent 重新开始循环
            else:
                # 4. 没有 tool call → 最终回复
                return {
                    "answer": response.content if hasattr(response, "content") else str(response),
                    "agent": current_agent.name,
                    "handoff_chain": handoff_chain,
                }

        raise TooManyTurns(f"超过最大轮数 {self.max_turns}")


# ═══════════════════════════════════════════════════════════════
# 客服 → 技术支持 Handoff 系统
# ═══════════════════════════════════════════════════════════════


def search_kb(query: str) -> str:
    """搜索知识库。"""
    kb = {
        "退货": "退货流程：登录→我的订单→申请退货→填写原因→等待审核→寄回商品→退款",
        "物流": "物流查询：登录→我的订单→点击订单→查看物流详情",
        "密码": "修改密码：设置→账号安全→修改密码→验证手机→设置新密码",
        "API": "API 调用 500 错误：检查 Content-Type header 是否设置为 application/json。如果是 401 错误，检查 API Key 是否正确。",
        "部署": "部署失败常见原因：1) .env 文件中 DEEPSEEK_API_KEY 未配置 2) Docker 容器内无法访问外网 3) 端口被占用",
    }
    for key, value in kb.items():
        if key in query:
            return value
    return f"知识库中未找到关于 '{query}' 的直接信息，请提供更多细节。"


def build_customer_service_system():
    """构建客服→技术支持两级 Handoff 系统。

    设计原则（AgentGuide 推荐）：
    - 每个 Agent 职责单一：客服只管业务，技术只管技术
    - Handoff 由 LLM 自主判断：不用硬编码路由规则
    - 终端 Agent（技术支持）没有 handoff：防止无限转交
    """

    # 技术支持 Agent 先创建（因为客服需要引用它）
    tech_support = Agent(
        "tech_support",
        "你是技术支持工程师，负责解决用户的 API 调用、系统部署等技术问题。"
        "使用 search_kb 工具查找解决方案。"
        "如果知识库中没有相关信息，诚实地告诉用户需要进一步排查。",
        {"search_kb": search_kb},
    )

    # 客服 Agent
    customer_service = Agent(
        "customer_service",
        "你是电商平台客服，负责处理退货、物流、账号等业务问题。"
        "使用 search_kb 工具查找相关信息。"
        "如果用户的问题涉及 API 调用、程序部署、系统报错等技术细节，"
        "你应该调用 transfer_to_tech_support 将对话转给技术支持。",
        {"search_kb": search_kb},
    )
    customer_service.add_handoff(
        tech_support,
        "当用户问题涉及技术细节（API调用、代码部署、系统配置等）时使用",
    )

    return customer_service, tech_support


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    reset()
    llm = get_or_create_llm(temperature=0)

    # --- 基础验证 ---
    section("基础验证：Agent + Handoff 机制")
    agent_a = Agent("A", "你是Agent A")
    agent_b = Agent("B", "你是Agent B", {"dummy": lambda: "dummy"})
    check("Agent 有 name", agent_a.name == "A")
    check("Agent 有 instructions", "你是Agent A" in agent_a.instructions)
    check("空 tools 为 dict", agent_a.tools == {})
    check("B 有 tool", len(agent_b.tools) == 1)
    agent_a.add_handoff(agent_b)
    check("注册 handoff 后 tools 增加", len(agent_a.tools) == 1)
    check("handoff function 名包含 transfer_to", "transfer_to_B" in agent_a.tools)
    result = agent_a.tools["transfer_to_B"]()
    check("handoff 返回目标 Agent", result is agent_b)

    # --- 业务问题：不需要 Handoff ---
    section("场景1: 业务问题 → 客服直接回答（无 Handoff）")
    swarm = Swarm(llm)
    cs_agent, tech_agent = build_customer_service_system()

    result1 = swarm.run(
        cs_agent,
        [HumanMessage(content="我想退货，应该怎么操作？")],
        debug=False,
    )
    print(f"  Agent: {result1['agent']}")
    print(f"  回复: {result1['answer'][:100]}...")
    print(f"  Handoff 链: {' → '.join(result1['handoff_chain'])}")

    check("退货问题由客服处理", result1["agent"] == "customer_service")
    check("没有发生 Handoff", len(result1["handoff_chain"]) == 1)
    check("回复包含退货", "退货" in result1["answer"])

    # --- 技术问题：触发 Handoff ---
    section("场景2: 技术问题 → 客服 Handoff 到技术支持")
    result2 = swarm.run(
        cs_agent,
        [HumanMessage(content="我的 API 调用一直返回 500 错误，怎么回事？")],
        debug=False,
    )
    print(f"  Agent: {result2['agent']}")
    print(f"  回复: {result2['answer'][:100]}...")
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

    summary()
