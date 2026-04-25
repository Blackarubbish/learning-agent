"""
LLM 工厂 — 全局单例缓存，支持 DeepSeek / Zhipu
"""

from langchain_openai import ChatOpenAI

from common.env import load_dotenv_if_needed, require_env

_cache = {}


def get_or_create_llm(
    provider: str = "deepseek",
    temperature: float = 0,
) -> ChatOpenAI:
    """
    获取全局单例 LLM（带缓存）。

    Args:
        provider: "deepseek" 或 "zhipu"
        temperature: 生成温度（生成用 0.7 左右，评估用 0）
    """
    cache_key = f"{provider}_{temperature}"

    if cache_key not in _cache:
        load_dotenv_if_needed()

        if provider == "deepseek":
            api_key = require_env("DEEPSEEK_API_KEY")
            llm = ChatOpenAI(
                model="deepseek-chat",
                base_url="https://api.deepseek.com",
                api_key=api_key,
                temperature=temperature,
            )
        elif provider == "zhipu":
            api_key = require_env("ZHIPU_API_KEY")
            llm = ChatOpenAI(
                model="glm-4-plus",
                base_url="https://open.bigmodel.cn/api/paas/v4",
                api_key=api_key,
                temperature=temperature,
            )
        else:
            raise ValueError(f"不支持的 provider: {provider}，可选 deepseek / zhipu")

        _cache[cache_key] = llm

    return _cache[cache_key]