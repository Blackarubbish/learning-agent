"""手写 ReAct Agent — Thought → Action → Observation 循环.

Usage:
    uv run handwrite/02-react/starter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Any

from tavily import TavilyClient

from handwrite.common.llm_client import LLMClient
from handwrite.common.message import LLMMessage, Role, create_msg

# import sys
# sys.path.insert(0, "...")  # noqa: ERA001  # 如果需要引入 handwrite/01-llm_client

# TODO 1: 引入或复制 LLMClient

llm_client = LLMClient()


class ToolManager:
    def __init__(self):
        self.tools: dict[str, dict[str, Any]] = {}

    def register_tool(self, name: str, desc: str, func: callable):
        self.tools[name] = {"name": name, "description": desc, "function": func}
        print(f"注册工具: {name}")

    def get_tool(self, name: str) -> callable:
        target = self.tools.get(name, {})
        if not target:
            return None
        return target.get("function")

    def get_available_tools(self) -> str:
        return "\n".join(f"- {name}: {info['description']}" for name, info in self.tools.items())


def web_search(query: str, max_results: str | int = 3) -> str:
    import os

    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    max_results = int(max_results)
    try:
        response = client.search(query, max_results=max_results, include_raw_content=False)
        results = response.get("results", [])
        if not results:
            return f"未找到关于 '{query}' 的搜索结果。"
        return "\n".join(f"- {r['title']}: {r['content'][:200]}" for r in results)
    except Exception as e:
        return f"搜索失败: {e}"


def get_current_date() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M")


REACT_SYSTEM_PROMPT = """
你是一个agent助手,基于ReAct范式开发。

你的可用工具如下
{tools}

**请严格按照如下格式进行回复**
Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{input1}},{{input2}},{{input3}}...]`:调用一个可用工具, 注意，传参顺序有要求。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 Finish[最终答案] 来输出最终答案。

现在，请开始解决以下问题:
Question: {question}
"""


class ReActAgent:
    def __init__(self, client: LLMClient, tool_manager: ToolManager, max_steps: int = 10):
        self.client = client
        self.tool_manager = tool_manager
        self.max_steps = max_steps

    def run(self, quertion: str) -> str:
        tools_desc = self.tool_manager.get_available_tools()
        self.history: list[LLMMessage] = [
            create_msg(
                role=Role.SYSTEM,
                content=REACT_SYSTEM_PROMPT.format(tools=tools_desc, question=quertion),
            )
        ]
        current_step = 0
        final_answer = ""
        while current_step < self.max_steps:
            current_step += 1
            response = self.client.run(self.history)
            if not response:
                print("错误:LLM未能返回有效响应。")
                break
            self.history.append(create_msg(role=Role.ASSISTANT, content=response))
            result = self._parse_response(response)
            if not result.get("action", None):
                print("错误❌: 未知的action")
                self.history.append(
                    create_msg(
                        role=Role.USER,
                        content=(
                            "未能解析出合法的Action,注意, 合法的action如下: \n"
                            "- `{tool_name}[{tool_input}]`:调用一个可用工具。\n"
                            "- `Finish[最终答案]`:当你认为已经获得最终答案时。, "
                        ),
                    )
                )
                continue
            if result["thought"]:
                print(f"💡思考: {result.get('thought')}")

            action = result.get("action")
            action_input = result.get("action_input")

            if action.startswith("Finish"):
                final_answer = action_input[0] if action_input else ""
                print(f"\n✅ 最终答案: {final_answer}")
                break

            tool_func = self.tool_manager.get_tool(action)
            if not tool_func:
                self.history.append(
                    create_msg(
                        role=Role.USER,
                        content=f"错误: 未知工具 '{action}'。可用工具: {self.tool_manager.get_available_tools()}",
                    )
                )
                continue

            observation = tool_func(*action_input)
            print(f"🔧 调用工具: {action}[{', '.join(action_input)}] → {observation[:100]}...")
            self.history.append(create_msg(role=Role.USER, content=observation))

        return final_answer

    def _parse_response(self, text: str) -> dict:
        import re

        thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", text, re.DOTALL)
        action_match = re.search(r"Action:\s*(.+?)(?=\n|\Z)", text)
        action = action_match.group(1).strip() if action_match else ""

        # 解析 Action 字段: "tool_name[param1,param2,...]" 或 "Finish[最终答案]"
        tool_match = re.match(r"(\w+)\[(.*)\]", action)
        tool_name = tool_match.group(1) if tool_match else action
        raw_input = tool_match.group(2) if tool_match else ""
        tool_input = [p.strip() for p in raw_input.split(",") if p.strip()] if raw_input else []

        return {
            "thought": thought_match.group(1).strip() if thought_match else "",
            "action": tool_name,
            "action_input": tool_input,
            "is_final": action.startswith("Finish"),
        }


if __name__ == "__main__":
    print("TODO: 实现 ReAct Agent")
    tools = ToolManager()

    tools.register_tool(
        "web_search",
        desc=(
            "网络搜索工具，可用参数如下:\n",
            "参数1: 搜索关键字query\n",
            "参数2: 最大返回结果max_result(可选), 整数类型, 默认返回3条结果",
        ),
        func=web_search,
    )

    tools.register_tool(
        "get_current_date",
        desc=("获取今天的日期,使用有时效性的功能前请先确认时间"),
        func=get_current_date,
    )

    llm = ReActAgent(llm_client, tool_manager=tools)
    final_answer = llm.run("最近a股行情如何?")
    print(f"--最终结果:-- \n {final_answer}")
