"""
Agent Study 共享模块

一键导入基础设施，消除重复 boilerplate。
每个 practice 文件只需：
    from common import embeddings, get_llm

============================================================
使用方式：
    # 基础使用
    from common import embeddings, get_llm

    # 带缓存的使用（推荐）
    from common import load_dotenv_if_needed, get_or_create_embeddings, get_or_create_llm
============================================================
"""

from common.check import check, reset, section, summary
from common.embeddings import ZhipuEmbeddings, get_or_create_embeddings
from common.env import load_dotenv_if_needed
from common.llm import get_or_create_llm

__all__ = [
    "load_dotenv_if_needed",
    "ZhipuEmbeddings",
    "get_or_create_embeddings",
    "get_or_create_llm",
    "section",
    "check",
    "summary",
    "reset",
]
