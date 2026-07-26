"""用 openai SDK 实现一个终端对话机器人，分三步迭代：

1. 单次对话 — 发送一条消息，流式打印回复
2. 多轮对话 — 维护 messages 列表，input() 驱动大循环
3. 生成器对话 — 用 yield 将流式输出暴露给调用方

Usage:
    uv run handwrite/01-llm_client/01-llm_client.py
"""

import os
from collections.abc import Generator

from dotenv import load_dotenv
from openai import OpenAI

from .message import LLMMessage

load_dotenv()


class LLMClient:
    def __init__(
        self, model: str = None, api_key: str = None, base_url: str = None, time_out: int = None
    ):
        self.model = model or os.getenv("LLM_MODEL_ID")
        api_key = api_key or os.getenv("LLM_API_KEY")
        base_url = base_url or os.getenv("LLM_BASE_URL")
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=time_out)

    def run(self, messages: list[LLMMessage], temperature: int = 0) -> str:
        try:
            # print(f"--llm start ({len(messages)} messages)--")
            # for i, msg in enumerate(messages):
            #     print(f"  [{i}] {msg.role}: {msg.content[:600]}...")
            openai_messages = [msg.to_dict() for msg in messages]
            response = self.client.chat.completions.create(
                messages=openai_messages, temperature=temperature, model=self.model, stream=True
            )
            final_response_content = []
            for chunk in response:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content or ""
                final_response_content.append(content)
            result = "".join(final_response_content)
            # print(f"--llm end ({len(result)} chars)--")
            return result

        except Exception as e:
            print(f"❌, 调用llm报错: {e}")
            return ""

    def stream(
        self, messages: list[LLMMessage], temperature: int = 0
    ) -> Generator[str, None, None]:
        try:
            print("--llm start--")
            openai_messages = [msg.to_dict() for msg in messages]
            response = self.client.chat.completions.create(
                messages=openai_messages, temperature=temperature, model=self.model, stream=True
            )
            final_response_content = []
            for chunk in response:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content or ""
                final_response_content.append(content)
                yield content
            return "".join(final_response_content)

        except Exception as e:
            print(f"❌, 调用llm报错: {e}")
            return ""
