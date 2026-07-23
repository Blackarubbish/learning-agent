"""手写 Reflection Agent — 失败→反馈→修正→重试.

Usage:
    uv run handwrite/04-reflection/starter.py
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handwrite.common.llm_client import LLMClient
from handwrite.common.message import Role, create_msg


class Memory:
    def __init__(self):
        self.records: list[dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        record = {"type": record_type, "content": content}
        self.records.append(record)
        print(f"📝 记忆已更新，新增一条 '{record_type}' 记录。")

    def get_trajectory(self) -> str:
        trajectory_parts = []
        for record in self.records:
            if record["type"] == "execution":
                trajectory_parts.append(f"--- 上一轮尝试 (代码) ---\n{record['content']}")
            elif record["type"] == "reflection":
                trajectory_parts.append(f"--- 评审员反馈 ---\n{record['content']}")
        return "\n\n".join(trajectory_parts)

    def get_last_execution(self) -> str | None:
        for record in reversed(self.records):
            if record["type"] == "execution":
                return record["content"]
        return None


INITIAL_PROMPT_TEMPLATE = """
你是一位资深的Python程序员。请根据以下要求，编写一个Python函数。
你的代码必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范。

要求: {task}

请直接输出代码，不要包含任何额外的解释。
"""

REFLECT_PROMPT_TEMPLATE = """
你是一位极其严格的代码评审专家和资深算法工程师，对代码的性能有极致的要求。
你的任务是审查以下Python代码，并专注于找出其在<strong>算法效率</strong>上的主要瓶颈。

# 原始任务:
{task}

# 待审查的代码:
```python
{code}
```

请分析该代码的时间复杂度，并思考是否存在一种<strong>算法上更优</strong>的解决方案来显著提升性能。
如果存在，请清晰地指出当前算法的不足，并提出具体的、可行的改进算法建议（例如，使用筛法替代试除法）。
如果代码在算法层面已经达到最优，才能回答“无需改进”。

请直接输出你的反馈，不要包含任何额外的解释。
"""


REFINE_PROMPT_TEMPLATE = """
你是一位资深的Python程序员。你正在根据一位代码评审专家的反馈来优化你的代码。

# 原始任务:
{task}

# 你上一轮尝试的代码:
{last_code_attempt}
评审员的反馈：
{feedback}

请根据评审员的反馈，生成一个优化后的新版本代码。
你的代码必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范。
请直接输出优化后的代码，不要包含任何额外的解释。
"""


class ReflectionAgent:
    def __init__(self, llm_client: LLMClient, max_iterations=3):
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations

    def run(self, task: str):
        print(f"\n--- 开始处理任务 ---\n任务: {task}")

        # --- 1. 初始执行 ---
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = INITIAL_PROMPT_TEMPLATE.format(task=task)
        initial_code = self._get_llm_response(initial_prompt)
        print(f"--- 初始执行阶段 LLM 返回 ---\n{initial_code}\n")
        self.memory.add_record("execution", initial_code)

        for i in range(self.max_iterations):
            print(f"\n--- 第 {i + 1}/{self.max_iterations} 轮迭代 ---")

            # a. 反思
            print("\n-> 正在进行反思...")
            last_code = self.memory.get_last_execution()
            feedback = self._get_llm_response(
                prompt=REFLECT_PROMPT_TEMPLATE.format(task=task, code=last_code)
            )
            print(f"--- 反思阶段 LLM 返回 ---\n{feedback}\n")
            self.memory.add_record("reflection", content=feedback)
            if "无需改进" in feedback:
                print("\n✅ 反思认为代码已无需改进，任务完成。")
                break

            redo_code = self._get_llm_response(
                prompt=REFINE_PROMPT_TEMPLATE.format(
                    task=task, last_code_attempt=last_code, feedback=feedback
                )
            )
            print(f"--- 改进阶段 LLM 返回 ---\n{redo_code}\n")
            self.memory.add_record("execution", redo_code)

        final_result = self.memory.get_last_execution()
        print(f"\n--- 任务完成 ---\n最终生成的代码:\n```python\n{final_result}\n```")
        return final_result

    def _get_llm_response(self, prompt: str) -> str:
        response = self.llm_client.run(messages=[create_msg(role=Role.USER, content=prompt)])
        return response


if __name__ == "__main__":
    llm = ReflectionAgent(llm_client=LLMClient())
    llm.run("编写一个Python函数，找出1到n之间所有的素数 (prime numbers)")
