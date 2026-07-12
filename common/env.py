"""
环境变量加载 — 全局只执行一次，所有模块共享
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

_loaded = False


def load_dotenv_if_needed():
    """
    在项目根目录查找 .env 并加载（幂等，多次调用不会重复加载）。
    返回项目根路径以便后续使用。
    """
    global _loaded
    if _loaded:
        return

    # 从 common/env.py 向上两级找到项目根
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"

    if env_path.exists():
        load_dotenv(env_path)
    else:
        print("[common] 未找到 .env 文件，请从 .env.example 复制一份", file=sys.stderr)

    _loaded = True


def require_env(key: str) -> str:
    """读取必需的环境变量，缺失时立即报错"""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"环境变量 {key} 未设置，请在 .env 文件中配置")
    return value
