"""手写 Plan-and-Solve Agent — 先计划，再执行（LLM-based Demo）.

本实现采用最简化的 LLM-based Plan-and-Resolve 范式：
- Planner 把复杂问题拆成步骤列表
- Executor 逐步调用 LLM 解决每个步骤，历史结果作为后续步骤的上下文
- 不调用外部工具，适合纯推理、生成、分析类任务

Usage:
    uv run handwrite/03-plan-and-solve/starter.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handwrite.common.llm_client import LLMClient
from handwrite.common.message import Role, create_msg

llm_client = LLMClient()

PLANNER_PROMPT_TEMPLATE = """
你是一位顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。

# 原始问题:
{question}

请严格按照以下 JSON 数组格式输出行动计划，不要输出任何额外的解释或对话：
[
  "步骤1的简短描述",
  "步骤2的简短描述",
  "步骤3的简短描述"
]
"""

EXECUTOR_PROMPT_TEMPLATE = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决“当前步骤”，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对“当前步骤”的回答:
"""


class Planner:
    """负责把用户问题拆解成可执行的步骤列表."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        """调用 LLM 生成步骤列表，返回 list[str]."""
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)
        messages = [
            create_msg(role=Role.SYSTEM, content="你是一个任务规划专家。"),
            create_msg(role=Role.USER, content=prompt),
        ]
        response = self.llm_client.run(messages=messages)
        return self._parse_plan(response)

    def _parse_plan(self, response: str) -> list[str]:
        """把 LLM 输出解析成步骤列表（JSON 数组）."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            steps = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM 输出不是合法 JSON:\n{response}\n错误: {e}")

        if not isinstance(steps, list):
            raise ValueError(f"LLM 输出必须是 JSON 数组，但得到 {type(steps).__name__}")

        result = [str(step).strip() for step in steps if str(step).strip()]
        if not result:
            raise ValueError("LLM 输出的步骤列表为空")

        return result


class Executor:
    """负责按顺序执行计划，每一步都调用 LLM，并维护历史上下文."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def execute(self, question: str, plan: list[str]) -> str:
        """逐步执行计划，最后一步的返回即为最终答案."""
        history = ""  # 用于存储历史步骤和结果
        print("\n--- 正在执行计划 ---")

        for i, step in enumerate(plan):
            print(f"\n-> 正在执行步骤 {i + 1}/{len(plan)}: {step}")

            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan="\n".join(f"{idx + 1}. {s}" for idx, s in enumerate(plan)),
                history=history if history else "无",
                current_step=step,
            )
            messages = [create_msg(role=Role.USER, content=prompt)]

            response_text = self.llm_client.run(messages=messages) or ""

            # 更新历史记录，为下一步做准备
            history += f"步骤 {i + 1}: {step}\n结果: {response_text}\n\n"
            print(f"✅ 步骤 {i + 1} 已完成，结果: {response_text}")

        # 循环结束后，最后一步的响应就是最终答案
        return response_text


class PlanAndSolveAgent:
    """Orchestrator: 组合 Planner 和 Executor 完成完整任务."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.planner = Planner(self.llm_client)
        self.executor = Executor(self.llm_client)

    def run(self, question: str) -> str:
        """运行完整流程：先规划，后执行."""
        print(f"\n--- 开始处理问题 ---\n问题: {question}")

        # 1. Plan 阶段
        plan = self.planner.plan(question)
        if not plan:
            print("\n--- 任务终止 --- \n无法生成有效的行动计划。")
            return ""

        print(f"\n📋 生成计划（共 {len(plan)} 步）:")
        for idx, step in enumerate(plan, start=1):
            print(f"  {idx}. {step}")

        # 2. Solve 阶段
        final_answer = self.executor.execute(question, plan)

        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")
        return final_answer


if __name__ == "__main__":
    agent = PlanAndSolveAgent(llm_client=llm_client)
    question = "我想学习 AI Agent，请帮我制定一个 3 个月的学习路线，包含需要掌握的核心技能、推荐资源和学习顺序"
    agent.run(question)
