"""
Embeddings 封装 — 全局单例缓存，避免重复初始化
"""

from langchain_core.embeddings import Embeddings
import httpx

from common.env import load_dotenv_if_needed, require_env

_cache = {}


class ZhipuEmbeddings(Embeddings):
    """智谱AI Embeddings 封装（兼容 LangChain Embeddings 接口）"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            "https://open.bigmodel.cn/api/paas/v4/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "embedding-3", "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["data"]]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def get_or_create_embeddings() -> ZhipuEmbeddings:
    """获取全局单例 Embeddings（带缓存，避免重复初始化）"""
    load_dotenv_if_needed()

    if "embeddings" not in _cache:
        api_key = require_env("ZHIPU_API_KEY")
        _cache["embeddings"] = ZhipuEmbeddings(api_key)

    return _cache["embeddings"]
